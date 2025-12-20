import math
import os
import random
import threading
import time

from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room, leave_room

from game_state import GameState

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
state = GameState()

ROUND_SEQUENCE = ["survival", "snowball", "light", "ice", "maze"]
ROUND_DURATIONS = {
    "survival": 45,
    "snowball": 120,
    "light": 120,
    "ice": 45,
    "maze": 75,
    "bonus": 10,
}
BONUS_CHANCE = 0.4

PLAYER_SPEED = 180.0
SURVIVAL_SPEED = 160.0
PROJECTILE_SPEED = 420.0
PROJECTILE_LIFETIME = 2.2
PLAYER_RADIUS = 14.0
PROJECTILE_RADIUS = 6.0
HAZARD_RADIUS = 14.0
GIFT_RADIUS = 12.0
FIREBALL_RADIUS = 7.0
FIREBALL_SPEED = 260.0
FIREBALL_DAMAGE = 5.0
ICE_ACCEL = 260.0
ICE_FRICTION = 0.88
ICE_SURVIVE_POINTS = 1
ICE_SCROLL_SPEED = 240.0
ICE_STRAFE_SPEED = 180.0
ICE_TREE_TARGET = 70
ICE_TREE_BUFFER = 160.0
ICE_TREE_SAFE_RADIUS = 80.0
ICE_PLAYER_Y = 0.6
ICE_FLAG_TARGET = 18
ICE_FLAG_POINTS = 10
YETI_SPEED = 210.0
YETI_RADIUS = 18.0
YETI_SPAWN_INTERVAL = 12.0
YETI_SPAWN_DELAY = 6.0
TREE_RADIUS = 22.0
TREE_SIZES = {
    "small": {"draw": 32, "radius": 16},
    "medium": {"draw": 48, "radius": 22},
    "large": {"draw": 64, "radius": 28},
}

BASE_WIDTH = 960
BASE_HEIGHT = 540
ICE_WIDTH = 2400
ICE_HEIGHT = 1600
LARGE_WIDTH = 6000
LARGE_HEIGHT = 3600

SURVIVAL_GIFT_POINTS = 5
MAZE_GIFT_POINTS = 10

MONSTER_TYPES = {
    "small": {"hp": 1, "speed": 110.0, "points": 3},
    "medium": {"hp": 2, "speed": 85.0, "points": 6},
    "big": {"hp": 4, "speed": 70.0, "points": 10},
}

world_task_started = False
world_task_lock = threading.Lock()


def _safe_name(raw_name):
    name = (raw_name or "").strip()
    if not name:
        return "Player"
    return name[:16]


def _room_payload(room):
    return {"room": state.serialize_room(room)}


def _world_payload(room):
    players = []
    for player in room.players.values():
        players.append(
            {
                "id": player.sid,
                "name": player.name,
                "color": player.color,
                "x": player.x,
                "y": player.y,
                "alive": player.alive,
                "team": player.team,
                "hasLight": player.has_light,
                "fx": player.facing_x,
                "fy": player.facing_y,
                "moving": abs(player.input_x) > 0.1 or abs(player.input_y) > 0.1,
                "score": player.score,
                "roundScore": player.round_score,
                "ringsLeft": player.rings_left,
            }
        )
    payload = {
        "room": {
            "code": room.code,
            "status": room.status,
            "currentRound": room.current_round,
            "roundType": room.round_type,
            "roundEndsAt": room.round_ends_at,
            "maxRounds": room.max_rounds,
            "hostId": room.host_sid,
        },
        "world": {
            "width": room.width,
            "height": room.height,
            "players": players,
            "projectiles": list(room.projectiles),
            "monsterProjectiles": list(room.monster_projectiles),
            "monsters": list(room.monsters),
            "decorations": list(room.decorations),
            "hazards": list(room.hazards),
            "gifts": list(room.gifts),
            "walls": list(room.walls),
            "light": dict(room.light) if room.light else {},
        },
    }
    return payload


def _clamp(value, low, high):
    return max(low, min(high, value))


def _random_spawn(room, index=0):
    margin = 50
    x = margin + (index * 70) % (room.width - margin * 2)
    y = margin + ((index * 110) % (room.height - margin * 2))
    return float(x), float(y)


def _edge_spawns(room, players, start_angle=0.0, end_angle=2 * math.pi):
    count = len(players)
    if count == 0:
        return
    margin = 80
    radius = min(room.width, room.height) / 2 - margin
    center_x = room.width / 2
    center_y = room.height / 2
    arc = end_angle - start_angle
    step = arc / max(1, count)
    offset = random.uniform(0.0, step)
    for idx, player in enumerate(players):
        angle = start_angle + offset + idx * step
        player.x = center_x + math.cos(angle) * radius
        player.y = center_y + math.sin(angle) * radius


def _tree_radius(deco):
    size = deco.get("size") or "medium"
    return TREE_SIZES.get(size, TREE_SIZES["medium"])["radius"]


def _circle_hit(ax, ay, ar, bx, by, br):
    dx = ax - bx
    dy = ay - by
    return dx * dx + dy * dy <= (ar + br) ** 2


def _player_bounds(room, x, y):
    x = _clamp(x, PLAYER_RADIUS, room.width - PLAYER_RADIUS)
    y = _clamp(y, PLAYER_RADIUS, room.height - PLAYER_RADIUS)
    return x, y


