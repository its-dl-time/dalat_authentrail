"use client";

import { useState } from "react";
import type { Answer, AuthHeaders } from "@/lib/api";
import { voteAnswer } from "@/lib/api";

const LABEL_MAP: Record<string, { text: string; color: string }> = {
  at_location:      { text: "Đang ở đây",     color: "#0B592F" },
  recently_visited: { text: "Vừa đến",        color: "#8CA70A" },
  local:            { text: "Người địa phương", color: "#EEB627" },
  regular_user:     { text: "Hay đến",         color: "#936440" },
  unverified:       { text: "Chưa xác minh",   color: "#6b6b6b" },
};

function timeAgo(iso: string) {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60)   return "vừa xong";
  if (diff < 3600) return `${Math.floor(diff / 60)} phút trước`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} giờ trước`;
  return `${Math.floor(diff / 86400)} ngày trước`;
}

interface Props {
  answer:    Answer;
  auth?:     AuthHeaders;
  userId?:   string;
}

export default function AnswerCard({ answer, auth, userId }: Props) {
  const [likes,    setLikes]    = useState(answer.likeCount);
  const [dislikes, setDislikes] = useState(answer.dislikeCount);
  const [voted,    setVoted]    = useState<1 | -1 | null>(null);
  const [loading,  setLoading]  = useState(false);

  const label = LABEL_MAP[answer.verificationLabel] ?? LABEL_MAP.unverified;

  async function handleVote(value: 1 | -1) {
    if (!auth || !userId || loading) return;
    setLoading(true);
    const res = await voteAnswer(answer.id, value, auth);
    if (res.ok) {
      setLikes(res.data.likeCount);
      setDislikes(res.data.dislikeCount);
      setVoted(voted === value ? null : value);
    }
    setLoading(false);
  }

  return (
    <div
      style={{
        display: "flex", gap: 10, padding: "10px 0",
        borderBottom: "1px solid rgba(11,89,47,.06)",
      }}
    >
      {/* Avatar */}
      <div
        style={{
          width: 32, height: 32, borderRadius: "50%", flexShrink: 0,
          background: "var(--g)", display: "grid", placeItems: "center",
          color: "#fff", fontSize: 12, fontWeight: 700,
        }}
      >
        {(answer.author.name ?? "?")[0].toUpperCase()}
      </div>

      <div style={{ flex: 1 }}>
        {/* Author row */}
        <div style={{ display: "flex", alignItems: "center", gap: 7, marginBottom: 4 }}>
          <span style={{ fontSize: 12.5, fontWeight: 600, color: "var(--tx)" }}>
            {answer.author.name}
          </span>
          <span
            style={{
              fontSize: 9.5, fontWeight: 600, color: label.color,
              background: `${label.color}18`, padding: "2px 7px", borderRadius: 8,
            }}
          >
            {label.text}
          </span>
          <span style={{ fontSize: 10.5, color: "var(--tm)", marginLeft: "auto" }}>
            {timeAgo(answer.createdAt)}
          </span>
        </div>

        {/* Poll option */}
        {answer.pollOption && (
          <div
            style={{
              display: "inline-block", fontSize: 12.5, fontWeight: 600,
              color: "var(--g)", background: "rgba(11,89,47,.07)",
              padding: "3px 10px", borderRadius: 8, marginBottom: 4,
            }}
          >
            {answer.pollOption.label}
          </div>
        )}

        {/* Text */}
        {answer.text && (
          <p style={{ fontSize: 13, color: "var(--tx)", lineHeight: 1.6, marginBottom: 8 }}>
            {answer.text}
          </p>
        )}

        {/* Vote row */}
        <div style={{ display: "flex", gap: 8 }}>
          <button
            onClick={() => handleVote(1)}
            disabled={!auth || loading}
            style={{
              display: "flex", alignItems: "center", gap: 4,
              fontSize: 11.5, fontWeight: 600,
              color: voted === 1 ? "var(--g)" : "var(--tm)",
              background: voted === 1 ? "rgba(11,89,47,.08)" : "none",
              border: "1px solid",
              borderColor: voted === 1 ? "var(--g)" : "rgba(0,0,0,.1)",
              padding: "3px 8px", borderRadius: 8, cursor: auth ? "pointer" : "default",
            }}
          >
            👍 {likes}
          </button>
          <button
            onClick={() => handleVote(-1)}
            disabled={!auth || loading}
            style={{
              display: "flex", alignItems: "center", gap: 4,
              fontSize: 11.5, fontWeight: 600,
              color: voted === -1 ? "var(--o)" : "var(--tm)",
              background: voted === -1 ? "rgba(223,111,59,.08)" : "none",
              border: "1px solid",
              borderColor: voted === -1 ? "var(--o)" : "rgba(0,0,0,.1)",
              padding: "3px 8px", borderRadius: 8, cursor: auth ? "pointer" : "default",
            }}
          >
            👎 {dislikes}
          </button>
        </div>
      </div>
    </div>
  );
}
