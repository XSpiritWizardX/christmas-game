// Static scenery is painted once per arena so moving hazards stay inexpensive on phones.
const floors = new Map();

export function drawFloor(ctx, mode, width, height) {
  if (mode !== "raceway" && mode !== "workshop") return;
  let floor = floors.get(mode);
  if (!floor || floor.width !== width || floor.height !== height) {
    floor = document.createElement("canvas");
    floor.width = width;
    floor.height = height;
    const g = floor.getContext("2d");
    if (mode === "raceway") {
      const snow = g.createLinearGradient(0, 0, width, height);
      snow.addColorStop(0, "#f1faf6");
      snow.addColorStop(1, "#99c9d0");
      g.fillStyle = snow;
      g.fillRect(0, 0, width, height);
      for (let i = 0; i < 150; i++) {
        const x = (i * 139) % width, y = (i * 83) % height;
        g.fillStyle = i % 3 ? "#ffffff70" : "#719ca33b";
        g.fillRect(x, y, 5 + i % 14, 2);
      }
      for (const offset of [-7, 7]) {
        g.beginPath();
        g.moveTo(45 + offset, 80);
        for (let i = 0; i < 4; i++) {
          const x = 180 + 180 * i + offset, y = i % 2 ? 445 : 95;
          g.bezierCurveTo(x - 55, y, x - 45, y, x + 52, y);
        }
        g.quadraticCurveTo(875, 435, 895, 270);
        g.strokeStyle = "#75a1aa66";
        g.lineWidth = 4;
        g.stroke();
      }
    } else {
      for (let y = 0; y < height; y += 28) {
        for (let x = -(y % 56 ? 58 : 0); x < width; x += 116) {
          g.fillStyle = ((x + y) % 3) ? "#edc592" : "#e7bc87";
          g.fillRect(x, y, 116, 28);
          g.fillStyle = "#b980523d";
          g.fillRect(x, y, 115, 2);
          g.fillRect(x, y, 2, 28);
          g.fillRect(x + 19, y + 17, 42, 1);
        }
      }
      for (const x of [340, 590]) {
        g.fillStyle = "#765643";
        g.fillRect(x - 12, 64, 24, 412);
        g.fillStyle = "#bd9c79";
        g.fillRect(x - 8, 67, 16, 406);
        g.fillStyle = "#826957";
        for (let y = 72; y < 470; y += 16) g.fillRect(x - 7, y, 14, 4);
      }
    }
    floors.set(mode, floor);
  }
  ctx.drawImage(floor, 0, 0);
}

export function drawObstacle(ctx, mode, obstacle, phase) {
  const {x, y, r} = obstacle;
  ctx.save();
  ctx.translate(x, y);
  ctx.fillStyle = "#183a443b";
  ctx.beginPath();
  ctx.ellipse(3, r * .55, r, r * .45, 0, 0, Math.PI * 2);
  ctx.fill();
  if (mode === "raceway") {
    ctx.beginPath();
    ctx.moveTo(-r, 7);
    ctx.quadraticCurveTo(-r + 2, -10, -10, -13);
    ctx.quadraticCurveTo(0, -31, 14, -13);
    ctx.quadraticCurveTo(25, -12, r, 8);
    ctx.quadraticCurveTo(13, 22, -r, 7);
    ctx.fillStyle = "#fbffff";
    ctx.fill();
    ctx.strokeStyle = "#6593a5";
    ctx.lineWidth = 3;
    ctx.stroke();
    ctx.fillStyle = "#a5d3df";
    ctx.beginPath();
    ctx.moveTo(-18, 5);ctx.quadraticCurveTo(3, 12, 18, -2);
    ctx.quadraticCurveTo(11, 18, -18, 5);ctx.fill();
  } else {
    ctx.rotate(phase * 2);
    for (let i = 0; i < 4; i++) {
      ctx.rotate(Math.PI / 2);
      ctx.fillStyle = "#623b38";
      ctx.fillRect(-7, -r, 14, r);
      ctx.fillStyle = "#b6453e";
      ctx.fillRect(-5, -r + 2, 10, r - 2);
      ctx.fillStyle = "#fff0bb";
      ctx.fillRect(-5, -r + 8, 10, 6);
    }
    ctx.beginPath();ctx.arc(0, 0, 11, 0, Math.PI * 2);
    ctx.fillStyle = "#f6be54";ctx.fill();ctx.strokeStyle = "#714b38";ctx.stroke();
  }
  ctx.restore();
}