def _rect_collides_circle(rect, cx, cy, radius):
    return (
        rect["x"] - radius <= cx <= rect["x"] + rect["w"] + radius
        and rect["y"] - radius <= cy <= rect["y"] + rect["h"] + radius
    )


def _move_with_walls(room, player, dt, speed):
    dx = player.input_x
    dy = player.input_y
    new_x = player.x + dx * speed * dt
    new_y = player.y + dy * speed * dt

    if room.walls:
        test_x = new_x
        if any(_rect_collides_circle(wall, test_x, player.y, PLAYER_RADIUS) for wall in room.walls):
            test_x = player.x
        test_y = new_y
        if any(_rect_collides_circle(wall, test_x, test_y, PLAYER_RADIUS) for wall in room.walls):
            test_y = player.y
        new_x, new_y = test_x, test_y

    new_x, new_y = _player_bounds(room, new_x, new_y)
    player.x = new_x
    player.y = new_y


def _move_entity(room, x, y, dx, dy, speed, dt, radius):
    new_x = x + dx * speed * dt
    new_y = y + dy * speed * dt
    if room.walls:
        test_x = new_x
        if any(_rect_collides_circle(wall, test_x, y, radius) for wall in room.walls):
            test_x = x
        test_y = new_y
        if any(_rect_collides_circle(wall, test_x, test_y, radius) for wall in room.walls):
            test_y = y
        new_x, new_y = test_x, test_y
    new_x = _clamp(new_x, radius, room.width - radius)
    new_y = _clamp(new_y, radius, room.height - radius)
    return new_x, new_y


def _spawn_snowball(room, player):
    now = time.time()
    if now - player.last_action_ts < 0.25:
        return
    player.last_action_ts = now
    dx = player.facing_x
    dy = player.facing_y
    if abs(dx) < 0.1 and abs(dy) < 0.1:
        dx, dy = 1.0, 0.0
    mag = math.hypot(dx, dy)
    if mag == 0:
        dx, dy = 1.0, 0.0
        mag = 1.0
    dx /= mag
    dy /= mag
    projectile = {
        "id": room.next_projectile_id,
        "x": player.x + dx * (PLAYER_RADIUS + 6),
        "y": player.y + dy * (PLAYER_RADIUS + 6),
        "vx": dx * PROJECTILE_SPEED,
        "vy": dy * PROJECTILE_SPEED,
        "color": player.color,
        "owner": player.sid,
        "life": 0.0,
    }
    room.next_projectile_id += 1
    room.projectiles.append(projectile)


def _spawn_hazard(room):
    room.hazards.append(
        {
            "id": room.next_item_id,
            "x": random.uniform(40, room.width - 40),
            "y": -20,
            "vy": random.uniform(140, 220),
        }
    )
    room.next_item_id += 1


def _spawn_falling_gift(room):
    room.gifts.append(
        {
            "id": room.next_item_id,
            "x": random.uniform(40, room.width - 40),
            "y": -20,
            "vy": random.uniform(110, 180),
            "type": random.choice(["candy", "present"]),
        }
    )
    room.next_item_id += 1


def _spawn_maze_gift(room):
    for _ in range(6):
        x = random.uniform(60, room.width - 60)
        y = random.uniform(60, room.height - 60)
        if any(_rect_collides_circle(wall, x, y, GIFT_RADIUS) for wall in room.walls):
            continue
        room.gifts.append(
            {
                "id": room.next_item_id,
                "x": x,
                "y": y,
                "vy": 0.0,
                "type": random.choice(["candy", "present"]),
            }
        )
        room.next_item_id += 1
        break


def _spawn_monsters(room):
    room.monsters = []
    count = max(6, min(12, len(room.players) * 2))
    types = ["small", "medium", "big"]
    for idx in range(count):
        mtype = types[idx % len(types)]
        cfg = MONSTER_TYPES[mtype]
        for _ in range(8):
            x = random.uniform(80, room.width - 80)
            y = random.uniform(80, room.height - 80)
            if any(_rect_collides_circle(wall, x, y, 18) for wall in room.walls):
                continue
            if abs(x - room.width / 2) < 120 and abs(y - room.height / 2) < 120:
                continue
            room.monsters.append(
                {
                    "id": room.next_monster_id,
                    "type": mtype,
                    "x": x,
                    "y": y,
                    "hp": cfg["hp"],
                    "maxHp": cfg["hp"],
                    "speed": cfg["speed"],
                    "dirX": random.uniform(-1, 1),
                    "dirY": random.uniform(-1, 1),
                    "wanderUntil": time.time() + random.uniform(1.0, 3.0),
                    "lastShot": 0.0,
                }
            )
            room.next_monster_id += 1
            break


def _spawn_yeti(room, count):
    if not room.players:
        return
    player_y = _ice_player_y(room)
    for _ in range(count):
        for _ in range(8):
            x = random.uniform(80, room.width - 80)
            y = min(room.height - YETI_RADIUS, player_y + random.uniform(280.0, 520.0))
            if any(
                _circle_hit(x, y, YETI_RADIUS, player.x, player.y, PLAYER_RADIUS + 120)
                for player in room.players.values()
            ):
                continue
            room.monsters.append(
                {
                    "id": room.next_monster_id,
                    "type": "yeti",
                    "x": x,
                    "y": y,
                    "speed": YETI_SPEED,
                }
            )
            room.next_monster_id += 1
            break


