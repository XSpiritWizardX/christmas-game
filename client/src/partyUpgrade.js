import { Socket } from "socket.io-client";

const INSTALL_FLAG = Symbol.for("christmas-sprint-party-upgrade");
const RESUME_TOKEN_KEY = "xmasResumeToken";
const RESUME_SESSION_KEY = "xmasResumeSession";
const OWNED_KEY = "xmasOwnedCosmetics";
const ROUND_NAMES = {
  survival: "Survival",
  snowball: "Snowball Fight",
  hunt: "Monster Hunt",
  thin_ice: "Thin Ice",
  light: "Carry the Light",
  ice: "Ice Slide",
  trails: "Glow Trails",
  hill: "King of the Hill",
  bonus: "Bonus Tap"
};

const originalEmit = Socket.prototype.emit;
const originalConnect = Socket.prototype.connect;
const socketMeta = new WeakMap();
let centerTimer = 0;
let scoreTimer = 0;

const prefersReducedMotion = () =>
  window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches === true;

function makeResumeToken() {
  let token = localStorage.getItem(RESUME_TOKEN_KEY);
  if (token) return token;
  token = globalThis.crypto?.randomUUID?.() ||
    `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}-${Math.random().toString(36).slice(2)}`;
  localStorage.setItem(RESUME_TOKEN_KEY, token);
  return token;
}

function loadResumeSession() {
  try {
    return JSON.parse(sessionStorage.getItem(RESUME_SESSION_KEY) || "null");
  } catch {
    return null;
  }
}

function saveResumeSession(meta) {
  if (!meta.roomCode || !meta.player) return;
  sessionStorage.setItem(
    RESUME_SESSION_KEY,
    JSON.stringify({ roomCode: meta.roomCode, player: meta.player })
  );
}

function clearResumeSession(meta) {
  meta.roomCode = "";
  meta.youId = "";
  meta.player = null;
  meta.reconnecting = false;
  sessionStorage.removeItem(RESUME_SESSION_KEY);
}

function haptic(pattern = 18) {
  if (navigator.vibrate) navigator.vibrate(pattern);
}

function ensureLayer() {
  let layer = document.getElementById("party-upgrade-layer");
  if (layer) return layer;

  layer = document.createElement("div");
  layer.id = "party-upgrade-layer";
  layer.setAttribute("aria-live", "polite");
  layer.innerHTML = `
    <div class="party-snow" aria-hidden="true"></div>
    <div class="party-connection" hidden></div>
    <div class="party-center" hidden></div>
    <div class="party-score-pop" hidden></div>
    <div class="party-collection-pill" hidden></div>
    <div class="party-confetti" aria-hidden="true"></div>
  `;
  document.body.appendChild(layer);

  if (!prefersReducedMotion()) {
    const snow = layer.querySelector(".party-snow");
    for (let i = 0; i < 18; i += 1) {
      const flake = document.createElement("i");
      flake.textContent = "❄";
      flake.style.setProperty("--x", `${Math.random() * 100}vw`);
      flake.style.setProperty("--delay", `${Math.random() * -10}s`);
      flake.style.setProperty("--duration", `${8 + Math.random() * 8}s`);
      flake.style.setProperty("--size", `${9 + Math.random() * 12}px`);
      snow.appendChild(flake);
    }
  }
  return layer;
}

function showConnection(message, kind = "info") {
  const node = ensureLayer().querySelector(".party-connection");
  node.textContent = message;
  node.dataset.kind = kind;
  node.hidden = false;
}

function hideConnection() {
  const node = ensureLayer().querySelector(".party-connection");
  node.hidden = true;
}

function showCenter(title, subtitle = "", duration = 1050, mode = "default") {
  const node = ensureLayer().querySelector(".party-center");
  window.clearTimeout(centerTimer);
  node.dataset.mode = mode;
  node.innerHTML = `<strong>${title}</strong>${subtitle ? `<span>${subtitle}</span>` : ""}`;
  node.hidden = false;
  node.classList.remove("party-center-pop");
  void node.offsetWidth;
  node.classList.add("party-center-pop");
  centerTimer = window.setTimeout(() => {
    node.hidden = true;
    node.classList.remove("party-center-pop");
  }, duration);
}

function showScore(delta) {
  if (!delta) return;
  const node = ensureLayer().querySelector(".party-score-pop");
  window.clearTimeout(scoreTimer);
  node.textContent = `+${delta}`;
  node.hidden = false;
  node.classList.remove("party-score-animate");
  void node.offsetWidth;
  node.classList.add("party-score-animate");
  scoreTimer = window.setTimeout(() => {
    node.hidden = true;
  }, 700);
}

