import React, { useEffect, useRef } from "react";

const PLAYER_COLORS = [
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
  "white"
];

const MONSTER_SPRITES = [
  "monster1",
  "monster2",
  "monster3",
  "monster4",
  "monster6",
  "monster7",
  "monster8",
  "monster10"
];

const HERO_SPRITES = {
  holly: "/assets/custom-heroes/player1-clean.png"
};

const ASSETS = {
  gift: "/assets/pixel/gift.svg",
  candy: "/assets/pixel/candy-cane.svg",
  tree: "/assets/pixel/tree.svg",
  snowball: "/assets/pixel/snowball.svg",
  snowflake: "/assets/pixel/snowflake.svg",
  star: "/assets/pixel/star.svg"
};

const COLOR_HEX = {
  red: "#e53935",
  orange: "#fb8c00",
  yellow: "#fdd835",
  lime: "#c0ca33",
  green: "#43a047",
  teal: "#00897b",
  cyan: "#00acc1",
  blue: "#1e88e5",
  indigo: "#3949ab",
  purple: "#8e24aa",
  magenta: "#d81b60",
  pink: "#f06292",
  brown: "#6d4c41",
  gray: "#546e7a",
  black: "#263238",
  white: "#ffffff"
};

const MONSTER_STYLE = {
  small: { size: 20, color: "#ff6b6b" },
  medium: { size: 26, color: "#ff9f1c" },
  big: { size: 32, color: "#8e24aa" },
  yeti: { size: 38, color: "#bfe7ff" }
};

const TREE_DRAW = {
  small: 32,
  medium: 48,
  large: 64
};

const TEAM_RING = {
  0: "#1e88e5",
  1: "#e53935"
};

const LIGHT_AURA_RADIUS = 130;

const loadImage = (src) => {
  const img = new Image();
  img.src = src;
  return img;
};

const roomToWorld = (room) => {
  if (!room) return null;
  return {
    width: room.width || 960,
    height: room.height || 540,
    players: room.players || [],
    projectiles: [],
    hazards: [],
    gifts: [],
    walls: [],
    trails: [],
    light: {},
    hill: {}
  };
};

const getSeed = (value) => {
  if (!value) return 0;
  let hash = 0;
  for (let i = 0; i < value.length; i += 1) {
    hash = (hash * 31 + value.charCodeAt(i)) % 997;
  }
  return hash;
};

const getDirection = (fx, fy) => {
  if (Math.abs(fy) > Math.abs(fx)) {
    return fy < -0.2 ? "up" : "down";
  }
  return fx < -0.2 ? "left" : "right";
};

const drawFacing = (ctx, left, top, pixel, color, direction) => {
  ctx.fillStyle = color;
  if (direction === "up") {
    ctx.fillRect(left + 6 * pixel, top + 2 * pixel, 4 * pixel, pixel);
    ctx.fillRect(left + 5 * pixel, top + 3 * pixel, 6 * pixel, pixel);
    return;
  }
  if (direction === "left") {
    ctx.fillRect(left + 9 * pixel, top + 2 * pixel, pixel, pixel);
    ctx.fillStyle = "#2a1a12";
    ctx.fillRect(left + 6 * pixel, top + 3 * pixel, pixel, pixel);
    return;
  }
  if (direction === "right") {
    ctx.fillRect(left + 6 * pixel, top + 2 * pixel, pixel, pixel);
    ctx.fillStyle = "#2a1a12";
    ctx.fillRect(left + 9 * pixel, top + 3 * pixel, pixel, pixel);
  }
};

const drawFeet = (ctx, left, top, pixel, color, step, direction) => {
  ctx.fillStyle = color;
  const y = top + 13 * pixel;
  if (direction === "left" || direction === "right") {
    const x1 = left + (step ? 5 : 9) * pixel;
    const x2 = left + (step ? 9 : 5) * pixel;
    ctx.fillRect(x1, y, 2 * pixel, pixel);
    ctx.fillRect(x2, y + pixel, 2 * pixel, pixel);
    return;
  }
  const x1 = left + 5 * pixel;
  const x2 = left + 9 * pixel;
  ctx.fillRect(x1, y + (step ? 0 : pixel), 2 * pixel, pixel);
  ctx.fillRect(x2, y + (step ? pixel : 0), 2 * pixel, pixel);
};