def _spawn_fireball(room, monster, target_x, target_y):
    dx = target_x - monster["x"]
    dy = target_y - monster["y"]
    mag = math.hypot(dx, dy)
    if mag == 0:
        return
    dx /= mag
    dy /= mag
    room.monster_projectiles.append(
        {
            "id": room.next_monster_projectile_id,
            "x": monster["x"],
            "y": monster["y"],
            "vx": dx * FIREBALL_SPEED,
            "vy": dy * FIREBALL_SPEED,
            "life": 0.0,
        }
    )
    room.next_monster_projectile_id += 1


def _spawn_trees(room, count, avoid_players=None):
    room.decorations = []
    avoid_players = avoid_players or []
    for _ in range(count):
        for _ in range(8):
            x = random.uniform(80, room.width - 80)
            y = random.uniform(80, room.height - 80)
            size = random.choice(["small", "medium", "large"])
            radius = TREE_SIZES[size]["radius"]
            if any(_rect_collides_circle(wall, x, y, radius) for wall in room.walls):
                continue
            if avoid_players and any(
                _circle_hit(x, y, radius + 40, player.x, player.y, PLAYER_RADIUS) for player in avoid_players
            ):
                continue
            if abs(x - room.width / 2) < 120 and abs(y - room.height / 2) < 120:
                continue
            room.decorations.append(
                {
                    "id": room.next_decoration_id,
                    "type": "tree",
                    "x": x,
                    "y": y,
                    "size": size,
                }
            )
            room.next_decoration_id += 1
            break


def _ice_player_y(room):
    return room.height * ICE_PLAYER_Y


def _ice_tree_target(room):
    area_factor = (room.width * room.height) / (ICE_WIDTH * ICE_HEIGHT)
    return max(40, min(120, int(ICE_TREE_TARGET * area_factor)))


def _ice_flag_target(room):
    area_factor = (room.width * room.height) / (ICE_WIDTH * ICE_HEIGHT)
    return max(10, min(40, int(ICE_FLAG_TARGET * area_factor)))


def _spawn_ice_tree(room, min_y, max_y):
    alive_players = [player for player in room.players.values() if player.alive]
    for _ in range(12):
        x = random.uniform(60, room.width - 60)
        y = random.uniform(min_y, max_y)
        size = random.choice(["small", "medium", "large"])
        radius = TREE_SIZES[size]["radius"]
        if alive_players and any(
            _circle_hit(x, y, radius + ICE_TREE_SAFE_RADIUS, player.x, player.y, PLAYER_RADIUS)
            for player in alive_players
        ):
            continue
        if any(
            _circle_hit(x, y, radius + _tree_radius(deco) + 6, deco["x"], deco["y"], _tree_radius(deco))
            for deco in room.decorations
        ):
            continue
        room.decorations.append(
            {
                "id": room.next_decoration_id,
                "type": "tree",
                "x": x,
                "y": y,
                "size": size,
            }
        )
        room.next_decoration_id += 1
        break


def _spawn_ice_flag(room, min_y, max_y):
    alive_players = [player for player in room.players.values() if player.alive]
    for _ in range(12):
        x = random.uniform(60, room.width - 60)
        y = random.uniform(min_y, max_y)
        if alive_players and any(
            _circle_hit(x, y, GIFT_RADIUS + ICE_TREE_SAFE_RADIUS, player.x, player.y, PLAYER_RADIUS)
            for player in alive_players
        ):
            continue
        if any(
            _circle_hit(x, y, GIFT_RADIUS + _tree_radius(deco) + 6, deco["x"], deco["y"], _tree_radius(deco))
            for deco in room.decorations
        ):
            continue
        if any(
            _circle_hit(x, y, GIFT_RADIUS + 6, gift["x"], gift["y"], GIFT_RADIUS)
            for gift in room.gifts
        ):
            continue
        room.gifts.append(
            {
                "id": room.next_item_id,
                "x": x,
                "y": y,
                "vy": 0.0,
                "type": "flag",
            }
        )
        room.next_item_id += 1
        break


def _ice_yeti_limit(room):
    if not room.players:
        return 0
    return max(1, min(5, math.ceil(len(room.players) / 3)))


def _maze_walls(room):
    width = room.width
    height = room.height
    walls = [
        {"x": width * 0.08, "y": height * 0.08, "w": 18, "h": height * 0.8},
        {"x": width * 0.2, "y": height * 0.15, "w": 18, "h": height * 0.7},
        {"x": width * 0.32, "y": height * 0.05, "w": 18, "h": height * 0.75},
        {"x": width * 0.45, "y": height * 0.2, "w": 18, "h": height * 0.65},
        {"x": width * 0.58, "y": height * 0.08, "w": 18, "h": height * 0.7},
        {"x": width * 0.7, "y": height * 0.15, "w": 18, "h": height * 0.72},
        {"x": width * 0.82, "y": height * 0.05, "w": 18, "h": height * 0.8},
        {"x": width * 0.1, "y": height * 0.3, "w": width * 0.18, "h": 18},
        {"x": width * 0.28, "y": height * 0.55, "w": width * 0.18, "h": 18},
        {"x": width * 0.46, "y": height * 0.38, "w": width * 0.18, "h": 18},
        {"x": width * 0.64, "y": height * 0.6, "w": width * 0.18, "h": 18},
        {"x": width * 0.2, "y": height * 0.75, "w": width * 0.22, "h": 18},
        {"x": width * 0.52, "y": height * 0.78, "w": width * 0.22, "h": 18},
        {"x": width * 0.36, "y": height * 0.22, "w": width * 0.22, "h": 18},
        {"x": width * 0.58, "y": height * 0.28, "w": width * 0.22, "h": 18},
    ]
    return walls


