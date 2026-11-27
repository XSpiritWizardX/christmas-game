import os
import tempfile
import unittest
from unittest.mock import patch

_tmp = tempfile.TemporaryDirectory()
os.environ.setdefault("SQLITE_PATH", os.path.join(_tmp.name, "test.db"))
import web
from server import festival
from server.game_state import GameState


class FestivalTests(unittest.TestCase):
    def test_full_rotation_with_bots(self):
        for mode in (*web.game_server.ROUND_SEQUENCE, "maze", "trails", "bonus"):
            with self.subTest(mode=mode):
                state = GameState()
                room = state.create_room("Peer", "peer", "red")
                state.add_bot(room)
                room.status = "in_round"
                web.game_server._setup_round(room, mode)
                if mode in festival.MODES:
                    for _ in range(800):
                        room.round_elapsed += 0.05
                        festival.step(room, 0.05, web.game_server._move_with_walls)
                        if room.festival["completed"]:
                            break
                    snapshot = web.game_server._world_payload(room)["world"]
                    self.assertNotIn("hidden", snapshot["festival"])
                    self.assertEqual(len(snapshot["players"]), 2)
                    for p in room.players.values():
                        self.assertEqual(p.score, p.round_score)
                self.assertEqual(
                    web.game_server._finish_round(room)[1]["room"]["status"],
                    "between_rounds",
                )

    def test_authority_and_sync(self):
        with patch.object(web.game_server, "_ensure_world_loop"):
            host = web.socketio.test_client(web.app)
            peer = web.socketio.test_client(web.app)
            try:
                host.emit("create_room", {"name": "Host"})
                code = next(
                    e["args"][0]["room"]["code"]
                    for e in host.get_received()
                    if e["name"] == "room_joined"
                )
                peer.emit("join_room", {"room": code, "name": "Peer"})
                settings = dict(mode="boss", rounds=1, difficulty="hard", ai="easy")
                peer.emit("festival_settings", settings)
                room = web.state.get_room(code)
                self.assertEqual(room.selected_mode, "random")
                host.emit("festival_settings", settings)
                peer.emit("festival_character", {"character": "yeti"})
                peer.emit("festival_character", {"character": ["forged"]})
                self.assertEqual(
                    next(
                        p.character for p in room.players.values() if p.name == "Peer"
                    ),
                    "yeti",
                )
                host.emit("start_game")
                self.assertEqual(room.round_order, ["boss"])
                with patch.object(web.socketio, "start_background_task"):
                    host.emit("start_round")
                for client in (host, peer):
                    events = client.get_received()
                    started = next(e for e in events if e["name"] == "round_started")
                    self.assertEqual(started["args"][0]["room"]["roundType"], "boss")
                peer.emit("player_input", {"x": [], "y": 1})
                peer.emit("collect", {"score": 999999})
                self.assertTrue(all(p.round_score == 0 for p in room.players.values()))
            finally:
                peer.disconnect()
                host.disconnect()


class ObjectiveTests(unittest.TestCase):
    def arena(self, mode):
        state = GameState()
        room = state.create_room("Host", "p", "red")
        state.add_bot(room)
        room.status = "in_round"
        web.game_server._setup_round(room, mode)
        return room, room.players["p"]

    def tick(self, room):
        room.round_elapsed += 0.05
        festival.step(room, 0.05, web.game_server._move_with_walls)

    def test_bot_finishes_slalom_without_crossing_walls(self):
        for mode in ("raceway", "avalanche"):
            room, _ = self.arena(mode)
            bot = next(p for p in room.players.values() if p.is_bot)
            for _ in range(900):
                self.tick(room)
                self.assertFalse(
                    any(
                        web.game_server._rect_collides_circle(w, bot.x, bot.y, 14)
                        for w in room.walls
                    )
                )
                if room.festival["completed"]:
                    break
            self.assertEqual(bot.checkpoint, 5)

    def test_workshop_requires_delivering_carried_package(self):
        room, p = self.arena("workshop")
        p.x, p.y = 100, 270
        self.tick(room)
        self.assertEqual((p.cargo, p.score), (1, 0))
        p.x, p.y = 830, 120
        self.tick(room)
        self.assertEqual((p.cargo, p.score), (0, 5))

    def test_treasures_and_boss_cannot_be_double_claimed(self):
        room, p = self.arena("ornaments")
        prize = next(iter(room.festival["hidden"]))
        m = room.festival["markers"][prize]
        p.x, p.y = m["x"], m["y"]
        room.round_elapsed = 1
        festival.action(room, p)
        festival.action(room, p)
        self.assertEqual(p.score, 5)
        room, p = self.arena("boss")
        room.festival["hp"] = 1
        p.x, p.y = 480, 270
        room.round_elapsed = 1
        festival.action(room, p)
        self.assertTrue(room.festival["completed"])
        self.assertEqual(room.festival["hp"], 0)

    def test_authenticated_costume_survives_new_player(self):
        import store
        from uuid import uuid4

        account = store.create_account(
            "QA", "Tester", str(uuid4()) + "@example.invalid", "qa-password"
        )
        room, p = self.arena("lake")
        self.assertEqual(store.character_preference(account), "classic")
        store.character_preference(account, "queen")
        web.game_server._apply_store_profile(p, account)
        self.assertEqual(p.character, "queen")

    def test_recovery_keeps_host_score_and_carried_item(self):
        room, p = self.arena("heist")
        p.score, p.cargo, p.character = 7, 1, "knight"
        with room.lock:
            self.assertTrue(web._resume_player(room, "p", "recovered"))
        self.assertEqual(
            (room.host_sid, p.score, p.cargo, p.character),
            ("recovered", 7, 1, "knight"),
        )

    def test_round_votes_choose_next_round_and_preserve_fixed_playlist(self):
        votes = web.game_server.round_vote
        room, player = self.arena("boss")
        room.status, room.selected_mode = "between_rounds", "random"
        room.current_round = 1
        room.round_order = ["boss", "lake", "workshop"]
        self.assertEqual(votes.winner(room), "lake")
        room.round_votes[player.sid] = "workshop"
        self.assertEqual(votes.winner(room), "workshop")
        votes.apply(room)
        self.assertEqual(room.round_order, ["boss", "workshop", "lake"])
        self.assertFalse(room.round_votes)
        room.round_votes[player.sid] = "boss"
        self.assertEqual(votes.winner(room), "boss")
        room.selected_mode = "boss"
        self.assertEqual(votes.ballot(room), [])

    def test_boss_warnings_precede_damage(self):
        room, _ = self.arena("boss")
        room.round_elapsed = 0
        festival.step(room, 0, lambda *args: None)
        warning = room.festival["warning"]
        self.assertTrue(warning)
        self.assertFalse(room.festival["danger"])
        room.round_elapsed = 0.65
        festival.step(room, 0, lambda *args: None)
        self.assertEqual(room.festival["danger"], warning)
