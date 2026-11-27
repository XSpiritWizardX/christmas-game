"""Authoritative rules for the Christmas festival arenas (960 by 540)."""
from collections import deque
import math
import random

MODES = ("workshop", "raceway", "avalanche", "chaos", "candy_maze", "lake", "heist", "boss", "sleigh", "ornaments")
HEROES = ("classic", "santa", "mrs_claus", "mischief", "nutcracker", "penguin", "polar_bear", "soldier", "yeti", "tree", "queen", "knight")
SCALE = {"easy": .8, "medium": 1, "hard": 1.25}


def marker(x, y, label, radius=22):
    return dict(x=x, y=y, label=label, r=radius)


def distance(p, m):
    return math.hypot(p.x-m["x"], p.y-m["y"])


def award(p, points):
    p.round_score += points
    p.score += points


def prepare(room):
    mode = room.round_type
    f = room.festival = dict(markers=[], danger=[], hp=0, phase=1, completed=False)
    for i, p in enumerate(room.players.values()):
        p.x, p.y = 65, 70 + i % 8 * 50
        p.rings_left = 3
        p.cargo = p.checkpoint = 0
        p.last_hit_ts = -10
        p.team = i % 2 if mode == "heist" else 0
        if mode == "heist":
            p.x = 870 if p.team else 90
        if mode == "sleigh":
            a = i * math.tau / len(room.players)
            p.x, p.y = 480+155*math.cos(a), 270+155*math.sin(a)
    marks = f["markers"]
    if mode == "workshop":
        marks.extend([marker(100,270,"LOAD",40), marker(830,120,"DELIVER",48), marker(830,420,"DELIVER",48)])
    elif mode == "candy_maze":
        # A spanning tree gives every room one reachable path from every other room.
        cols, rows = 8, 5
        graph = {(x,y): [] for x in range(cols) for y in range(rows)}
        stack, seen = [(0,0)], {(0,0)}
        while stack:
            x,y = stack[-1]
            choices = [cell for cell in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)) if cell in graph and cell not in seen]
            if not choices:
                stack.pop()
                continue
            cell = random.choice(choices)
            graph[x,y].append(cell)
            graph[cell].append((x,y))
            seen.add(cell)
            stack.append(cell)
        for (x,y), links in graph.items():
            if x<cols-1 and (x+1,y) not in links:
                room.walls.append(dict(x=(x+1)*120-5,y=y*108,w=10,h=108))
            if y<rows-1 and (x,y+1) not in links:
                room.walls.append(dict(x=x*120,y=(y+1)*108-5,w=120,h=10))
        room.maze_paths = graph
        for x,y in random.sample(list(graph)[1:],8):
            marks.append(marker(x*120+60,y*108+54,"CANDY",22))
        for p in room.players.values():
            p.x,p.y = 60,54
    elif mode in ("raceway","avalanche"):
        for i in range(4):
            gap = 95 if i%2==0 else 445
            x = 180+i*180
            room.walls.append(dict(x=x,y=165 if gap==95 else 0,w=20,h=375))
            marks.append(marker(x+40,gap,"CANDY" if mode=="candy_maze" else str(i+1),35))
        marks.append(marker(895,270,"FINISH",45))
    elif mode == "heist":
        marks.extend([marker(80,270,"GREEN VAULT",55),marker(880,270,"RED VAULT",55)])
        f["stock"] = [10,10]
    elif mode == "boss":
        f["maxHp"] = f["hp"] = 8*len(room.players)
        marks.append(marker(480,270,"FROST OGRE",48))
    elif mode == "ornaments":
        for i in range(18):
            marks.append(marker(random.randint(80,880),random.randint(65,475),"SPRUCE",30))
        f["hidden"] = set(random.sample(range(18),9))
    elif mode == "lake":
        for p in room.players.values():
            p.x,p.y = 480,270


def public(room):
    return {k:v for k,v in room.festival.items() if k!="hidden"}


def action(room,p):
    if not p.alive or room.round_elapsed-p.last_action_ts < .55:
        return
    p.last_action_ts = room.round_elapsed
    f, mode = room.festival, room.round_type
    if mode=="boss" and distance(p,f["markers"][0])<100 and f["hp"]>0:
        f["hp"]-=1
        award(p,1)
        if f["hp"]==0:
            f["completed"]=True
            for ally in room.players.values():
                if ally.alive:
                    award(ally,15)
    elif mode=="sleigh":
        for q in room.players.values():
            if q is not p and q.alive and math.hypot(p.x-q.x,p.y-q.y)<80:
                a=math.atan2(q.y-p.y,q.x-p.x)
                q.vel_x+=380*math.cos(a)
                q.vel_y+=380*math.sin(a)
    elif mode=="ornaments":
        candidates=[(distance(p,m),i) for i,m in enumerate(f["markers"]) if m["label"]=="SPRUCE"]
        if candidates:
            d,i=min(candidates)
            if d<55:
                found=i in f["hidden"]
                f["markers"][i]["label"]="FOUND" if found else "EMPTY"
                if found:
                    f["hidden"].remove(i)
                    award(p,5)
                f["completed"]=not f["hidden"]
    elif mode=="heist":
        for q in room.players.values():
            if q.team!=p.team and q.cargo and distance(q,f["markers"][p.team])<130 and math.hypot(q.x-p.x,q.y-p.y)<65:
                q.cargo=0
                f["stock"][p.team]+=1