def _setup_round(room, round_type):
    room.projectiles = []
    room.monster_projectiles = []
    room.monsters = []
    room.decorations = []
    room.hazards = []
    room.gifts = []
    room.walls = []
    room.light = {}
    room.hazard_accum = 0.0
    room.gift_accum = 0.0
    room.round_type = round_type

    if round_type == "ice":
        room.width = ICE_WIDTH
        room.height = ICE_HEIGHT
    elif round_type in {"snowball", "maze", "light"}:
        room.width = LARGE_WIDTH
        room.height = LARGE_HEIGHT
    else:
        room.width = BASE_WIDTH
        room.height = BASE_HEIGHT

    players = list(room.players.values())

    if round_type == "snowball":
        split = max(1, math.ceil(len(players) / 2))
        for idx, player in enumerate(players):
            player.team = 0 if idx < split else 1
    else:
        for player in players:
            player.team = 0

    for idx, player in enumerate(players):
        player.alive = True
        player.has_light = False
        player.round_score = 0
        player.score_accum = 0.0
        player.energy = 0.0
        player.rings_left = 3 if round_type == "snowball" else 0
        player.input_x = 0.0
        player.input_y = 0.0
        player.facing_x = 1.0
        player.facing_y = 0.0
        player.last_action_ts = 0.0
        player.last_hit_ts = 0.0
        player.vel_x = 0.0
        player.vel_y = 0.0

        if round_type == "survival":
            spacing = room.width / (len(players) + 1)
            player.x = spacing * (idx + 1)
            player.y = room.height - 50
        else:
            player.x, player.y = _random_spawn(room, idx)
        if round_type == "ice":
            player.y = _ice_player_y(room)
        if round_type == "maze":
            player.energy = 45.0
            player.round_score = int(player.energy)
        elif round_type == "bonus":
            player.x, player.y = _random_spawn(room, idx)

    if round_type == "snowball":
        blue_team = [player for player in players if player.team == 0]
        red_team = [player for player in players if player.team == 1]
        _edge_spawns(room, blue_team, start_angle=math.pi / 2, end_angle=3 * math.pi / 2)
        _edge_spawns(room, red_team, start_angle=-math.pi / 2, end_angle=math.pi / 2)
    elif round_type in {"maze", "light"}:
        _edge_spawns(room, players)

    if round_type == "maze":
        room.walls = _maze_walls(room)
        _spawn_monsters(room)
        for _ in range(6):
            _spawn_maze_gift(room)
    if round_type == "ice":
        tree_target = _ice_tree_target(room)
        for _ in range(tree_target):
            _spawn_ice_tree(room, 0.0, room.height + ICE_TREE_BUFFER)
        flag_target = _ice_flag_target(room)
        for _ in range(flag_target):
            _spawn_ice_flag(room, 0.0, room.height + ICE_TREE_BUFFER)
    if round_type in {"snowball", "maze", "light"}:
        area_factor = (room.width * room.height) / (BASE_WIDTH * BASE_HEIGHT)
        count = max(24, min(140, int(32 * area_factor)))
        _spawn_trees(room, count)
    if round_type == "light":
        room.light = {"x": room.width / 2, "y": room.height / 2, "holder": ""}


def _update_projectiles(room, dt):
    alive_projectiles = []
    for projectile in room.projectiles:
        projectile["x"] += projectile["vx"] * dt
        projectile["y"] += projectile["vy"] * dt
        projectile["life"] += dt
        if (
            projectile["life"] > PROJECTILE_LIFETIME
            or projectile["x"] < -20
            or projectile["x"] > room.width + 20
            or projectile["y"] < -20
            or projectile["y"] > room.height + 20
        ):
            continue
        if room.walls and any(
            _rect_collides_circle(wall, projectile["x"], projectile["y"], PROJECTILE_RADIUS)
            for wall in room.walls
        ):
            continue
        if room.decorations and any(
            deco.get("type") == "tree"
            and _circle_hit(
                projectile["x"],
                projectile["y"],
                PROJECTILE_RADIUS,
                deco["x"],
                deco["y"],
                _tree_radius(deco),
            )
            for deco in room.decorations
        ):
            continue
        alive_projectiles.append(projectile)
    room.projectiles = alive_projectiles


def _remove_projectiles_on_player_hit(room):
    if not room.projectiles:
        return
    remaining = []
    for projectile in room.projectiles:
        hit = False
        for player in room.players.values():
            if _circle_hit(projectile["x"], projectile["y"], PROJECTILE_RADIUS, player.x, player.y, PLAYER_RADIUS):
                hit = True
                break
        if not hit:
            remaining.append(projectile)
    room.projectiles = remaining


def _update_lobby(room, dt):
    for player in room.players.values():
        _move_with_walls(room, player, dt, PLAYER_SPEED)


