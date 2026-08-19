import unittest
from unittest.mock import patch

from server.game_state import GameState, MAX_PLAYERS, _is_holly


class PlayerIdentityTests(unittest.TestCase):
    def test_holly_name_matching_is_trimmed_and_case_insensitive(self):
        self.assertTrue(_is_holly(" Holly "))
        self.assertTrue(_is_holly("HOLLY"))
        self.assertFalse(_is_holly("Holly J"))
        self.assertFalse(_is_holly(None))


class RoomStateTests(unittest.TestCase):
    def setUp(self):
        self.state = GameState()

    @patch("server.game_state._generate_room_code", return_value="SNOW")
    def test_create_room_sets_host_and_requested_color(self, _code):
        room = self.state.create_room("Alex", "sid-host", "blue")

        self.assertEqual(room.code, "SNOW")
        self.assertEqual(room.host_sid, "sid-host")
        self.assertEqual(room.players["sid-host"].name, "Alex")
        self.assertEqual(room.players["sid-host"].color, "blue")
        self.assertEqual(room.status, "lobby")

    @patch("server.game_state._generate_room_code", return_value="SNOW")
    def test_holly_reserves_black_and_reassigns_existing_black_player(self, _code):
        room = self.state.create_room("Alex", "sid-host", "black")
        updated, error = self.state.join_room("SNOW", "Holly", "sid-holly", "red")

        self.assertIsNone(error)
        self.assertIs(updated, room)
        self.assertEqual(room.players["sid-holly"].color, "black")
        self.assertNotEqual(room.players["sid-host"].color, "black")

    @patch("server.game_state._generate_room_code", return_value="SNOW")
    def test_duplicate_requested_color_falls_back_to_available_color(self, _code):
        room = self.state.create_room("Alex", "sid-host", "blue")
        _, error = self.state.join_room("SNOW", "Sam", "sid-2", "blue")

        self.assertIsNone(error)
        self.assertNotEqual(room.players["sid-2"].color, "blue")
        self.assertNotEqual(room.players["sid-host"].color, room.players["sid-2"].color)

    @patch("server.game_state._generate_room_code", return_value="SNOW")
    def test_room_rejects_players_after_capacity_is_reached(self, _code):
        self.state.create_room("Host", "sid-0", "red")
        for index in range(1, MAX_PLAYERS):
            _, error = self.state.join_room("SNOW", f"Player {index}", f"sid-{index}", "")
            self.assertIsNone(error)

        room, error = self.state.join_room("SNOW", "Overflow", "sid-overflow", "")
        self.assertIsNone(room)
        self.assertEqual(error, "Room is full")

    @patch("server.game_state._generate_room_code", return_value="SNOW")
    def test_removing_host_transfers_host_to_remaining_human(self, _code):
        room = self.state.create_room("Host", "sid-host", "red")
        self.state.join_room("SNOW", "Guest", "sid-guest", "blue")

        updated = self.state.remove_player("sid-host")

        self.assertIs(updated, room)
        self.assertEqual(room.host_sid, "sid-guest")
        self.assertNotIn("sid-host", room.players)

    @patch("server.game_state._generate_room_code", return_value="SNOW")
    def test_serialized_room_exposes_stable_client_contract(self, _code):
        room = self.state.create_room("Host", "sid-host", "red")
        payload = self.state.serialize_room(room)

        self.assertEqual(payload["code"], "SNOW")
        self.assertEqual(payload["hostId"], "sid-host")
        self.assertEqual(payload["status"], "lobby")
        self.assertEqual(payload["width"], room.width)
        self.assertEqual(payload["height"], room.height)
        self.assertEqual(payload["players"][0]["name"], "Host")
        self.assertFalse(payload["players"][0]["isBot"])


if __name__ == "__main__":
    unittest.main()
