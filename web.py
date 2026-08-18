import os
import random
import sys
import threading
import time

from flask import request, send_from_directory

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_DIR = os.path.join(ROOT_DIR, "server")
CLIENT_DIST = os.path.join(ROOT_DIR, "client", "dist")

if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

import server.app as game_server  # noqa: E402

app = game_server.app
socketio = game_server.socketio
state = game_server.state

# ---------------------------------------------------------------------------
# Party-game production upgrades
# ---------------------------------------------------------------------------

RECONNECT_GRACE_SECONDS = 15

# Faster, punchier rounds. The game loop stays server-authoritative; only the
# presentation length changes.
game_server.ROUND_DURATIONS.update(
    {
        "survival": 55,
        "snowball": 70,
        "hunt": 70,
        "hill": 65,
        "thin_ice": 75,
        "light": 65,
        "ice": 75,
        "trails": 65,
        "bonus": 10,
    }
)

# Keep progression cosmetic. Existing boost_speed purchases remain owned, but
# are presented as a cosmetic aura and no longer increase movement speed.
game_server.STORE_ITEMS = [
    {"id": "skin_ice", "label": "Ice Drift Skin", "cost": 3, "type": "skin"},
    {"id": "boost_speed", "label": "Sleigh Bell Aura", "cost": 6, "type": "cosmetic"},
    {"id": "trail_candy", "label": "Candy Cane Trail", "cost": 5, "type": "cosmetic"},
    {"id": "hat_elf", "label": "Elf Hat Badge", "cost": 4, "type": "cosmetic"},
    {"id": "victory_sparkle", "label": "Victory Sparkles", "cost": 8, "type": "cosmetic"},
]


def _fair_player_speed_multiplier(player):
    # Preserve the game's Holly easter egg, but remove store-bought speed
    # advantages so crowns never become pay-to-win power.
    return game_server.HOLLY_SPEED_MULTIPLIER if game_server._is_holly_player(player) else 1.0


game_server._player_speed_multiplier = _fair_player_speed_multiplier

# Give AI opponents memorable Christmas identities and subtle personalities.
AI_PROFILES = [
    ("Krampus", 1.00, 0.72),
    ("Rudolph", 1.12, 0.92),
    ("Frosty", 0.90, 1.12),
    ("Ginger", 1.04, 0.88),
    ("Jingles", 0.98, 0.82),
    ("Tinsel", 1.08, 1.00),
    ("Coal", 0.94, 0.78),
    ("Noel", 1.02, 0.96),
]

_original_add_bot = state.add_bot
_original_set_bot_input = game_server._set_bot_input
_original_ai_ready_action = game_server._ai_ready_action


def _themed_add_bot(room, name=None):
    if name is None:
        used = {player.name for player in room.players.values()}
        available = [profile for profile in AI_PROFILES if profile[0] not in used]
        profile = random.choice(available or AI_PROFILES)
        name = profile[0]
    else:
        profile = next((entry for entry in AI_PROFILES if entry[0] == name), None)

    updated, error = _original_add_bot(room, name=name)
    if error or not updated:
        return updated, error

    bot = next(
        (player for player in updated.players.values() if player.is_bot and player.name == name),
        None,
    )
    if bot:
        if profile is None:
            profile = random.choice(AI_PROFILES)
        bot.party_move_scale = profile[1]
        bot.party_action_scale = profile[2]
    return updated, error


def _personality_bot_input(player, dx, dy, speed_scale=1.0):
    personality_scale = getattr(player, "party_move_scale", 1.0)
    return _original_set_bot_input(player, dx, dy, speed_scale=speed_scale * personality_scale)


def _personality_ai_ready_action(player, now, cooldown):
    scale = getattr(player, "party_action_scale", 1.0)
    scaled = (max(0.08, cooldown[0] * scale), max(0.1, cooldown[1] * scale))
    return _original_ai_ready_action(player, now, scaled)


state.add_bot = _themed_add_bot
game_server._set_bot_input = _personality_bot_input
game_server._ai_ready_action = _personality_ai_ready_action

# ---------------------------------------------------------------------------
# Reconnect / resume support
# ---------------------------------------------------------------------------

_resume_lock = threading.Lock()
_resume_by_token = {}
_token_by_sid = {}
_resume_generation = {}
_original_create_room = state.create_room
_original_join_room = state.join_room
_original_remove_player = state.remove_player


def _event_payload():
    try:
        event = getattr(request, "event", None) or {}
    except RuntimeError:
        return {}
    args = event.get("args") or []
    if args and isinstance(args[0], dict):
        return args[0]
    return {}


def _event_name():
    try:
        event = getattr(request, "event", None) or {}
    except RuntimeError:
        return ""
    return str(event.get("message") or "")


def _resume_token_from_event():
    value = _event_payload().get("resumeToken")
    return str(value or "").strip()[:128]


def _register_resume(token, room_code, sid):
    if not token:
        return
    with _resume_lock:
        previous = _resume_by_token.get(token)
        if previous:
            _token_by_sid.pop(previous.get("sid"), None)
        _resume_by_token[token] = {"room": room_code, "sid": sid}
        _token_by_sid[sid] = token
        _resume_generation[token] = _resume_generation.get(token, 0) + 1


def _clear_resume_for_sid(sid):
    with _resume_lock:
        token = _token_by_sid.pop(sid, None)
        if token:
            current = _resume_by_token.get(token)
            if current and current.get("sid") == sid:
                _resume_by_token.pop(token, None)
            _resume_generation[token] = _resume_generation.get(token, 0) + 1


