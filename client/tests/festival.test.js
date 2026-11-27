import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import { levels,heroes,festivalTrack } from "../src/festival.js";

test("every arena has instructions and a distinct, cached, playable PCM arrangement",async()=>{
  const hashes=new Set();
  for(const [mode,[name,instruction]] of Object.entries(levels)){
    assert.ok(name && instruction);
    const url=festivalTrack(mode);
    assert.equal(festivalTrack(mode),url);
    const bytes=Buffer.from(await (await fetch(url)).arrayBuffer());
    assert.equal(bytes.toString("ascii",0,4),"RIFF");
    assert.equal(bytes.readUInt32LE(40),bytes.length-44);
    hashes.add(createHash("sha256").update(bytes).digest("hex"));
  }
  assert.equal(hashes.size,10);
});
test("eleven distinct character previews ship with the client",async()=>{
  const designs=new Set();
  for(const id of Object.keys(heroes)){
    designs.add(await readFile(new URL("../public/assets/festival/"+id+".svg",import.meta.url),"utf8"));
  }
  assert.equal(designs.size,11);
});
