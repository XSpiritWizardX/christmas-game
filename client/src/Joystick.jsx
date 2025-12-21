import React, { useEffect, useRef, useState } from "react";

const KEY_MOVE = new Set(["KeyW", "KeyA", "KeyS", "KeyD"]);
const KEY_ACTION = "Space";

const isTypingTarget = (target) => {
  if (!target) return false;
  const tag = target.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || target.isContentEditable;
};

export default function Joystick({ onMove, onAction }) {
  const baseRef = useRef(null);
  const pointerIdRef = useRef(null);
  const keysRef = useRef({ w: false, a: false, s: false, d: false });
  const [knob, setKnob] = useState({ x: 0, y: 0 });

  useEffect(() => {
    const base = baseRef.current;
    if (!base) return undefined;

    const radius = 36;
    const applyKeys = () => {
      let dx = 0;
      let dy = 0;
      if (keysRef.current.w) dy -= 1;
      if (keysRef.current.s) dy += 1;
      if (keysRef.current.a) dx -= 1;
      if (keysRef.current.d) dx += 1;
      const mag = Math.hypot(dx, dy);
      if (mag > 1) {
        dx /= mag;
        dy /= mag;
      }
      setKnob({ x: dx * radius, y: dy * radius });
      onMove?.(dx, dy);
    };

    const handlePointerDown = (event) => {
      if (pointerIdRef.current !== null) return;
      pointerIdRef.current = event.pointerId;
      base.setPointerCapture(event.pointerId);
      handleMove(event);
    };

    const handlePointerUp = (event) => {
      if (pointerIdRef.current !== event.pointerId) return;
      pointerIdRef.current = null;
      setKnob({ x: 0, y: 0 });
      onMove?.(0, 0);
    };

    const handleMove = (event) => {
      if (pointerIdRef.current === null) return;
      if (pointerIdRef.current !== event.pointerId) return;
      const rect = base.getBoundingClientRect();
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;
      let dx = event.clientX - centerX;
      let dy = event.clientY - centerY;
      const distance = Math.hypot(dx, dy);
      if (distance > radius) {
        dx = (dx / distance) * radius;
        dy = (dy / distance) * radius;
      }
      setKnob({ x: dx, y: dy });
      onMove?.(dx / radius, dy / radius);
    };

    base.addEventListener("pointerdown", handlePointerDown);
    base.addEventListener("pointermove", handleMove);
    base.addEventListener("pointerup", handlePointerUp);
    base.addEventListener("pointercancel", handlePointerUp);

    const handleKeyDown = (event) => {
      if (isTypingTarget(event.target)) return;
      if (event.code === KEY_ACTION) {
        event.preventDefault();
        if (!event.repeat) {
          onAction?.();
        }
        return;
      }
      if (!KEY_MOVE.has(event.code)) return;
      event.preventDefault();
      if (event.code === "KeyW") keysRef.current.w = true;
      if (event.code === "KeyA") keysRef.current.a = true;
      if (event.code === "KeyS") keysRef.current.s = true;
      if (event.code === "KeyD") keysRef.current.d = true;
      applyKeys();
    };

    const handleKeyUp = (event) => {
      if (isTypingTarget(event.target)) return;
      if (!KEY_MOVE.has(event.code)) return;
      event.preventDefault();
      if (event.code === "KeyW") keysRef.current.w = false;
      if (event.code === "KeyA") keysRef.current.a = false;
      if (event.code === "KeyS") keysRef.current.s = false;
      if (event.code === "KeyD") keysRef.current.d = false;
      applyKeys();
    };

    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("keyup", handleKeyUp);

    return () => {
      base.removeEventListener("pointerdown", handlePointerDown);
      base.removeEventListener("pointermove", handleMove);
      base.removeEventListener("pointerup", handlePointerUp);
      base.removeEventListener("pointercancel", handlePointerUp);
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("keyup", handleKeyUp);
    };
  }, [onAction, onMove]);

  return (
    <div ref={baseRef} className="joystick-base" aria-label="Movement joystick">
      <div
        className="joystick-knob"
        style={{ transform: `translate(${knob.x}px, ${knob.y}px)` }}
      />
    </div>
  );
}
