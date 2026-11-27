import React, { useState } from "react";
import { QRCodeSVG } from "qrcode.react";

export function inviteCode() {
  const code = new URLSearchParams(location.search).get("room")?.toUpperCase();
  return /^[A-Z]{4}$/.test(code || "") ? code : "";
}

export function RoomInvite({ code }) {
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState("");
  const url = new URL("/", location.origin);
  url.searchParams.set("room", code);
  async function share() {
    try {
      if (navigator.share) await navigator.share({ title: "Join my Snow Dash room", url: url.href });
      else {
        await navigator.clipboard.writeText(url.href);
        setMessage("Link copied");
      }
    } catch (error) {
      if (error.name !== "AbortError") setMessage("Copy the link below or scan the code.");
    }
  }
  return <section className="room-invite">
    <button onClick={() => setOpen(!open)} aria-expanded={open}>Invite friends</button>
    {open && <div>
      <QRCodeSVG value={url.href} size={144} marginSize={4} title={'Join room ' + code} />
      <input aria-label="Room invite link" readOnly value={url.href} onFocus={e => e.target.select()} />
      <button onClick={share}>{navigator.share ? "Share link" : "Copy link"}</button>
      <span role="status">{message}</span>
    </div>}
  </section>;
}