def _update_survival(room, dt):
    room.hazard_accum += dt
    room.gift_accum += dt
    while room.hazard_accum >= 0.6:
        _spawn_hazard(room)
        room.hazard_accum -= 0.6
    while room.gift_accum >= 1.8:
        _spawn_falling_gift(room)
        room.gift_accum -= 1.8

    for player in room.players.values():
        if not player.alive:
            continue
        player.x = _clamp(player.x + player.input_x * SURVIVAL_SPEED * dt, PLAYER_RADIUS, room.width - PLAYER_RADIUS)
        player.y = room.height - 50
        player.score_accum += dt
        while player.score_accum >= 1.0:
            player.score += 1
            player.round_score += 1
            player.score_accum -= 1.0

    hazards = []
    for hazard in room.hazards:
        hazard["y"] += hazard["vy"] * dt
        if hazard["y"] > room.height + 30:
            continue
        hit = False
        for player in room.players.values():
            if player.alive and _circle_hit(hazard["x"], hazard["y"], HAZARD_RADIUS, player.x, player.y, PLAYER_RADIUS):
                player.alive = False
                hit = True
                break
        if not hit:
            hazards.append(hazard)
    room.hazards = hazards

    gifts = []
    for gift in room.gifts:
        gift["y"] += gift["vy"] * dt
        if gift["y"] > room.height + 30:
            continue
        collected = False
        for player in room.players.values():
            if player.alive and _circle_hit(gift["x"], gift["y"], GIFT_RADIUS, player.x, player.y, PLAYER_RADIUS):
                player.score += SURVIVAL_GIFT_POINTS
                player.round_score += SURVIVAL_GIFT_POINTS
                collected = True
                break
        if not collected:
            gifts.append(gift)
    room.gifts = gifts


def _update_snowball(room, dt):
    for player in room.players.values():
        if not player.alive:
            continue
        _move_with_walls(room, player, dt, PLAYER_SPEED)

    _update_projectiles(room, dt)

    remaining = []
    for projectile in room.projectiles:
        hit = False
        shooter = room.players.get(projectile["owner"])
        if not shooter:
            continue
        for player in room.players.values():
            if player.sid == projectile["owner"]:
                continue
            if not player.alive:
                continue
            if player.team == shooter.team:
                continue
            if _circle_hit(projectile["x"], projectile["y"], PROJECTILE_RADIUS, player.x, player.y, PLAYER_RADIUS):
                player.rings_left = max(0, player.rings_left - 1)
                if player.rings_left == 0:
                    player.alive = False
                    shooter.score += 20
                    shooter.round_score += 20
                hit = True
                break
        if not hit:
            remaining.append(projectile)
    room.projectiles = remaining


def _update_ice(room, dt):
    scroll = ICE_SCROLL_SPEED * dt
    player_y = _ice_player_y(room)
    room.gift_accum += dt
    if not room.monsters and room.gift_accum >= YETI_SPAWN_DELAY:
        _spawn_yeti(room, 1)
        room.gift_accum = 0.0
    elif room.gift_accum >= YETI_SPAWN_INTERVAL and len(room.monsters) < _ice_yeti_limit(room):
        _spawn_yeti(room, 1)
        room.gift_accum = 0.0

    for player in room.players.values():
        if not player.alive:
            continue
        if player.input_x < -0.2:
            direction = -1.0
        elif player.input_x > 0.2:
            direction = 1.0
        else:
            direction = 0.0
        player.input_y = 1.0
        player.facing_x = direction
        player.facing_y = 1.0
        player.x = _clamp(
            player.x + direction * ICE_STRAFE_SPEED * dt, PLAYER_RADIUS, room.width - PLAYER_RADIUS
        )
        player.y = player_y
        player.score_accum += dt
        while player.score_accum >= 1.0:
            player.score += ICE_SURVIVE_POINTS
            player.round_score += ICE_SURVIVE_POINTS
            player.score_accum -= 1.0

    if room.decorations:
        for deco in room.decorations:
            deco["y"] -= scroll
        room.decorations = [deco for deco in room.decorations if deco["y"] > -ICE_TREE_BUFFER]
    target_trees = _ice_tree_target(room)
    while len(room.decorations) < target_trees:
        _spawn_ice_tree(room, room.height + ICE_TREE_BUFFER, room.height + ICE_TREE_BUFFER + room.height)

    if room.gifts:
        for gift in room.gifts:
            gift["y"] -= scroll
        room.gifts = [gift for gift in room.gifts if gift["y"] > -ICE_TREE_BUFFER]
    target_flags = _ice_flag_target(room)
    while len(room.gifts) < target_flags:
        _spawn_ice_flag(room, room.height + ICE_TREE_BUFFER, room.height + ICE_TREE_BUFFER + room.height)

    for yeti in room.monsters:
        yeti["y"] -= scroll
        target = None
        best_dist = 1e9
        for player in room.players.values():
            if not player.alive:
                continue
            dx = player.x - yeti["x"]
            dy = player.y - yeti["y"]
            dist = math.hypot(dx, dy)
            if dist < best_dist:
                best_dist = dist
                target = player
        if not target:
            continue
        dx = target.x - yeti["x"]
        dy = target.y - yeti["y"]
        mag = math.hypot(dx, dy) or 1.0
        dx /= mag
        dy /= mag
        yeti["x"], yeti["y"] = _move_entity(room, yeti["x"], yeti["y"], dx, dy, yeti["speed"], dt, YETI_RADIUS)

    if room.gifts:
        remaining_gifts = []
        for gift in room.gifts:
            collected = False
            for player in room.players.values():
                if not player.alive:
                    continue
                if _circle_hit(gift["x"], gift["y"], GIFT_RADIUS, player.x, player.y, PLAYER_RADIUS):
                    player.score += ICE_FLAG_POINTS
                    player.round_score += ICE_FLAG_POINTS
                    collected = True
                    break
            if not collected:
                remaining_gifts.append(gift)
        room.gifts = remaining_gifts

    for player in room.players.values():
        if not player.alive:
            continue
        for deco in room.decorations:
            if _circle_hit(player.x, player.y, PLAYER_RADIUS, deco["x"], deco["y"], _tree_radius(deco)):
                player.alive = False
                break
        if not player.alive:
            continue
        for yeti in room.monsters:
            if _circle_hit(yeti["x"], yeti["y"], YETI_RADIUS, player.x, player.y, PLAYER_RADIUS):
                player.alive = False
                break


