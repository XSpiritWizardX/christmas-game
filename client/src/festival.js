export const levels = {
  workshop: ["Santa's Workshop", "Pick up a present at LOAD. Deliver to the glowing dock, alternating north and south.", "#ffe1bc", "#b44538"],
  raceway: ["Reindeer Raceway", "Pass the numbered gates in order. Reach the finish first.", "#d5ead9", "#18735b"],
  avalanche: ["Avalanche Escape", "Outrun the snow front. Pass each gate and reach shelter before losing three hearts.", "#d4dfee", "#364c79"],
  chaos: ["Christmas Chaos", "Dodge the moving storms. Their paths change every six seconds. Survive for points.", "#ede1f4", "#81397b"],
  candy_maze: ["Candy Cane Maze", "Explore the winding passages and collect candy. Each cane is worth four points. Clearing the maze ends the round.", "#f8dbe3", "#a7234b"],
  lake: ["Frozen Lake", "Stay on the drifting floes. One melts as another forms. Open water costs hearts.", "#87cadc", "#225a80"],
  heist: ["Grinch's Heist", "Raid the opposing vault and return gifts to yours. Use Action near your vault to stop a thief.", "#d6e8c1", "#386244"],
  boss: ["North Pole Boss Battle", "Approach the Frost Ogre and press Action to strike. Dodge its orbiting frost through three phases.", "#dcdcf5", "#534683"],
  sleigh: ["Sleigh Battle", "Drive inside the circular rink. Press Action near a rival to ram their sleigh over the edge.", "#e5daca", "#88573e"],
  ornaments: ["Ornament Hunt", "Explore the grove. Press Action beside an unsearched spruce to uncover hidden ornaments.", "#cde3cf", "#255f4c"]
};
export const heroes = {
  santa:"Santa Claus", mrs_claus:"Mrs. Claus", mischief:"Mistletoe Menace", nutcracker:"Nutcracker",
  penguin:"Christmas Penguin", polar_bear:"Polar Bear", soldier:"Toy Soldier", yeti:"Yeti",
  tree:"Christmas Tree", queen:"Snow Queen", knight:"Gingerbread Knight"
};

// Original bell ostinatos. Generate one small mono PCM loop per arrangement on demand.
const cache = new Map();
export function festivalTrack(mode) {
  if (cache.has(mode)) return cache.get(mode);
  const index = [...Object.keys(levels),"victory","defeat","countdown"].indexOf(mode);
  if (index < 0) return "";
  const beat = .21 + (index % 5)*.025, rate=12000, length=Math.floor(rate*beat*32);
  const buf=new ArrayBuffer(44+length*2), view=new DataView(buf);
  const tag=(offset,str)=>[...str].forEach((c,i)=>view.setUint8(offset+i,c.charCodeAt(0)));
  tag(0,"RIFF"); view.setUint32(4,36+length*2,true); tag(8,"WAVE"); tag(12,"fmt ");
  view.setUint32(16,16,true); view.setUint16(20,1,true); view.setUint16(22,1,true);
  view.setUint32(24,rate,true); view.setUint32(28,rate*2,true); view.setUint16(32,2,true);
  view.setUint16(34,16,true); tag(36,"data"); view.setUint32(40,length*2,true);
  const scale=[0,2,4,7,9,12,7,4];
  for(let i=0;i<length;i++){
    const t=i/rate, n=Math.floor(t/beat), u=t-n*beat;
    const root=196*2**((index%7)/12), f=root*2**(scale[(n*(1+index%3)+(n>>2)+index)%8]/12);
    const wave=Math.sin(2*Math.PI*f*u)+.32*Math.sin(4*Math.PI*f*u)+.2*Math.sin(Math.PI*root*t);
    view.setInt16(44+i*2,Math.round(8500*wave*Math.min(1,u*180)*Math.exp(-10*u)*Math.min(1,(length-i)/120)),true);
  }
  const url=URL.createObjectURL(new Blob([buf],{type:"audio/wav"}));
  cache.set(mode,url);
  return url;
}

export function drawArena(ctx, mode, arena, player){
  if(!levels[mode] || !arena?.markers) return;
  const accent=levels[mode][3];
  ctx.save();
  if(mode==="sleigh"){
    ctx.fillStyle="#fbf2e3"; ctx.beginPath();ctx.arc(480,270,240,0,2*Math.PI);ctx.fill();ctx.strokeStyle=accent;ctx.stroke();
  }
  if(mode==="avalanche"){ctx.fillStyle="#fff";ctx.fillRect(0,0,arena.front||0,540);}
  ctx.font="bold 13px sans-serif";ctx.textAlign="center";
  for(const [i,m] of arena.markers.entries()){
    ctx.beginPath();ctx.arc(m.x,m.y,m.r,0,Math.PI*2);
    ctx.fillStyle=mode==="lake"?"#e6fbff":accent;ctx.fill();
    ctx.strokeStyle=mode==="workshop" && i===(player?.cargo?1+(player.checkpoint%2):0)?"#ffbc20":"#ffffff";ctx.lineWidth=4;ctx.stroke();
    ctx.fillStyle=mode==="lake"?accent:"#fff";
    ctx.fillText(mode==="boss"?"OGRE "+arena.hp:m.label,m.x,m.y+4);
  }
  for(const m of arena.danger){ctx.beginPath();ctx.arc(m.x,m.y,m.r,0,Math.PI*2);ctx.fillStyle="#b43a66bb";ctx.fill();ctx.fillStyle="#fff";ctx.fillText("❄",m.x,m.y+5);}
  ctx.restore();
}