function shakeScreen() {
  if (prefersReducedMotion()) return;
  document.documentElement.classList.remove("party-shake");
  void document.documentElement.offsetWidth;
  document.documentElement.classList.add("party-shake");
  window.setTimeout(() => document.documentElement.classList.remove("party-shake"), 280);
}

function burstConfetti(count = 36) {
  if (prefersReducedMotion()) return;
  const host = ensureLayer().querySelector(".party-confetti");
  host.innerHTML = "";
  for (let i = 0; i < count; i += 1) {
    const piece = document.createElement("i");
    piece.textContent = ["✦", "★", "❄", "●"][i % 4];
    piece.style.setProperty("--x", `${8 + Math.random() * 84}vw`);
    piece.style.setProperty("--drift", `${-80 + Math.random() * 160}px`);
    piece.style.setProperty("--delay", `${Math.random() * 0.35}s`);
    piece.style.setProperty("--fall", `${1.8 + Math.random() * 1.4}s`);
    host.appendChild(piece);
  }
  window.setTimeout(() => { host.innerHTML = ""; }, 3600);
}

function spawnCandySpark() {
  if (prefersReducedMotion()) return;
  const host = ensureLayer();
  const spark = document.createElement("div");
  spark.className = "party-candy-spark";
  spark.textContent = "🍬";
  spark.style.left = `${72 + Math.random() * 17}vw`;
  spark.style.top = `${70 + Math.random() * 18}vh`;
  host.appendChild(spark);
  window.setTimeout(() => spark.remove(), 900);
}

function applyOwnedCosmetics(owned = []) {
  const clean = Array.isArray(owned) ? owned : [];
  localStorage.setItem(OWNED_KEY, JSON.stringify(clean));
  const root = document.documentElement;
  ["skin_ice", "boost_speed", "trail_candy", "hat_elf", "victory_sparkle"].forEach((id) => {
    root.classList.toggle(`owns-${id.replaceAll("_", "-")}`, clean.includes(id));
  });
  const pill = ensureLayer().querySelector(".party-collection-pill");
  if (clean.length) {
    pill.textContent = `Holiday collection · ${clean.length}`;
    pill.hidden = false;
  } else {
    pill.hidden = true;
  }
}

function loadOwnedCosmetics() {
  try {
    applyOwnedCosmetics(JSON.parse(localStorage.getItem(OWNED_KEY) || "[]"));
  } catch {
    applyOwnedCosmetics([]);
  }
}

function standingsSubtitle(room) {
  const players = [...(room?.players || [])].sort((a, b) => (b.score || 0) - (a.score || 0));
  if (!players.length) return "";
  return players.slice(0, 3).map((player, index) => `#${index + 1} ${player.name} ${player.score}pts`).join(" · ");
}

function getMeta(socket) {
  let meta = socketMeta.get(socket);
  if (meta) return meta;

  const restored = loadResumeSession();
  meta = {
    resumeToken: makeResumeToken(),
    roomCode: restored?.roomCode || "",
    player: restored?.player || null,
    youId: "",
    reconnecting: false,
    lastInputAt: 0,
    lastInput: null,
    lastPlayerState: null,
    observersInstalled: false
  };
  socketMeta.set(socket, meta);
  installObservers(socket, meta);
  return meta;
}