def _update_maze(room, dt):
    goal_x = room.width / 2
    goal_y = room.height / 2
    now = time.time()
    room.gift_accum += dt
    if len(room.gifts) < 8 and room.gift_accum >= 2.0:
        _spawn_maze_gift(room)
        room.gift_accum = 0.0

    _update_projectiles(room, dt)

    for player in room.players.values():
        if not player.alive:
            continue
        _move_with_walls(room, player, dt, PLAYER_SPEED)
        player.energy -= dt
        if player.energy <= 0:
            player.energy = 0
            player.alive = False
        player.round_score = int(player.energy)

    gifts = []
    for gift in room.gifts:
        collected = False
        for player in room.players.values():
            if player.alive and _circle_hit(gift["x"], gift["y"], GIFT_RADIUS, player.x, player.y, PLAYER_RADIUS):
                player.score += MAZE_GIFT_POINTS
                player.round_score += MAZE_GIFT_POINTS
                collected = True
                break
        if not collected:
            gifts.append(gift)
    room.gifts = gifts

    remaining_projectiles = []
    for projectile in room.projectiles:
        hit = False
        shooter = room.players.get(projectile["owner"])
        for monster in room.monsters:
            if _circle_hit(projectile["x"], projectile["y"], PROJECTILE_RADIUS, monster["x"], monster["y"], 16):
                monster["hp"] -= 1
                if shooter:
                    points = MONSTER_TYPES[monster["type"]]["points"]
                    shooter.score += points
                    shooter.round_score += points
                hit = True
                break
        if not hit:
            remaining_projectiles.append(projectile)
    room.projectiles = remaining_projectiles

    room.monsters = [monster for monster in room.monsters if monster["hp"] > 0]

    for monster in room.monsters:
        target = None
        best_dist = 1e9
        for player in room.players.values():
            if not player.alive:
                continue
            dx = player.x - monster["x"]
            dy = player.y - monster["y"]
            dist = math.hypot(dx, dy)
            if dist < best_dist:
                best_dist = dist
                target = player
        if target and best_dist < 320:
            dx = target.x - monster["x"]
            dy = target.y - monster["y"]
            mag = math.hypot(dx, dy) or 1.0
            dx /= mag
            dy /= mag
            monster["x"], monster["y"] = _move_entity(
                room, monster["x"], monster["y"], dx, dy, monster["speed"], dt, 16
            )
            if best_dist < 280 and now - monster["lastShot"] > 1.4:
                _spawn_fireball(room, monster, target.x, target.y)
                monster["lastShot"] = now
        else:
            if now > monster["wanderUntil"]:
                monster["dirX"] = random.uniform(-1, 1)
                monster["dirY"] = random.uniform(-1, 1)
                monster["wanderUntil"] = now + random.uniform(1.0, 2.5)
            monster["x"], monster["y"] = _move_entity(
                room,
                monster["x"],
                monster["y"],
                monster["dirX"],
                monster["dirY"],
                monster["speed"] * 0.6,
                dt,
                16,
            )

        for player in room.players.values():
            if not player.alive:
                continue
            if _circle_hit(monster["x"], monster["y"], 16, player.x, player.y, PLAYER_RADIUS):
                if now - player.last_hit_ts > 0.8:
                    player.energy = max(0.0, player.energy - FIREBALL_DAMAGE)
                    player.last_hit_ts = now
                    if player.energy <= 0:
                        player.alive = False

    monster_projectiles = []
    for projectile in room.monster_projectiles:
        projectile["x"] += projectile["vx"] * dt
        projectile["y"] += projectile["vy"] * dt
        projectile["life"] += dt
        if (
            projectile["life"] > 3.0
            or projectile["x"] < -20
            or projectile["x"] > room.width + 20
            or projectile["y"] < -20
            or projectile["y"] > room.height + 20
        ):
            continue
        if any(_rect_collides_circle(wall, projectile["x"], projectile["y"], FIREBALL_RADIUS) for wall in room.walls):
            continue
        hit = False
        for player in room.players.values():
            if not player.alive:
                continue
            if _circle_hit(projectile["x"], projectile["y"], FIREBALL_RADIUS, player.x, player.y, PLAYER_RADIUS):
                player.energy = max(0.0, player.energy - FIREBALL_DAMAGE)
                if player.energy <= 0:
                    player.alive = False
                hit = True
                break
        if not hit:
            monster_projectiles.append(projectile)
    room.monster_projectiles = monster_projectiles

    for player in room.players.values():
        if player.alive and _circle_hit(player.x, player.y, PLAYER_RADIUS, goal_x, goal_y, 20):
            if player.energy > 0:
                player.score += 20
                player.round_score += 20
                player.energy = 0
                player.alive = False