def target(room,p):
    f, mode = room.festival,room.round_type
    marks=f["markers"]
    if mode=="candy_maze":
        start = (min(7,int(p.x//120)),min(4,int(p.y//108)))
        goals = {(int(m["x"]//120),int(m["y"]//108)):m for m in marks}
        queue = deque([(start, None)])
        seen = {start}
        while queue:
            cell, first = queue.popleft()
            if cell in goals:
                if first is None:
                    return goals[cell]
                # Center on the corridor before turning at a junction.
                x,y = start
                tx,ty = first
                if tx!=x and abs(p.y-(y*108+54))>10:
                    return marker(p.x,y*108+54,"")
                if ty!=y and abs(p.x-(x*120+60))>10:
                    return marker(x*120+60,p.y,"")
                return marker(tx*120+60,ty*108+54,"")
            for nxt in room.maze_paths[cell]:
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append((nxt, first or nxt))
        return None
    if mode=="workshop":
        return marks[1+p.checkpoint%2 if p.cargo else 0]
    if mode in ("raceway","avalanche"):
        m=marks[min(p.checkpoint,4)]
        if p.checkpoint<4 and p.x<m["x"]-64 and abs(p.y-m["y"])>18:
            return marker(p.x,m["y"],"")
        return m
    if mode=="heist":
        return marks[p.team if p.cargo else 1-p.team]
    if mode=="boss":
        return marks[0]
    if mode=="ornaments":
        return min((m for m in marks if m["label"]=="SPRUCE"),key=lambda m:distance(p,m),default=None)
    if mode=="sleigh":
        if math.hypot(p.x-480,p.y-270)>175:
            return marker(480,270,"")
        enemies=[q for q in room.players.values() if q is not p and q.alive]
        if enemies:
            q=min(enemies,key=lambda q:math.hypot(q.x-p.x,q.y-p.y))
            return marker(q.x,q.y,"")
    if mode=="lake":
        return min(marks,key=lambda m:distance(p,m))
    if mode=="chaos":
        danger=min(f["danger"],key=lambda m:distance(p,m))
        a=math.atan2(p.y-danger["y"],p.x-danger["x"])
        return marker(max(35,min(925,p.x+80*math.cos(a))),max(35,min(505,p.y+80*math.sin(a))),"")
    return None


def step(room,dt,move):
    f,mode,t=room.festival,room.round_type,room.round_elapsed
    pace=SCALE[room.difficulty]
    z=t*pace
    if mode=="lake":
        f["markers"]=[marker(480+180*math.sin(z*.42+i),270+120*math.sin(z*.55+2*i),"FLOE",85) for i in range(4) if (int(z/4)+1)%4!=i]
    elif mode=="chaos":
        f["danger"]=[marker(480+410*math.sin(z*.6+i*2),270+205*math.cos(z*(.5+int(z/6)%3*.15)+i),"STORM",65) for i in range(5)]
    elif mode=="avalanche":
        f["front"]=min(960,z*17)
    elif mode=="boss":
        f["phase"]=1+min(2,int(3*(1-f["hp"]/f["maxHp"])))
        phase=f["phase"]
        f["danger"]=[marker(480+(85+75*math.sin(z))*math.cos(z+i*math.tau/(phase*2)),270+(85+75*math.sin(z))*math.sin(z+i*math.tau/(phase*2)),"FROST",27) for i in range(phase*2)]
    for p in room.players.values():
        if not p.alive:
            continue
        if p.is_bot and t>=p.ai_next_decision_ts:
            p.ai_next_decision_ts=t+{"easy":.65,"medium":.32,"hard":.14}[room.ai_difficulty]
            m=target(room,p)
            if m:
                dx,dy=m["x"]-p.x,m["y"]-p.y
                length=max(1,math.hypot(dx,dy))
                p.input_x,p.input_y=dx/length,dy/length
            action(room,p)
        move(room,p,dt,230 if mode=="raceway" else 180)
        if mode=="candy_maze":
            candy=next((m for m in f["markers"] if distance(p,m)<25),None)
            if candy:
                f["markers"].remove(candy)
                award(p,4)
                f["completed"]=not f["markers"]
        if mode=="sleigh":
            p.x+=p.vel_x*dt
            p.y+=p.vel_y*dt
            p.vel_x*=math.exp(-2.3*dt)
            p.vel_y*=math.exp(-2.3*dt)
        hazard=any(distance(p,m)<m["r"] for m in f["danger"])
        if mode=="lake":
            hazard=not any(distance(p,m)<m["r"] for m in f["markers"])
        if mode=="avalanche":
            hazard=p.x<f["front"]
        if hazard and t-p.last_hit_ts>=1.5:
            p.last_hit_ts=t
            p.rings_left-=1
            p.alive=p.rings_left>0
        if mode=="sleigh" and math.hypot(p.x-480,p.y-270)>240:
            p.alive=False
        if not p.alive:
            continue
        if mode in ("lake","chaos","sleigh","avalanche") and int(t)!=int(max(0,t-dt)):
            award(p,1)
        if mode in ("workshop","heist"):
            m=target(room,p)
            if distance(p,m)<m["r"]:
                if p.cargo:
                    p.cargo=0
                    award(p,5)
                    p.checkpoint+=1
                    if mode=="heist":
                        f["stock"][p.team]+=1
                elif mode=="workshop" or f["stock"][1-p.team]>0:
                    p.cargo=1
                    if mode=="heist":
                        f["stock"][1-p.team]-=1
        if mode in ("raceway","avalanche"):
            m=f["markers"][p.checkpoint]
            if distance(p,m)<m["r"]:
                p.checkpoint+=1
                award(p,10 if p.checkpoint==5 else 2)
                if p.checkpoint==5:
                    f["completed"]=True
                    break
    if mode=="sleigh" and len(room.players)>1:
        survivors=[p for p in room.players.values() if p.alive]
        if len(survivors)==1:
            award(survivors[0],15)
            f["completed"]=True