function installObservers(socket, meta) {
  if (meta.observersInstalled) return;
  meta.observersInstalled = true;

  socket.on("connect", () => {
    if (!meta.roomCode || !meta.player) {
      hideConnection();
      return;
    }
    meta.reconnecting = true;
    showConnection("Rejoining your Christmas match…", "reconnect");
    window.setTimeout(() => {
      originalEmit.call(socket, "join_room", {
        ...meta.player,
        room: meta.roomCode,
        token: localStorage.getItem("authToken") || "",
        resumeToken: meta.resumeToken
      });
    }, 120);
  });

  socket.on("disconnect", (reason) => {
    if (!meta.roomCode || reason === "io client disconnect") return;
    meta.reconnecting = true;
    showConnection("Connection lost — holding your spot for 15 seconds…", "warning");
  });

  socket.on("connect_error", () => {
    if (meta.roomCode) showConnection("Trying to reconnect…", "warning");
  });

  socket.on("room_joined", (payload) => {
    meta.roomCode = payload?.room?.code || meta.roomCode;
    meta.youId = payload?.youId || meta.youId;
    meta.reconnecting = false;
    saveResumeSession(meta);
    hideConnection();
    if (meta.roomCode) {
      showCenter("CONNECTED", `Room ${meta.roomCode}`, 650, "success");
    }
  });

  socket.on("server_error", (payload) => {
    if (!meta.reconnecting) return;
    const message = payload?.message || "Unable to resume match";
    if (/not found|already started/i.test(message)) {
      clearResumeSession(meta);
      showConnection("Previous match expired. Create or join a room to keep playing.", "error");
      window.setTimeout(hideConnection, 4200);
    }
  });

  socket.on("party_countdown", (payload) => {
    const value = payload?.value || "";
    const roundName = ROUND_NAMES[payload?.roundType] || "Next Round";
    if (value === "GO!") {
      haptic([30, 35, 55]);
      showCenter("GO!", roundName, 850, "go");
    } else {
      haptic(24);
      showCenter(value, `${roundName} · Round ${payload?.round || ""}`, 690, "countdown");
    }
  });

  socket.on("round_started", (payload) => {
    const roundType = payload?.room?.roundType;
    document.documentElement.dataset.partyRound = roundType || "lobby";
  });

  socket.on("round_ended", (payload) => {
    haptic([20, 50, 20]);
    showCenter("ROUND COMPLETE", standingsSubtitle(payload?.room), 1800, "result");
    burstConfetti(22);
  });

  socket.on("game_over", (payload) => {
    haptic([30, 45, 30, 45, 70]);
    showCenter("FINAL RESULTS", standingsSubtitle(payload?.room), 2400, "final");
    let owned = [];
    try { owned = JSON.parse(localStorage.getItem(OWNED_KEY) || "[]"); } catch { owned = []; }
    burstConfetti(owned.includes("victory_sparkle") ? 76 : 48);
    clearResumeSession(meta);
  });

  socket.on("announcement", (payload) => {
    if (!payload?.message) return;
    showCenter(payload.message, "", Math.min(1800, (payload.duration || 2) * 1000), "announcement");
  });

  socket.on("store_data", (payload) => {
    applyOwnedCosmetics(payload?.owned || []);
  });

  socket.on("world_state", (payload) => {
    if (!meta.youId) return;
    const current = payload?.world?.players?.find((player) => player.id === meta.youId);
    if (!current) return;
    const previous = meta.lastPlayerState;
    if (previous) {
      const scoreDelta = (current.score || 0) - (previous.score || 0);
      if (scoreDelta > 0) showScore(scoreDelta);
      if (previous.alive && !current.alive) {
        haptic([55, 35, 80]);
        shakeScreen();
        showCenter("ELIMINATED", "You’ll be back next round", 1100, "danger");
      } else if ((current.ringsLeft ?? 3) < (previous.ringsLeft ?? 3)) {
        haptic(45);
        shakeScreen();
      }
    }
    meta.lastPlayerState = {
      score: current.score || 0,
      alive: Boolean(current.alive),
      ringsLeft: current.ringsLeft ?? 3
    };
  });
}

function upgradedEmit(event, ...args) {
  const meta = getMeta(this);

  if (event === "create_room" || event === "join_room") {
    const payload = { ...(args[0] || {}) };
    meta.player = {
      name: payload.name || "Player",
      color: payload.color || "red"
    };
    if (event === "join_room") meta.roomCode = String(payload.room || "").toUpperCase();
    payload.resumeToken = meta.resumeToken;
    saveResumeSession(meta);
    return originalEmit.call(this, event, payload, ...args.slice(1));
  }

  if (event === "leave_room") {
    clearResumeSession(meta);
    return originalEmit.call(this, event, ...args);
  }

  if (event === "start_round") {
    return originalEmit.call(this, "party_start_round", ...(args.length ? args : [null]));
  }

  if (event === "player_input") {
    const payload = args[0] || {};
    const now = performance.now();
    const last = meta.lastInput;
    const changed = !last || last.x !== payload.x || last.y !== payload.y;
    const minGap = changed ? 25 : 250;
    if (now - meta.lastInputAt < minGap) return this;
    meta.lastInputAt = now;
    meta.lastInput = { x: payload.x, y: payload.y };
  }

  if (event === "action") {
    haptic(16);
    document.documentElement.classList.add("party-action-pulse");
    window.setTimeout(() => document.documentElement.classList.remove("party-action-pulse"), 180);
    let owned = [];
    try { owned = JSON.parse(localStorage.getItem(OWNED_KEY) || "[]"); } catch { owned = []; }
    if (owned.includes("trail_candy")) spawnCandySpark();
  }

  return originalEmit.call(this, event, ...args);
}

function upgradedConnect(...args) {
  getMeta(this);
  return originalConnect.apply(this, args);
}

export function installPartyUpgrade() {
  if (globalThis[INSTALL_FLAG]) return;
  globalThis[INSTALL_FLAG] = true;
  Socket.prototype.emit = upgradedEmit;
  Socket.prototype.connect = upgradedConnect;
  ensureLayer();
  loadOwnedCosmetics();

  document.addEventListener("pointerdown", (event) => {
    if (event.target.closest?.(".action-button")) haptic(12);
  }, { passive: true });
}