def _update_light(room, dt):
    _update_projectiles(room, dt)
    for player in room.players.values():
        _move_with_walls(room, player, dt, PLAYER_SPEED)

    light = room.light
    if not light:
        return
    holder_id = light.get("holder") if light else ""

    if holder_id and holder_id in room.players:
        holder = room.players[holder_id]
        holder.has_light = True
        light["x"] = holder.x
        light["y"] = holder.y
        holder.score_accum += dt * 3
        while holder.score_accum >= 1.0:
            holder.score += 1
            holder.round_score += 1
            holder.score_accum -= 1.0
        for player in room.players.values():
            if player.sid == holder_id:
                continue
            if _circle_hit(player.x, player.y, PLAYER_RADIUS, holder.x, holder.y, PLAYER_RADIUS):
                holder.has_light = False
                player.has_light = True
                light["holder"] = player.sid
                player.score += 5
                player.round_score += 5
                break
    else:
        for player in room.players.values():
            if _circle_hit(player.x, player.y, PLAYER_RADIUS, light["x"], light["y"], 16):
                light["holder"] = player.sid
                player.has_light = True
                break
    _remove_projectiles_on_player_hit(room)


def _update_bonus(room, dt):
    for player in room.players.values():
        player.x = room.width / 2
        player.y = room.height / 2


def _world_loop():
    tick_rate = 1.0 / 20.0
    while True:
        socketio.sleep(tick_rate)
        rooms = state.list_rooms()
        now = time.time()
        for room in rooms:
            end_payload = None
            end_finished = False
            with room.lock:
                dt = now - room.last_update_ts
                if dt <= 0:
                    continue
                if dt > 0.2:
                    dt = 0.2
                room.last_update_ts = now
                room.tick += 1

                if room.status in {"lobby", "between_rounds"}:
                    _update_lobby(room, dt)
                    _update_projectiles(room, dt)
                    _remove_projectiles_on_player_hit(room)
                elif room.status == "in_round":
                    if room.round_type == "survival":
                        _update_survival(room, dt)
                    elif room.round_type == "snowball":
                        _update_snowball(room, dt)
                    elif room.round_type == "ice":
                        _update_ice(room, dt)
                    elif room.round_type == "maze":
                        _update_maze(room, dt)
                    elif room.round_type == "light":
                        _update_light(room, dt)
                    elif room.round_type == "bonus":
                        _update_bonus(room, dt)
                    if room.players and not any(player.alive for player in room.players.values()):
                        end_finished, end_payload = _finish_round(room)

                payload = _world_payload(room)
            socketio.emit("world_state", payload, to=room.code)
            if end_payload:
                if end_finished:
                    socketio.emit("game_over", end_payload, to=room.code)
                else:
                    socketio.emit("round_ended", end_payload, to=room.code)


def _ensure_world_loop():
    global world_task_started
    if world_task_started:
        return
    with world_task_lock:
        if world_task_started:
            return
        world_task_started = True
        socketio.start_background_task(_world_loop)


def _finish_round(room):
    finished = False
    if room.round_type == "light":
        holder_id = room.light.get("holder") if room.light else ""
        if holder_id and holder_id in room.players:
            holder = room.players[holder_id]
            holder.score += 10
            holder.round_score += 10
    room.round_ends_at = 0.0
    room.task_running = False
    if room.current_round >= room.max_rounds:
        room.status = "finished"
        finished = True
    else:
        room.status = "between_rounds"
    payload = _room_payload(room)
    return finished, payload


def _run_round_timer(room_code, round_number):
    while True:
        room = state.get_room(room_code)
        if not room:
            return
        with room.lock:
            if room.status != "in_round" or room.current_round != round_number:
                room.task_running = False
                return
            end_at = room.round_ends_at
        if time.time() >= end_at:
            break
        socketio.sleep(0.2)

    room = state.get_room(room_code)
    if not room:
        return
    with room.lock:
        if room.status != "in_round" or room.current_round != round_number:
            room.task_running = False
            return
        finished, payload = _finish_round(room)
    if finished:
        socketio.emit("game_over", payload, to=room_code)
    else:
        socketio.emit("round_ended", payload, to=room_code)


@socketio.on("create_room")
def handle_create_room(data):
    _ensure_world_loop()
    payload = data or {}
    name = _safe_name(payload.get("name"))
    color = (payload.get("color") or "").strip().lower()
    room = state.create_room(name, request.sid, color)
    join_room(room.code)
    emit("room_joined", {"room": state.serialize_room(room), "youId": request.sid})
    socketio.emit("room_update", _room_payload(room), to=room.code)


@socketio.on("join_room")
def handle_join_room(data):
    _ensure_world_loop()
    payload = data or {}
    code = (payload.get("room") or "").strip().upper()
    name = _safe_name(payload.get("name"))
    color = (payload.get("color") or "").strip().lower()
    if not code:
        emit("server_error", {"message": "Room code required"})
        return
    room, error = state.join_room(code, name, request.sid, color)
    if error:
        emit("server_error", {"message": error})
        return
    join_room(code)
    emit("room_joined", {"room": state.serialize_room(room), "youId": request.sid})
    socketio.emit("room_update", _room_payload(room), to=code)