export default function GameCanvas({ world, room, youId, roundType }) {
  const canvasRef = useRef(null);
  const assetsRef = useRef(null);
  const lastRenderRef = useRef(0);

  useEffect(() => {
    if (assetsRef.current) return;
    const images = {
      gift: loadImage(ASSETS.gift),
      candy: loadImage(ASSETS.candy),
      tree: loadImage(ASSETS.tree),
      snowball: loadImage(ASSETS.snowball),
      snowflake: loadImage(ASSETS.snowflake),
      star: loadImage(ASSETS.star),
      players: {},
      monsters: {},
      heroes: {}
    };
    PLAYER_COLORS.forEach((color) => {
      images.players[color] = loadImage(`/assets/pixel/players/player-${color}.svg`);
    });
    MONSTER_SPRITES.forEach((name) => {
      images.monsters[name] = loadImage(`/assets/monsters/${name}.png`);
    });
    Object.entries(HERO_SPRITES).forEach(([key, src]) => {
      images.heroes[key] = loadImage(src);
    });
    assetsRef.current = images;
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    const snapshot = world && world.players ? world : roomToWorld(room);
    if (!canvas || !snapshot) return;
    const nowMs = performance.now();
    const isMobile = navigator.maxTouchPoints > 0 || window.innerWidth < 900;
    const minFrame = isMobile ? 33 : 0;
    if (nowMs - lastRenderRef.current < minFrame) return;
    lastRenderRef.current = nowMs;
    const ctx = canvas.getContext("2d");
    ctx.imageSmoothingEnabled = false;
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
    }

    const worldWidth = snapshot.width || 960;
    const worldHeight = snapshot.height || 540;
    const useFixedView = worldWidth > 2000 || worldHeight > 1200;
    const targetViewWidth = useFixedView ? 1200 : worldWidth;
    const targetViewHeight = useFixedView ? 675 : worldHeight;
    const baseScale = Math.min(canvas.width / targetViewWidth, canvas.height / targetViewHeight);
    const zoom = roundType && roundType !== "lobby" ? (useFixedView ? 1.0 : 1.15) : 1.0;
    const scale = baseScale * zoom;
    const now = performance.now() / 1000;

    const viewWidth = canvas.width / scale;
    const viewHeight = canvas.height / scale;
    const you = snapshot.players?.find((player) => player.id === youId);
    const camX = you
      ? Math.max(0, Math.min(worldWidth - viewWidth, (you.x ?? worldWidth / 2) - viewWidth / 2))
      : 0;
    const camY = you
      ? Math.max(0, Math.min(worldHeight - viewHeight, (you.y ?? worldHeight / 2) - viewHeight / 2))
      : 0;

    const fitsWidth = worldWidth * scale <= canvas.width;
    const fitsHeight = worldHeight * scale <= canvas.height;
    const offsetX = fitsWidth ? (canvas.width - worldWidth * scale) / 2 : -camX * scale;
    const offsetY = fitsHeight ? (canvas.height - worldHeight * scale) / 2 : -camY * scale;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    ctx.save();
    ctx.translate(offsetX, offsetY);
    ctx.scale(scale, scale);

    ctx.fillStyle = "#f4fbff";
    ctx.fillRect(0, 0, worldWidth, worldHeight);

    const outerBorder = 6;
    const innerBorder = 3;
    ctx.fillStyle = "#1a1a1a";
    ctx.fillRect(0, 0, worldWidth, outerBorder);
    ctx.fillRect(0, worldHeight - outerBorder, worldWidth, outerBorder);
    ctx.fillRect(0, 0, outerBorder, worldHeight);
    ctx.fillRect(worldWidth - outerBorder, 0, outerBorder, worldHeight);
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(
      outerBorder,
      outerBorder,
      worldWidth - outerBorder * 2,
      innerBorder
    );
    ctx.fillRect(
      outerBorder,
      worldHeight - outerBorder - innerBorder,
      worldWidth - outerBorder * 2,
      innerBorder
    );
    ctx.fillRect(
      outerBorder,
      outerBorder,
      innerBorder,
      worldHeight - outerBorder * 2
    );
    ctx.fillRect(
      worldWidth - outerBorder - innerBorder,
      outerBorder,
      innerBorder,
      worldHeight - outerBorder * 2
    );

    if (roundType === "survival" || roundType === "ice") {
      ctx.fillStyle = "rgba(255, 255, 255, 0.7)";
      const flakeCount = roundType === "ice" ? 70 : 55;
      for (let i = 0; i < flakeCount; i += 1) {
        const seed = (i * 97) % 997;
        const speed = 18 + (seed % 9);
        const drift = 12 + (seed % 5);
        const x = (seed * 19 + now * drift * 60) % worldWidth;
        const y = (seed * 37 + now * speed * 60) % worldHeight;
        const size = 2 + (seed % 3);
        ctx.beginPath();
        ctx.arc(x, y, size, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    if (snapshot.walls && snapshot.walls.length) {
      ctx.fillStyle = "#a67c52";
      snapshot.walls.forEach((wall) => {
        ctx.fillRect(wall.x, wall.y, wall.w, wall.h);
      });
    }

    if (snapshot.trails && snapshot.trails.length) {
      const minX = fitsWidth ? 0 : camX - 32;
      const maxX = fitsWidth ? worldWidth : camX + viewWidth + 32;
      const minY = fitsHeight ? 0 : camY - 32;
      const maxY = fitsHeight ? worldHeight : camY + viewHeight + 32;
      snapshot.trails.forEach((trail) => {
        const size = trail.size || 16;
        if (
          trail.x + size < minX ||
          trail.x > maxX ||
          trail.y + size < minY ||
          trail.y > maxY
        ) {
          return;
        }
        const trailColor = COLOR_HEX[trail.color] || "#f2c14e";
        ctx.fillStyle = trailColor;
        ctx.fillRect(trail.x, trail.y, size, size);
      });
    }

    const images = assetsRef.current;
    const drawImage = (img, x, y, size) => {
      if (!img || !img.complete) return false;
      ctx.drawImage(img, x - size / 2, y - size / 2, size, size);
      return true;
    };

    if (snapshot.gifts) {
      snapshot.gifts.forEach((gift) => {
        const bob = Math.sin(now * 3 + gift.id) * 2;
        const giftType =
          gift.type || (roundType === "survival" || roundType === "maze" ? "candy" : "present");
        const img =
          giftType === "candy"
            ? images?.candy
            : giftType === "flag"
            ? images?.star
            : images?.gift;
        if (!drawImage(img, gift.x, gift.y + bob, 26)) {
          ctx.fillStyle = "#f2c14e";
          ctx.fillRect(gift.x - 10, gift.y - 10 + bob, 20, 20);
        }
      });
    }

    if (snapshot.hazards) {
      snapshot.hazards.forEach((hazard) => {
        if (hazard.type === "big_snowball") {
          const size = (hazard.radius || 20) * 2;
          if (images?.snowball?.complete) {
            const spin = now * 3 + (hazard.id || 0) * 0.35;
            ctx.save();
            ctx.translate(hazard.x, hazard.y);
            ctx.rotate(spin);
            ctx.drawImage(images.snowball, -size / 2, -size / 2, size, size);
            ctx.restore();
          } else {
            ctx.fillStyle = "#ffffff";
            ctx.beginPath();
            ctx.arc(hazard.x, hazard.y, hazard.radius || 20, 0, Math.PI * 2);
            ctx.fill();
          }
          ctx.strokeStyle = "#1a1a1a";
          ctx.lineWidth = 3;
          ctx.beginPath();
          ctx.arc(hazard.x, hazard.y, (hazard.radius || 20) - 1, 0, Math.PI * 2);
          ctx.stroke();
          ctx.fillStyle = "#1a1a1a";
          ctx.beginPath();
          ctx.arc(hazard.x - 6, hazard.y - 4, 2, 0, Math.PI * 2);
          ctx.arc(hazard.x + 5, hazard.y + 3, 2, 0, Math.PI * 2);
          ctx.fill();
          return;
        }
        if (!drawImage(images?.snowflake, hazard.x, hazard.y, 28)) {
          ctx.fillStyle = "#7ec8ff";
          ctx.beginPath();
          ctx.arc(hazard.x, hazard.y, 12, 0, Math.PI * 2);
          ctx.fill();
        }
      });
    }

    if (snapshot.projectiles) {
      snapshot.projectiles.forEach((projectile) => {
        const stroke = COLOR_HEX[projectile.color] || "#2a1a12";
        if (!drawImage(images?.snowball, projectile.x, projectile.y, 18)) {
          ctx.fillStyle = "#ffffff";
          ctx.beginPath();
          ctx.arc(projectile.x, projectile.y, 6, 0, Math.PI * 2);
          ctx.fill();
        }
        ctx.strokeStyle = stroke;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(projectile.x, projectile.y, 8, 0, Math.PI * 2);
        ctx.stroke();
      });
    }

    if (snapshot.monsterProjectiles) {
      snapshot.monsterProjectiles.forEach((projectile) => {
        ctx.fillStyle = "#ff7043";
        ctx.beginPath();
        ctx.arc(projectile.x, projectile.y, 7, 0, Math.PI * 2);
        ctx.fill();
      });
    }

    if (snapshot.monsters) {
      snapshot.monsters.forEach((monster) => {
        const style = MONSTER_STYLE[monster.type] || MONSTER_STYLE.small;
        const spriteName = monster.sprite || monster.type;
        const img = images?.monsters?.[spriteName];
        const isBoss = monster.type === "boss";
        const size = isBoss ? 96 : 60;
        const bob = Math.sin(now * 2.2 + monster.id) * 2.5;
        const wobble = Math.sin(now * 3.1 + monster.id) * 0.04;
        const facing = Number.isFinite(monster.vx)
          ? monster.vx
          : Number.isFinite(monster.dirX)
          ? monster.dirX
          : 1;
        const flip = facing < -0.05 ? -1 : 1;
        if (img && img.complete) {
          ctx.save();
          ctx.translate(monster.x, monster.y + bob);
          ctx.scale(flip * (1 + wobble), 1 - wobble);
          ctx.drawImage(img, -size / 2, -size / 2, size, size);
          ctx.restore();
        } else {
          ctx.fillStyle = style.color;
          ctx.beginPath();
          ctx.arc(monster.x, monster.y + bob, style.size / 2, 0, Math.PI * 2);
          ctx.fill();
          ctx.fillStyle = "#2a1a12";
          ctx.fillRect(monster.x - 4, monster.y - 6 + bob, 2, 2);
          ctx.fillRect(monster.x + 2, monster.y - 6 + bob, 2, 2);
        }
        if (isBoss) {
          ctx.strokeStyle = "rgba(255, 87, 51, 0.65)";
          ctx.lineWidth = 3;
          ctx.beginPath();
          ctx.arc(monster.x, monster.y + bob, size * 0.48, 0, Math.PI * 2);
          ctx.stroke();
        }
      });
    }

    if (snapshot.decorations) {
      snapshot.decorations.forEach((deco) => {
        if (deco.type !== "tree") return;
        const sway = Math.sin(now * 1.4 + deco.id) * 2;
        const size = TREE_DRAW[deco.size] || TREE_DRAW.medium;
        if (!drawImage(images?.tree, deco.x, deco.y + sway, size)) {
          ctx.fillStyle = "#2e7d32";
          const half = size * 0.25;
          ctx.fillRect(deco.x - half, deco.y - half - 8 + sway, half * 2, half * 2);
        }
      });
    }

    if (snapshot.hill && snapshot.hill.radius) {
      const hillX = snapshot.hill.x ?? worldWidth / 2;
      const hillY = snapshot.hill.y ?? worldHeight * 0.18;
      const hillRadius = snapshot.hill.radius ?? 160;
      ctx.save();
      ctx.fillStyle = "rgba(242, 193, 78, 0.18)";
      ctx.strokeStyle = "rgba(214, 141, 0, 0.7)";
      ctx.lineWidth = 4;
      ctx.beginPath();
      ctx.arc(hillX, hillY, hillRadius, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
      ctx.restore();
    }

    if (snapshot.light && snapshot.light.x) {
      if (!drawImage(images?.star, snapshot.light.x, snapshot.light.y, 28)) {
        ctx.fillStyle = "#f2c14e";
        ctx.beginPath();
        ctx.arc(snapshot.light.x, snapshot.light.y, 10, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    if (roundType === "light" && snapshot.players) {
      const holder = snapshot.players.find((player) => player.hasLight);
      if (holder && Number.isFinite(holder.x) && Number.isFinite(holder.y)) {
        const auraColor = COLOR_HEX[holder.color] || "#f2c14e";
        ctx.save();
        ctx.strokeStyle = `${auraColor}88`;
        ctx.lineWidth = 4;
        ctx.beginPath();
        ctx.arc(holder.x, holder.y, LIGHT_AURA_RADIUS, 0, Math.PI * 2);
        ctx.stroke();
        ctx.restore();
      }
    }

    if (snapshot.players) {
      snapshot.players.forEach((player, index) => {
        const isHolly = (player.name || "").trim().toLowerCase() === "holly";
        const heroSprite = isHolly ? images?.heroes?.holly : null;
        const sprite = images?.players?.[player.color];
        const size = 44;
        const pixel = size / 16;
        const px = Number.isFinite(player.x)
          ? player.x
          : worldWidth / 2 + (index % 4) * 36 - 54;
        const py = Number.isFinite(player.y)
          ? player.y
          : worldHeight / 2 + Math.floor(index / 4) * 36 - 36;
        const left = px - size / 2;
        const top = py - size / 2;
        const moving = player.moving;
        const direction = getDirection(player.fx ?? 1, player.fy ?? 0);
        const step = moving ? Math.floor((now * 8 + getSeed(player.id)) % 2) : 0;
        const bob = moving ? Math.round(Math.sin(now * 10 + getSeed(player.id)) * 1) : 0;
        const heroBob = moving ? Math.sin(now * 10 + getSeed(player.id)) * 2 : 0;
        const heroWobble = moving ? Math.sin(now * 6 + getSeed(player.id)) * 0.05 : 0;
        const heroFlip = (player.fx ?? 1) < -0.1 ? -1 : 1;

        ctx.globalAlpha = player.alive ? 1 : 0.35;
        if (heroSprite && heroSprite.complete) {
          const heroSize = 64;
          ctx.save();
          ctx.translate(px, py + heroBob);
          ctx.scale(heroFlip * (1 + heroWobble), 1 - heroWobble);
          ctx.drawImage(heroSprite, -heroSize / 2, -heroSize / 2, heroSize, heroSize);
          ctx.restore();
        } else {
          if (!drawImage(sprite, px, py + bob, size)) {
            ctx.fillStyle = "#2a1a12";
            ctx.beginPath();
            ctx.arc(px, py + bob, 14, 0, Math.PI * 2);
            ctx.fill();
          }
        }
        if (roundType === "snowball" && player.alive) {
          const rings = Math.max(0, Math.min(3, player.ringsLeft ?? 0));
          if (rings) {
            ctx.strokeStyle = TEAM_RING[player.team] || "#1e88e5";
            ctx.lineWidth = 2;
            for (let i = 0; i < rings; i += 1) {
              ctx.beginPath();
              ctx.arc(px, py + bob, 18 + i * 4, 0, Math.PI * 2);
              ctx.stroke();
            }
          }
        }
        if (player.alive && !(heroSprite && heroSprite.complete)) {
          drawFacing(ctx, left, top + bob, pixel, COLOR_HEX[player.color] || "#ffffff", direction);
          drawFeet(ctx, left, top + bob, pixel, "#2a1a12", step, direction);
        }
        ctx.globalAlpha = 1;
        if (player.id === youId) {
          ctx.strokeStyle = "rgba(46, 125, 50, 0.8)";
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.arc(px, py + bob, 18, 0, Math.PI * 2);
          ctx.stroke();
        }
      });
    }

    ctx.restore();

    if (roundType && ["snowball", "light", "trails", "hunt", "hill"].includes(roundType)) {
      const mapPadding = 12;
      let mapWidth = 105;
      let mapHeight = (mapWidth * worldHeight) / worldWidth;
      if (mapHeight > 90) {
        mapHeight = 72;
        mapWidth = (mapHeight * worldWidth) / worldHeight;
      }
      const compactHud = canvas.height < 520;
      if (compactHud) {
        mapWidth = 90;
        mapHeight = (mapWidth * worldHeight) / worldWidth;
        if (mapHeight > 78) {
          mapHeight = 64;
          mapWidth = (mapHeight * worldWidth) / worldHeight;
        }
      }
      const mapX = compactHud ? mapPadding : canvas.width - mapWidth - mapPadding;
      const mapY = compactHud ? mapPadding + 86 : (canvas.height < 450 ? 180 : 240) + mapPadding;

      ctx.save();
      ctx.fillStyle = "rgba(255, 255, 255, 0.9)";
      ctx.strokeStyle = "rgba(42, 26, 18, 0.2)";
      ctx.lineWidth = 2;
      ctx.fillRect(mapX, mapY, mapWidth, mapHeight);
      ctx.strokeRect(mapX, mapY, mapWidth, mapHeight);

      const toMapX = (x) => mapX + (x / worldWidth) * mapWidth;
      const toMapY = (y) => mapY + (y / worldHeight) * mapHeight;

      if (snapshot.monsters) {
        ctx.fillStyle = "rgba(255, 107, 107, 0.8)";
        snapshot.monsters.forEach((monster) => {
          ctx.beginPath();
          ctx.arc(toMapX(monster.x), toMapY(monster.y), 2.5, 0, Math.PI * 2);
          ctx.fill();
        });
      }

      if (snapshot.light && snapshot.light.x) {
        ctx.fillStyle = "#f2c14e";
        ctx.beginPath();
        ctx.arc(toMapX(snapshot.light.x), toMapY(snapshot.light.y), 3, 0, Math.PI * 2);
        ctx.fill();
      }

      if (snapshot.hill && snapshot.hill.radius) {
        ctx.strokeStyle = "rgba(214, 141, 0, 0.7)";
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.arc(
          toMapX(snapshot.hill.x ?? worldWidth / 2),
          toMapY(snapshot.hill.y ?? worldHeight * 0.18),
          (snapshot.hill.radius ?? 160) * (mapWidth / worldWidth),
          0,
          Math.PI * 2
        );
        ctx.stroke();

      }

      if (snapshot.players) {
        snapshot.players.forEach((player) => {
          ctx.fillStyle = COLOR_HEX[player.color] || "#2a1a12";
          ctx.beginPath();
          ctx.arc(toMapX(player.x), toMapY(player.y), 3, 0, Math.PI * 2);
          ctx.fill();
          if (player.id === youId) {
            ctx.strokeStyle = "rgba(46, 125, 50, 0.9)";
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.arc(toMapX(player.x), toMapY(player.y), 4.5, 0, Math.PI * 2);
            ctx.stroke();
          }
        });
      }
      ctx.restore();
    }
  }, [world, room, youId, roundType]);

  return <canvas ref={canvasRef} className="game-canvas" />;
}
