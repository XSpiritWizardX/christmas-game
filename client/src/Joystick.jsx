import React, { useEffect, useRef, useState } from "react";

export default function Joystick({ onMove }) {
  const baseRef = useRef(null);
  const pointerIdRef = useRef(null);
  const [knob, setKnob] = useState({ x: 0, y: 0 });

  useEffect(() => {
    const base = baseRef.current;
    if (!base) return undefined;

    const radius = 36;

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

    return () => {
      base.removeEventListener("pointerdown", handlePointerDown);
      base.removeEventListener("pointermove", handleMove);
      base.removeEventListener("pointerup", handlePointerUp);
      base.removeEventListener("pointercancel", handlePointerUp);
    };
  }, [onMove]);

  return (
    <div ref={baseRef} className="joystick-base" aria-label="Movement joystick">
      <div
        className="joystick-knob"
        style={{ transform: `translate(${knob.x}px, ${knob.y}px)` }}
      />
    </div>
  );
}