def _resume_player(room, old_sid, new_sid):
    player = room.players.pop(old_sid, None)
    if not player:
        return False
    player.sid = new_sid
    room.players[new_sid] = player
    if room.host_sid == old_sid:
        room.host_sid = new_sid
    if room.light and room.light.get("holder") == old_sid:
        room.light["holder"] = new_sid
    for projectile in room.projectiles:
        if projectile.get("owner") == old_sid:
            projectile["owner"] = new_sid
    return True


def _create_room_with_resume(name, sid, color):
    room = _original_create_room(name, sid, color)
    token = _resume_token_from_event()
    _register_resume(token, room.code, sid)
    return room


def _join_room_with_resume(code, name, sid, color):
    token = _resume_token_from_event()
    if token:
        with _resume_lock:
            existing = dict(_resume_by_token.get(token) or {})
        if existing and existing.get("room") == code:
            room = state.get_room(code)
            old_sid = existing.get("sid")
            if room and old_sid in room.players:
                with room.lock:
                    if _resume_player(room, old_sid, sid):
                        _register_resume(token, room.code, sid)
                        return room, None

    room, error = _original_join_room(code, name, sid, color)
    if room and not error:
        _register_resume(token, room.code, sid)
    return room, error


def _expire_disconnected_player(token, sid, generation):
    socketio.sleep(RECONNECT_GRACE_SECONDS)
    with _resume_lock:
        current = _resume_by_token.get(token)
        still_current = (
            current
            and current.get("sid") == sid
            and _resume_generation.get(token, 0) == generation
        )
    if not still_current:
        return

    updated = _original_remove_player(sid)
    _clear_resume_for_sid(sid)
    if updated:
        socketio.emit("room_update", game_server._room_payload(updated), to=updated.code)


def _remove_player_with_grace(sid):
    # Explicit Leave should be immediate. Network disconnects get a grace
    # period so a phone can switch Wi-Fi/cellular without losing the match.
    if _event_name() != "disconnect":
        _clear_resume_for_sid(sid)
        return _original_remove_player(sid)

    with _resume_lock:
        token = _token_by_sid.get(sid)
        if not token:
            return _original_remove_player(sid)
        _resume_generation[token] = _resume_generation.get(token, 0) + 1
        generation = _resume_generation[token]

    room = state.get_room_by_player(sid)
    socketio.start_background_task(_expire_disconnected_player, token, sid, generation)
    return room


state.create_room = _create_room_with_resume
state.join_room = _join_room_with_resume
state.remove_player = _remove_player_with_grace

# ---------------------------------------------------------------------------
# 3-2-1-GO round starts
# ---------------------------------------------------------------------------


@socketio.on("party_start_round")
def handle_party_start_round(_data=None):
    game_server._ensure_world_loop()
    host_sid = request.sid
    room = state.get_room_by_player(host_sid)
    if not room:
        game_server.emit("server_error", {"message": "Room not found"})
        return
    if room.host_sid != host_sid:
        game_server.emit("server_error", {"message": "Only the host can start rounds"})
        return

    with room.lock:
        if room.status != "between_rounds":
            game_server.emit("server_error", {"message": "Round cannot start now"})
            return
        if room.current_round >= room.max_rounds:
            game_server.emit("server_error", {"message": "Game already finished"})
            return
        if room.task_running:
            game_server.emit("server_error", {"message": "Round already running"})
            return
        order = room.round_order or list(game_server.ROUND_SEQUENCE)
        next_index = room.current_round
        if next_index >= len(order):
            game_server.emit("server_error", {"message": "Round cannot start now"})
            return
        round_type = order[next_index]
        room.task_running = True
        room_code = room.code

    for value in ("3", "2", "1"):
        socketio.emit(
            "party_countdown",
            {"value": value, "roundType": round_type, "round": next_index + 1},
            to=room_code,
        )
        socketio.sleep(0.72)

    room = state.get_room(room_code)
    if not room:
        return
    with room.lock:
        if room.status != "between_rounds" or room.current_round != next_index:
            room.task_running = False
            return
        room.current_round += 1
        room.round_duration = game_server.ROUND_DURATIONS.get(round_type, 55)
        game_server._setup_round(room, round_type)
        room.status = "in_round"
        room.round_ends_at = time.time() + room.round_duration
        room.task_running = True
        payload = game_server._room_payload(room)
        round_number = room.current_round

    socketio.emit(
        "party_countdown",
        {"value": "GO!", "roundType": round_type, "round": round_number},
        to=room_code,
    )
    socketio.emit("round_started", payload, to=room_code)
    socketio.start_background_task(game_server._run_round_timer, room_code, round_number)

# Cut world-state broadcast bandwidth roughly in half while preserving the
# authoritative 60 Hz simulation. 30 Hz state updates still feel smooth in a
# browser game and scale much better toward 16 players.
_original_socketio_emit = socketio.emit
_world_emit_count = {}


def _optimized_emit(event, *args, **kwargs):
    if event == "world_state":
        room_code = kwargs.get("to") or kwargs.get("room") or "_global"
        count = _world_emit_count.get(room_code, 0) + 1
        _world_emit_count[room_code] = count
        if count % 2:
            return None
    return _original_socketio_emit(event, *args, **kwargs)


socketio.emit = _optimized_emit

# ---------------------------------------------------------------------------
# React SPA serving
# ---------------------------------------------------------------------------


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_client(path):
    if path:
        candidate = os.path.join(CLIENT_DIST, path)
        if os.path.isfile(candidate):
            return send_from_directory(CLIENT_DIST, path)
    return send_from_directory(CLIENT_DIST, "index.html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    socketio.run(app, host="0.0.0.0", port=port)
