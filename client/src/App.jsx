import { useEffect, useMemo, useRef, useState } from "react";
import { io } from "socket.io-client";
import GameCanvas from "./GameCanvas.jsx";
import Joystick from "./Joystick.jsx";

const SERVER_URL = import.meta.env.VITE_SERVER_URL || "http://localhost:5000";

const defaultName = "";
const PLAYER_COLORS = [
  { id: "red", label: "Red", hex: "#e53935" },
  { id: "orange", label: "Orange", hex: "#fb8c00" },
  { id: "yellow", label: "Yellow", hex: "#fdd835" },
  { id: "lime", label: "Lime", hex: "#c0ca33" },
  { id: "green", label: "Green", hex: "#43a047" },
  { id: "teal", label: "Teal", hex: "#00897b" },
  { id: "cyan", label: "Cyan", hex: "#00acc1" },
  { id: "blue", label: "Blue", hex: "#1e88e5" },
  { id: "indigo", label: "Indigo", hex: "#3949ab" },
  { id: "purple", label: "Purple", hex: "#8e24aa" },
  { id: "magenta", label: "Magenta", hex: "#d81b60" },
  { id: "pink", label: "Pink", hex: "#f06292" },
  { id: "brown", label: "Brown", hex: "#6d4c41" },
  { id: "gray", label: "Gray", hex: "#546e7a" },
  { id: "black", label: "Black", hex: "#263238" },
  { id: "white", label: "White", hex: "#ffffff" }
].map((color) => ({
  ...color,
  sprite: `/assets/pixel/players/player-${color.id}.svg`
}));

const COLOR_LOOKUP = PLAYER_COLORS.reduce((acc, color) => {
  acc[color.id] = color;
  return acc;
}, {});

const MUSIC_TRACKS = {
  menu: "/assets/audio/menu.wav",
  lobby: "/assets/audio/lobby.wav",
  trails: "/assets/audio/round-trails.wav",
  snowball: "/assets/audio/round-snowball.wav",
  light: "/assets/audio/round-light.wav",
  ice: "/assets/audio/round-ice.wav",
  survival: "/assets/audio/round-survival.wav"
};

const SFX_TRACKS = {
  whoosh: "/assets/audio/whoosh.wav",
  collect: "/assets/audio/collect.wav"
};
const SFX_VOLUME = 0.5;

const roundName = (roundType) => {
  switch (roundType) {
    case "survival":
      return "Round 5 - Survival";
    case "snowball":
      return "Round 2 - Snowball Fight";
    case "light":
      return "Round 3 - Carry the Light";
    case "ice":
      return "Round 4 - Ice Slide";
    case "trails":
      return "Round 1 - Glow Trails";
    case "bonus":
      return "Bonus Round - Tap";
    default:
      return "Lobby";
  }
};

const roundLabel = (roundType) => {
  switch (roundType) {
    case "survival":
      return "Survival";
    case "snowball":
      return "Snowball Fight";
    case "light":
      return "Carry the Light";
    case "ice":
      return "Ice Slide";
    case "trails":
      return "Glow Trails";
    case "bonus":
      return "Bonus Tap";
    default:
      return "Lobby";
  }
};

const roundInstruction = (roundType) => {
  switch (roundType) {
    case "survival":
      return "Dodge falling snowflakes and grab candy for points.";
    case "snowball":
      return "Players are separated into two teams. Players have three health. Throw snowballs to eliminate the other team. Watch for big snowballs crossing the map.";
    case "light":
      return "The christmas light will spawn randomly on the map. Hold the light to score up to twenty seconds; pass it to nearby players. And travel near the light holder for points. If hit, it drops.";
    case "ice":
      return "Stay alive on the slope. Avoid trees; points each second.";
    case "trails":
      return "Fill the map with your color. Avoid other trails to survive.";
    case "bonus":
      return "Tap fast to rack up points.";
    default:
      return "Get ready for the next round.";
  }
};

const formatTime = (seconds) => {
  if (seconds <= 0) return "0";
  return String(seconds);
};

const normalizeCode = (value) => value.replace(/\s+/g, "").toUpperCase();