@socketio.on("leave_room")
def handle_leave_room(_data=None):
    room = state.get_room_by_player(request.sid)
    if not room:
        return
    leave_room(room.code)
    updated = state.remove_player(request.sid)
    if updated:
        socketio.emit("room_update", _room_payload(updated), to=updated.code)


@socketio.on("set_ready")
def handle_set_ready(data):
    payload = data or {}
    ready = bool(payload.get("ready"))
    room = state.set_ready(request.sid, ready)
    if room:
        socketio.emit("room_update", _room_payload(room), to=room.code)


@socketio.on("set_color")
def handle_set_color(data):
    payload = data or {}
    color = (payload.get("color") or "").strip().lower()
    room, error = state.set_color(request.sid, color)
    if error:
        emit("server_error", {"message": error})
        return
    if room:
        socketio.emit("room_update", _room_payload(room), to=room.code)


@socketio.on("player_input")
def handle_player_input(data):
    _ensure_world_loop()
    payload = data or {}
    input_x = payload.get("x", 0.0)
    input_y = payload.get("y", 0.0)
    state.set_input(request.sid, input_x, input_y)


@socketio.on("action")
def handle_action(_data=None):
    _ensure_world_loop()
    room = state.get_room_by_player(request.sid)
    if not room:
        return
    with room.lock:
        player = room.players.get(request.sid)
        if not player:
            return
        if room.status in {"lobby", "between_rounds"}:
            _spawn_snowball(room, player)
            return
        if room.status != "in_round":
            return
        if room.round_type == "snowball":
            _spawn_snowball(room, player)
        elif room.round_type == "bonus":
            now = time.time()
            if now - player.last_action_ts < 0.15:
                return
            player.last_action_ts = now
            player.score += 1
            player.round_score += 1
        elif room.round_type == "light":
            _spawn_snowball(room, player)
        elif room.round_type == "maze":
            _spawn_snowball(room, player)


@socketio.on("start_game")
def handle_start_game(_data=None):
    _ensure_world_loop()
    room = state.get_room_by_player(request.sid)
    if not room:
        emit("server_error", {"message": "Room not found"})
        return
    if room.host_sid != request.sid:
        emit("server_error", {"message": "Only the host can start"})
        return
    with room.lock:
        if room.status == "in_round" or room.task_running:
            emit("server_error", {"message": "Round already running"})
            return
        for player in room.players.values():
            player.score = 0
            player.round_score = 0
            player.ready = False
            player.alive = True
            player.score_accum = 0.0
            player.has_light = False
            player.energy = 0.0
        room.status = "between_rounds"
        room.current_round = 0
        room.round_type = "lobby"
        order = list(ROUND_SEQUENCE)
        if random.random() < BONUS_CHANCE:
            order.append("bonus")
        room.round_order = order
        room.max_rounds = len(order)
        room.width = BASE_WIDTH
        room.height = BASE_HEIGHT
        room.round_ends_at = 0.0
        room.task_running = False
    socketio.emit("room_update", _room_payload(room), to=room.code)


@socketio.on("start_round")
def handle_start_round(_data=None):
    _ensure_world_loop()
    room = state.get_room_by_player(request.sid)
    if not room:
        emit("server_error", {"message": "Room not found"})
        return
    if room.host_sid != request.sid:
        emit("server_error", {"message": "Only the host can start rounds"})
        return
    with room.lock:
        if room.status != "between_rounds":
            emit("server_error", {"message": "Round cannot start now"})
            return
        if room.current_round >= room.max_rounds:
            emit("server_error", {"message": "Game already finished"})
            return
        if room.task_running:
            emit("server_error", {"message": "Round already running"})
            return
        room.current_round += 1
        order = room.round_order or list(ROUND_SEQUENCE)
        if room.current_round > len(order):
            emit("server_error", {"message": "Round cannot start now"})
            return
        round_type = order[room.current_round - 1]
        room.round_duration = ROUND_DURATIONS.get(round_type, 45)
        _setup_round(room, round_type)
        room.status = "in_round"
        room.round_ends_at = time.time() + room.round_duration
        room.task_running = True
        payload = _room_payload(room)
        round_number = room.current_round
    socketio.emit("round_started", payload, to=room.code)
    socketio.start_background_task(_run_round_timer, room.code, round_number)


@socketio.on("collect")
def handle_collect(_data=None):
    room, error = state.record_collect(request.sid)
    if not room:
        emit("server_error", {"message": "Room not found"})
        return
    if error:
        return
    socketio.emit("room_update", _room_payload(room), to=room.code)


@socketio.on("request_state")
def handle_request_state(_data=None):
    room = state.get_room_by_player(request.sid)
    if room:
        emit("room_update", _room_payload(room))


@socketio.on("disconnect")
def handle_disconnect():
    updated = state.remove_player(request.sid)
    if updated:
        socketio.emit("room_update", _room_payload(updated), to=updated.code)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@socketio.on("connect")
def handle_connect():
    _ensure_world_loop()


if __name__ == "__main__":
    _ensure_world_loop()
    port = int(os.environ.get("PORT", "5000"))
    socketio.run(app, host="0.0.0.0", port=port)
