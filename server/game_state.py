import random
import string
import threading
import time
from dataclasses import dataclass, field

MAX_PLAYERS = 16
ROOM_WIDTH = 960
ROOM_HEIGHT = 540

PLAYER_COLORS = [
    "red",
    "orange",
    "yellow",
    "lime",
    "green",
    "teal",
    "cyan",
    "blue",
    "indigo",
    "purple",
    "magenta",
    "pink",
    "brown",
    "gray",
    "black",
    "white",
]


def _generate_room_code(existing_codes):
    letters = string.ascii_uppercase
    while True:
        code = "".join(random.choice(letters) for _ in range(4))
        if code not in existing_codes:
            return code


@dataclass
class PlayerState:
    sid: str
    name: str
    color: str
    score: int = 0
    round_score: int = 0
    ready: bool = False
    last_collect_ts: float = 0.0
    last_action_ts: float = 0.0
    last_hit_ts: float = 0.0
    vel_x: float = 0.0
    vel_y: float = 0.0
    x: float = 0.0
    y: float = 0.0
    input_x: float = 0.0
    input_y: float = 0.0
    facing_x: float = 1.0
    facing_y: float = 0.0
    alive: bool = True
    team: int = 0
    energy: float = 0.0
    has_light: bool = False
    score_accum: float = 0.0
    rings_left: int = 3


@dataclass
class RoomState:
    code: str
    host_sid: str
    players: dict = field(default_factory=dict)
    status: str = "lobby"
    current_round: int = 0
    round_duration: int = 20
    intermission: int = 8
    max_rounds: int = 5
    round_ends_at: float = 0.0
    task_running: bool = False
    lock: threading.Lock = field(default_factory=threading.Lock)
    width: int = ROOM_WIDTH
    height: int = ROOM_HEIGHT
    round_type: str = "lobby"
    projectiles: list = field(default_factory=list)
    monster_projectiles: list = field(default_factory=list)
    monsters: list = field(default_factory=list)
    decorations: list = field(default_factory=list)
    hazards: list = field(default_factory=list)
    gifts: list = field(default_factory=list)
    walls: list = field(default_factory=list)
    light: dict = field(default_factory=dict)
    trails: list = field(default_factory=list)
    trail_map: dict = field(default_factory=dict)
    last_update_ts: float = field(default_factory=time.time)
    tick: int = 0
    hazard_accum: float = 0.0
    gift_accum: float = 0.0
    next_projectile_id: int = 1
    next_item_id: int = 1
    next_monster_id: int = 1
    next_monster_projectile_id: int = 1
    next_decoration_id: int = 1
    round_order: list = field(default_factory=list)
    round_elapsed: float = 0.0
    ice_finish_line_spawned: bool = False
    ice_buffer_until: float = 0.0


class GameState:
    def __init__(self):
        self.rooms = {}
        self.lock = threading.Lock()

    def _pick_available_color(self, room):
        used = {player.color for player in room.players.values()}
        for color in PLAYER_COLORS:
            if color not in used:
                return color
        return ""

    def _color_taken(self, room, color):
        return any(player.color == color for player in room.players.values())

    def _spawn_position(self, room, index=0):
        margin = 40
        x = margin + (index * 60) % (room.width - margin * 2)
        y = margin + ((index * 90) % (room.height - margin * 2))
        return float(x), float(y)

    def create_room(self, name, sid, color):
        with self.lock:
            code = _generate_room_code(self.rooms.keys())
            room = RoomState(code=code, host_sid=sid)
            chosen = color if color in PLAYER_COLORS else ""
            if not chosen:
                chosen = self._pick_available_color(room)
            player = PlayerState(sid=sid, name=name, color=chosen)
            player.x, player.y = self._spawn_position(room, 0)
            room.players[sid] = player
            self.rooms[code] = room
            return room

    def join_room(self, code, name, sid, color):
        with self.lock:
            room = self.rooms.get(code)
            if not room:
                return None, "Room not found"
            if room.status != "lobby":
                return None, "Room already started"
            if len(room.players) >= MAX_PLAYERS:
                return None, "Room is full"
            chosen = color if color in PLAYER_COLORS and not self._color_taken(room, color) else ""
            if not chosen:
                chosen = self._pick_available_color(room)
            if not chosen:
                return None, "No colors available"
            player = PlayerState(sid=sid, name=name, color=chosen)
            player.x, player.y = self._spawn_position(room, len(room.players))
            room.players[sid] = player
            return room, None

    def get_room(self, code):
        with self.lock:
            return self.rooms.get(code)

    def get_room_by_player(self, sid):
        with self.lock:
            for room in self.rooms.values():
                if sid in room.players:
                    return room
            return None

    def list_rooms(self):
        with self.lock:
            return list(self.rooms.values())

    def remove_player(self, sid):
        with self.lock:
            for code, room in list(self.rooms.items()):
                if sid in room.players:
                    del room.players[sid]
                    if room.host_sid == sid:
                        room.host_sid = next(iter(room.players), "")
                    if not room.players:
                        del self.rooms[code]
                        return None
                    return room
            return None

    def serialize_room(self, room):
        players = []
        for player in room.players.values():
            players.append(
                {
                    "id": player.sid,
                    "name": player.name,
                    "color": player.color,
                    "x": player.x,
                    "y": player.y,
                    "score": player.score,
                    "roundScore": player.round_score,
                    "ready": player.ready,
                    "team": player.team,
                    "alive": player.alive,
                    "ringsLeft": player.rings_left,
                }
            )
        return {
            "code": room.code,
            "status": room.status,
            "currentRound": room.current_round,
            "hostId": room.host_sid,
            "players": players,
            "roundEndsAt": room.round_ends_at,
            "maxRounds": room.max_rounds,
            "roundType": room.round_type,
            "width": room.width,
            "height": room.height,
        }

    def record_collect(self, sid):
        room = self.get_room_by_player(sid)
        if not room:
            return None, None
        with room.lock:
            if room.status != "in_round":
                return room, "Round not active"
            player = room.players.get(sid)
            if not player:
                return room, "Player not found"
            now = time.time()
            if now - player.last_collect_ts < 0.2:
                return room, "Too fast"
            player.last_collect_ts = now
            player.round_score += 1
            return room, None

    def set_ready(self, sid, ready):
        room = self.get_room_by_player(sid)
        if not room:
            return None
        with room.lock:
            player = room.players.get(sid)
            if player:
                player.ready = ready
        return room

    def set_input(self, sid, input_x, input_y):
        room = self.get_room_by_player(sid)
        if not room:
            return None
        with room.lock:
            player = room.players.get(sid)
            if player:
                player.input_x = max(-1.0, min(1.0, float(input_x)))
                player.input_y = max(-1.0, min(1.0, float(input_y)))
                if abs(player.input_x) > 0.1 or abs(player.input_y) > 0.1:
                    player.facing_x = player.input_x
                    player.facing_y = player.input_y
        return room

    def set_color(self, sid, color):
        room = self.get_room_by_player(sid)
        if not room:
            return None, "Room not found"
        if room.status != "lobby":
            return room, "Game already started"
        if color not in PLAYER_COLORS:
            return room, "Pick a valid color"
        with room.lock:
            if self._color_taken(room, color):
                return room, "Color already taken"
            player = room.players.get(sid)
            if player:
                player.color = color
        return room, None
