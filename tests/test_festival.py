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
                        room.round_elapsed += .05
                        festival.step(room,.05,web.game_server._move_with_walls)
                        if room.festival["completed"]:
                            break
                    snapshot = web.game_server._world_payload(room)["world"]
                    self.assertNotIn("hidden",snapshot["festival"])
                    self.assertEqual(len(snapshot["players"]),2)
                    for p in room.players.values():
                        self.assertEqual(p.score,p.round_score)
                self.assertEqual(web.game_server._finish_round(room)[1]["room"]["status"],"between_rounds")

    def test_authority_and_sync(self):
        with patch.object(web.game_server,"_ensure_world_loop"):
            host = web.socketio.test_client(web.app)
            peer = web.socketio.test_client(web.app)
            try:
                host.emit("create_room",{"name":"Host"})
                code=next(e["args"][0]["room"]["code"] for e in host.get_received() if e["name"]=="room_joined")
                peer.emit("join_room",{"room":code,"name":"Peer"})
                settings=dict(mode="boss",rounds=1,difficulty="hard",ai="easy")
                peer.emit("festival_settings",settings)
                room=web.state.get_room(code)
                self.assertEqual(room.selected_mode,"random")
                host.emit("festival_settings",settings)
                peer.emit("festival_character",{"character":"yeti"})
                peer.emit("festival_character",{"character":["forged"]})
                self.assertEqual(next(p.character for p in room.players.values() if p.name=="Peer"),"yeti")
                host.emit("start_game")
                self.assertEqual(room.round_order,["boss"])
                with patch.object(web.socketio,"start_background_task"):
                    host.emit("start_round")
                for client in (host,peer):
                    events=client.get_received()
                    started=next(e for e in events if e["name"]=="round_started")
                    self.assertEqual(started["args"][0]["room"]["roundType"],"boss")
                peer.emit("player_input",{"x":[],"y":1})
                peer.emit("collect",{"score":999999})
                self.assertTrue(all(p.round_score==0 for p in room.players.values()))
            finally:
                peer.disconnect()
                host.disconnect()