const roomToWorld = (room) => {
  if (!room) return null;
  return {
    width: room.width || 960,
    height: room.height || 540,
    players: room.players || [],
    projectiles: [],
    monsterProjectiles: [],
    monsters: [],
    decorations: [],
    hazards: [],
    gifts: [],
    walls: [],
    trails: [],
    light: {}
  };
};

const mergeWorldWithRoom = (prevWorld, room) => {
  if (!room) return prevWorld;
  const base = prevWorld || roomToWorld(room);
  return {
    ...base,
    width: room.width || base.width,
    height: room.height || base.height,
    players: room.players || base.players || []
  };
};

export default function App() {
  const socketRef = useRef(null);
  const inputRef = useRef({ x: 0, y: 0 });
  const audioRef = useRef(null);
  const currentTrackRef = useRef("");
  const sfxRef = useRef({
    whoosh: { pool: [], index: 0 },
    collect: { pool: [], index: 0 }
  });
  const prevGiftsRef = useRef([]);
  const [connected, setConnected] = useState(false);
  const [name, setName] = useState(defaultName);
  const [roomCode, setRoomCode] = useState("");
  const [room, setRoom] = useState(null);
  const [world, setWorld] = useState(null);
  const [youId, setYouId] = useState("");
  const [colorId, setColorId] = useState(PLAYER_COLORS[0].id);
  const [error, setError] = useState("");
  const [timeLeft, setTimeLeft] = useState(0);
  const [menuOpen, setMenuOpen] = useState(false);
  const [leaderboardOpen, setLeaderboardOpen] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [needsTap, setNeedsTap] = useState(false);
  const [announcement, setAnnouncement] = useState(null);
  const isHollyName =
    (room?.players?.find((player) => player.id === youId)?.name ?? name)
      .trim()
      .toLowerCase() === "holly";

  useEffect(() => {
    const socket = io(SERVER_URL, { transports: ["websocket", "polling"] });
    socketRef.current = socket;

    socket.on("connect", () => setConnected(true));
    socket.on("disconnect", () => setConnected(false));
    socket.on("server_error", (payload) => {
      setError(payload?.message || "Server error");
    });
    socket.on("room_joined", (payload) => {
      setRoom(payload.room);
      setYouId(payload.youId);
      setWorld((prev) => mergeWorldWithRoom(prev, payload.room));
      setError("");
    });
    socket.on("room_update", (payload) => {
      setRoom(payload.room);
      setWorld((prev) => mergeWorldWithRoom(prev, payload.room));
    });
    socket.on("world_state", (payload) => {
      setWorld(payload.world);
      setRoom((prev) => {
        if (!payload.room) return prev;
        return { ...payload.room, players: payload.world.players };
      });
    });
    socket.on("round_started", (payload) => {
      setRoom(payload.room);
    });
    socket.on("round_ended", (payload) => {
      setRoom(payload.room);
    });
    socket.on("game_over", (payload) => {
      setRoom(payload.room);
    });
    socket.on("announcement", (payload) => {
      const message = payload?.message;
      if (!message) return;
      setAnnouncement({ message, duration: payload?.duration || 3 });
    });

    return () => socket.disconnect();
  }, []);

  useEffect(() => {
    if (!room?.roundEndsAt) {
      setTimeLeft(0);
      return;
    }
    const tick = () => {
      const remaining = Math.max(0, Math.ceil(room.roundEndsAt - Date.now() / 1000));
      setTimeLeft(remaining);
    };
    tick();
    const id = setInterval(tick, 200);
    return () => clearInterval(id);
  }, [room?.roundEndsAt]);

  useEffect(() => {
    if (!room) return undefined;
    const id = setInterval(() => {
      const current = inputRef.current;
      emit("player_input", { x: current.x, y: current.y });
    }, 50);
    return () => clearInterval(id);
  }, [room?.code]);

  const trackSrc = useMemo(() => {
    if (!room) return MUSIC_TRACKS.menu;
    if (room.status === "lobby") return MUSIC_TRACKS.lobby;
    const roundType = room.roundType || "lobby";
    return MUSIC_TRACKS[roundType] || MUSIC_TRACKS.lobby;
  }, [room?.roundType, room?.status]);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio || !trackSrc) return;
    if (currentTrackRef.current !== trackSrc) {
      currentTrackRef.current = trackSrc;
      audio.src = trackSrc;
      audio.load();
    }
    audio.loop = true;
    audio.volume = 0.5;
    audio.muted = isMuted;
    const playPromise = audio.play();
    if (playPromise && typeof playPromise.catch === "function") {
      playPromise.catch(() => setNeedsTap(true));
    }
  }, [trackSrc, isMuted]);

  useEffect(() => {
    const makePool = (src, size = 4) =>
      Array.from({ length: size }, () => {
        const audio = new Audio(src);
        audio.preload = "auto";
        audio.volume = SFX_VOLUME;
        return audio;
      });
    const whooshPool = makePool(SFX_TRACKS.whoosh, 4);
    const collectPool = makePool(SFX_TRACKS.collect, 3);
    sfxRef.current = {
      whoosh: { pool: whooshPool, index: 0 },
      collect: { pool: collectPool, index: 0 }
    };
    return () => {
      [...whooshPool, ...collectPool].forEach((audio) => {
        audio.pause();
        audio.src = "";
      });
    };
  }, []);

  useEffect(() => {
    Object.values(sfxRef.current).forEach((entry) => {
      if (!entry.pool) return;
      entry.pool.forEach((audio) => {
        audio.muted = isMuted;
        audio.volume = SFX_VOLUME;
      });
    });
  }, [isMuted]);

  useEffect(() => {
    if (!needsTap) return;
    const resume = () => {
      const audio = audioRef.current;
      if (!audio) return;
      audio.muted = isMuted;
      audio.play().then(() => setNeedsTap(false)).catch(() => {});
    };
    window.addEventListener("pointerdown", resume);
    return () => window.removeEventListener("pointerdown", resume);
  }, [needsTap, isMuted]);

  const you = useMemo(() => {
    return room?.players?.find((player) => player.id === youId);
  }, [room?.players, youId]);

  useEffect(() => {
    if (you?.color && you.color !== colorId) {
      setColorId(you.color);
    }
  }, [you?.color, colorId]);

  useEffect(() => {
    if (!isHollyName) return;
    if (colorId !== "black") return;
    const fallback = PLAYER_COLORS.find((color) => color.id !== "black")?.id;
    if (fallback) {
      setColorId(fallback);
    }
  }, [colorId, isHollyName]);

  useEffect(() => {
    if (!you || !room || !isHollyName) return;
    if (you.color !== "black") return;
    const taken = new Set(
      room.players.filter((player) => player.id !== youId).map((player) => player.color)
    );
    const fallback = PLAYER_COLORS.find(
      (color) => color.id !== "black" && !taken.has(color.id)
    )?.id;
    if (fallback) {
      setColorId(fallback);
      emit("set_color", { color: fallback });
    }
  }, [you, room, youId, isHollyName]);

  useEffect(() => {
    if (!announcement) return undefined;
    const id = setTimeout(() => setAnnouncement(null), announcement.duration * 1000);
    return () => clearTimeout(id);
  }, [announcement]);

  const sortedPlayers = useMemo(() => {
    if (!room?.players) return [];
    return [...room.players].sort((a, b) => {
      if (b.score !== a.score) return b.score - a.score;
      return b.roundScore - a.roundScore;
    });
  }, [room?.players]);

  const takenColors = useMemo(() => {
    if (!room?.players) return new Set();
    return new Set(
      room.players.filter((player) => player.id !== youId).map((player) => player.color)
    );
  }, [room?.players, youId]);

  const resetState = () => {
    setRoom(null);
    setWorld(null);
    setYouId("");
    setError("");
    setAnnouncement(null);
    setMenuOpen(false);
    setLeaderboardOpen(false);
    inputRef.current = { x: 0, y: 0 };
  };

  const emit = (event, payload) => {
    if (!socketRef.current) return;
    socketRef.current.emit(event, payload);
  };

  const handleCreate = () => {
    setError("");
    emit("create_room", { name, color: colorId });
  };

  const handleJoin = () => {
    const code = normalizeCode(roomCode);
    setError("");
    emit("join_room", { name, room: code, color: colorId });
  };

  const handleReadyToggle = () => {
    emit("set_ready", { ready: !you?.ready });
  };

  const handleStart = () => {
    emit("start_game");
  };

  const toggleMute = () => {
    setIsMuted((prev) => !prev);
  };

  const playSfx = (name) => {
    const entry = sfxRef.current[name];
    if (!entry || !entry.pool || entry.pool.length === 0) return;
    const index = entry.index % entry.pool.length;
    entry.index += 1;
    const audio = entry.pool[index];
    audio.currentTime = 0;
    audio.muted = isMuted;
    audio.volume = SFX_VOLUME;
    audio.play().catch(() => {});
  };
  const playWhoosh = () => playSfx("whoosh");
  const playCollect = () => playSfx("collect");

  const handleAddAi = () => {
    emit("add_ai");
  };

  const handleRemoveAi = () => {
    emit("remove_ai");
  };

  const handleStartRound = () => {
    emit("start_round");
  };

  const handleAction = () => {
    emit("action");
    if (!room) return;
    if (room.status === "finished") return;
    const roundType = room.roundType;
    const isThrowRound =
      room.status === "lobby" ||
      room.status === "between_rounds" ||
      roundType === "snowball" ||
      roundType === "maze" ||
      roundType === "light" ||
      roundType === "survival" ||
      roundType === "ice";
    if (isThrowRound && !(roundType === "light" && you?.hasLight)) {
      playWhoosh();
    }
  };

  const handleLeave = () => {
    emit("leave_room");
    resetState();
  };

  const handleColorPick = (color) => {
    setError("");
    if (isHollyName && color === "black") {
      return;
    }
    setColorId(color);
    if (room?.status === "lobby") {
      emit("set_color", { color });
    }
  };

  const handleJoystick = (x, y) => {
    inputRef.current = { x, y };
  };

  const isHost = room?.hostId === youId;
  const nextRound = room ? Math.min(room.currentRound + 1, room.maxRounds) : 1;
  const nextRoundType = room?.nextRoundType || room?.roundType;
  const waitingForHost = room?.status === "between_rounds";
  const inLobby = room?.status === "lobby";
  const topThree = sortedPlayers.slice(0, 3);
  const youPlacement = sortedPlayers.findIndex((player) => player.id === youId) + 1;

  const actionLabel = (() => {
    if (!room) return "Action";
    if (room.status === "lobby") return "Throw";
    if (room.roundType === "snowball" || room.roundType === "light")
      return "Throw";
    if (room.roundType === "ice" || room.roundType === "survival")
      return "Throw";
    if (room.roundType === "trails") return "Trail";
    if (room.roundType === "bonus") return "Tap!";
    return "Action";
  })();

  const actionDisabled = room?.roundType === "trails";

  useEffect(() => {
    const gifts = world?.gifts || [];
    const prevGifts = prevGiftsRef.current || [];
    prevGiftsRef.current = gifts;
    if (!room || room.status !== "in_round") return;
    if (!youId) return;
    if (!prevGifts.length || gifts.length >= prevGifts.length) return;
    const youPlayer = world?.players?.find((player) => player.id === youId);
    if (!youPlayer) return;
    const giftMap = new Map(gifts.map((gift) => [gift.id, gift]));
    const removed = prevGifts.filter((gift) => !giftMap.has(gift.id));
    const nearCollected = removed.some((gift) => {
      const dx = (gift.x ?? 0) - (youPlayer.x ?? 0);
      const dy = (gift.y ?? 0) - (youPlayer.y ?? 0);
      return dx * dx + dy * dy < 1600;
    });
    if (nearCollected) {
      playCollect();
    }
  }, [world?.gifts, world?.players, room?.status, youId]);

  return (
    <div className="app">
      <audio ref={audioRef} preload="auto" playsInline />
      {!room && (
        <main className="card fade-in lobby-card">
          <div className="lobby-grid">
            <div className="lobby-left">
              <h1>Christmas Sprint</h1>
              <p className="subtitle">A Christmas Competition.</p>

              <label className="field">
                <span>Your name</span>
                <input
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  placeholder="Santa"
                  maxLength={16}
                />
              </label>

              <label className="field">
                <span>Room code</span>
                <input
                  value={roomCode}
                  onChange={(event) => setRoomCode(event.target.value)}
                  placeholder="ABCD"
                  maxLength={6}
                />
              </label>

              <div className="button-row">
                <button className="primary" onClick={handleCreate}>
                  Create room
                </button>
                <button className="secondary" onClick={handleJoin}>
                  Join room
                </button>
              </div>

              {error && <div className="error">{error}</div>}
            </div>

            <div className="lobby-right">
              <div className="color-section">
                <div className="section-title">Choose your color</div>
                <div className="color-grid">
                  {PLAYER_COLORS.map((color) => {
                    const selected = color.id === colorId;
                    const disabledForHolly = isHollyName && color.id === "black";
                    return (
                      <button
                        key={color.id}
                        type="button"
                        className={selected ? "color-option selected" : "color-option"}
                        onClick={() => handleColorPick(color.id)}
                        disabled={disabledForHolly}
                        aria-pressed={selected}
                      >
                        <img src={color.sprite} alt="" className="player-avatar" />
                        <span>{color.label}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        </main>
      )}

      {room && (
        <div className="game-shell">
          <GameCanvas world={world} room={room} youId={youId} roundType={room.roundType} />

          <div className="hud top-left">
            <div className="hud-title">{roundName(room?.roundType)}</div>
            <div className="hud-sub">
              Room {room.code} · {connected ? "Live" : "Offline"}
            </div>
          </div>

          <div className="hud top-center">
            <div className="round-chip">
              Round {room.currentRound} / {room.maxRounds}
            </div>
            {room.roundEndsAt > 0 && <div className="timer-chip">{formatTime(timeLeft)}s</div>}
            {announcement && (
              <div className="announcement-banner">{announcement.message}</div>
            )}
          </div>

          <div className="hud top-right">
            <div className="hud-header">
              <button className="menu-button" onClick={() => setLeaderboardOpen(true)}>
                Leaderboard
              </button>
              <button className="menu-button" onClick={() => setMenuOpen(true)}>
                Menu
              </button>
            </div>
          </div>

          {inLobby && (
            <>
              {menuOpen && (
                <div className="menu-overlay" onClick={() => setMenuOpen(false)}>
                <div className="menu-card" onClick={(event) => event.stopPropagation()}>
                    <div className="menu-header">
                      <div className="menu-title">Lobby Menu</div>
                      <button
                        className="menu-close"
                        type="button"
                        onClick={() => setMenuOpen(false)}
                        aria-label="Close menu"
                      >
                        ×
                      </button>
                    </div>
                    <div className="menu-actions">
                      <button className="secondary" onClick={handleReadyToggle}>
                        {you?.ready ? "Unready" : "Ready up"}
                      </button>
                      <button className="secondary" onClick={toggleMute} aria-pressed={isMuted}>
                        {isMuted ? "Unmute music" : "Mute music"}
                      </button>
                      {isHost && (
                        <>
                          <button className="primary" onClick={handleStart}>
                            Start game
                          </button>
                          <button className="secondary" onClick={handleAddAi}>
                            Add AI
                          </button>
                          <button className="ghost" onClick={handleRemoveAi}>
                            Remove AI
                          </button>
                        </>
                      )}
                      <button className="ghost" onClick={handleLeave}>
                        Leave
                      </button>
                    </div>

                    <div className="color-section compact">
                      <div className="section-title">Pick your color</div>
                      <div className="color-grid">
                        {PLAYER_COLORS.map((color) => {
                          const selected = you?.color === color.id || color.id === colorId;
                          const takenByOther = takenColors.has(color.id);
                          const disabledForHolly = isHollyName && color.id === "black";
                          const disabled = (takenByOther && !selected) || disabledForHolly;
                          return (
                            <button
                              key={color.id}
                              type="button"
                              className={selected ? "color-option selected" : "color-option"}
                              onClick={() => handleColorPick(color.id)}
                              disabled={disabled}
                              aria-pressed={selected}
                            >
                              <img src={color.sprite} alt="" className="player-avatar" />
                              <span>{color.label}</span>
                            </button>
                          );
                        })}
                      </div>
                    </div>
                    {error && <div className="error">{error}</div>}
                  </div>
                </div>
              )}
            </>
          )}

          {waitingForHost && (
            <div className="overlay">
              <div className="overlay-card">
                <div className="overlay-title">Next Round: {roundLabel(nextRoundType)}</div>
                <div className="overlay-sub">{roundInstruction(nextRoundType)}</div>
                <div className="overlay-sub">Waiting for host · Start round {nextRound} when ready.</div>
                {isHost && room.currentRound < room.maxRounds && (
                  <button className="primary" onClick={handleStartRound}>
                    Start round {nextRound}
                  </button>
                )}
              </div>
            </div>
          )}

          {room.status === "finished" && (
            <div className="overlay">
              <div className="final-card">
                <div className="final-header">
                  <div>
                    <div className="final-title">Final Results</div>
                    <div className="final-sub">
                      {youPlacement ? `You placed #${youPlacement}` : "Thanks for playing!"}
                    </div>
                  </div>
                  <img
                    src="/assets/pixel/trophy.svg"
                    alt=""
                    className="trophy-icon"
                  />
                </div>

                <div className="podium">
                  {topThree.map((player, index) => (
                    <div key={player.id} className={`podium-spot place-${index + 1}`}>
                      <div className="podium-rank">#{index + 1}</div>
                      <img
                        src={COLOR_LOOKUP[player.color]?.sprite}
                        alt=""
                        className="player-avatar podium-avatar"
                      />
                      <div className="podium-name">{player.name}</div>
                      <div className="podium-score">{player.score} pts</div>
                    </div>
                  ))}
                </div>

                <div className="final-list">
                  {sortedPlayers.map((player, index) => (
                    <div key={player.id} className="final-row">
                      <span className="final-rank">#{index + 1}</span>
                      <span className="player-name">
                        <img
                          src={COLOR_LOOKUP[player.color]?.sprite}
                          alt=""
                          className="player-avatar"
                        />
                        {player.name}
                      </span>
                      <span className="final-score">{player.score} pts</span>
                    </div>
                  ))}
                </div>

                <div className="final-actions">
                  <button className="primary" onClick={handleLeave}>
                    Back to home
                  </button>
                </div>
              </div>
            </div>
          )}

          {menuOpen && !inLobby && (
            <div className="menu-overlay" onClick={() => setMenuOpen(false)}>
              <div className="menu-card" onClick={(event) => event.stopPropagation()}>
                <div className="menu-header">
                  <div className="menu-title">Menu</div>
                  <button
                    className="menu-close"
                    type="button"
                    onClick={() => setMenuOpen(false)}
                    aria-label="Close menu"
                  >
                    ×
                  </button>
                </div>
                <div className="menu-actions">
                  <button className="secondary" onClick={toggleMute} aria-pressed={isMuted}>
                    {isMuted ? "Unmute music" : "Mute music"}
                  </button>
                  <button className="ghost" onClick={handleLeave}>
                    Leave game
                  </button>
                </div>
              </div>
            </div>
          )}

          {leaderboardOpen && (
            <div className="menu-overlay" onClick={() => setLeaderboardOpen(false)}>
              <div className="menu-card" onClick={(event) => event.stopPropagation()}>
                <div className="menu-header">
                  <div className="menu-title">Leaderboard</div>
                  <button
                    className="menu-close"
                    type="button"
                    onClick={() => setLeaderboardOpen(false)}
                    aria-label="Close leaderboard"
                  >
                    ×
                  </button>
                </div>
                <div className="score-list">
                  {sortedPlayers.map((player) => (
                    <div key={player.id} className="score-row">
                      <span className="player-name">
                        <img
                          src={COLOR_LOOKUP[player.color]?.sprite}
                          alt=""
                          className="player-avatar"
                        />
                        {player.name}
                      </span>
                      {inLobby ? (
                        <span className={player.ready ? "ready-pill ready" : "ready-pill"}>
                          {player.ready ? "Ready" : "Not ready"}
                        </span>
                      ) : (
                        <span className="score-value">{player.score}</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {error && !inLobby && <div className="toast error">{error}</div>}

          <div className="hud bottom-left">
            <Joystick onMove={handleJoystick} onAction={handleAction} />
          </div>

          <div className="hud bottom-right">
            <button
              className="action-button"
              onPointerDown={handleAction}
              disabled={actionDisabled}
            >
              {actionLabel}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
