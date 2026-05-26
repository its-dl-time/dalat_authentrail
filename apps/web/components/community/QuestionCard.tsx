"use client";

import { useState, useCallback } from "react";
import type { Question, Answer, AuthHeaders } from "@/lib/api";
import { getAnswers, postAnswer } from "@/lib/api";
import AnswerCard from "./AnswerCard";

function timeAgo(iso: string) {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60)    return "vừa xong";
  if (diff < 3600)  return `${Math.floor(diff / 60)} phút trước`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} giờ trước`;
  return `${Math.floor(diff / 86400)} ngày trước`;
}

interface Props {
  question: Question;
  auth?:    AuthHeaders;
  userId?:  string;
}

export default function QuestionCard({ question, auth, userId }: Props) {
  const [expanded,  setExpanded]  = useState(false);
  const [answers,   setAnswers]   = useState<Answer[]>([]);
  const [loadingA,  setLoadingA]  = useState(false);
  const [replyText, setReplyText] = useState("");
  const [sending,   setSending]   = useState(false);

  const totalAnswers = question._count.answers;
  const isPoll       = question.type === "poll";
  const totalVotes   = question.pollOptions.reduce((s, o) => s + o.voteCount, 0);

  const loadAnswers = useCallback(async () => {
    if (expanded) { setExpanded(false); return; }
    setLoadingA(true);
    const res = await getAnswers(question.id);
    if (res.ok) setAnswers(res.data);
    setLoadingA(false);
    setExpanded(true);
  }, [expanded, question.id]);

  // Append a server-pushed answer (from Socket.io)
  const appendAnswer = useCallback((answer: Answer) => {
    setAnswers((prev) => [answer, ...prev]);
  }, []);
  // Expose appendAnswer so parent can call it on socket events
  (question as unknown as { _appendAnswer?: typeof appendAnswer })._appendAnswer = appendAnswer;

  async function sendReply() {
    if (!auth || !replyText.trim()) return;
    setSending(true);
    const res = await postAnswer(question.id, { text: replyText.trim() }, auth);
    if (res.ok) {
      setAnswers((prev) => [res.data, ...prev]);
      setReplyText("");
      setExpanded(true);
    }
    setSending(false);
  }

  async function votePoll(optId: string) {
    if (!auth) return;
    await postAnswer(question.id, { pollOptionId: optId }, auth);
  }

  return (
    <div
      style={{
        background: "#fff", borderRadius: 14,
        border: "1px solid rgba(11,89,47,.08)",
        padding: 16, marginBottom: 12,
      }}
    >
      {/* Header */}
      <div style={{ display: "flex", alignItems: "flex-start", gap: 10, marginBottom: 10 }}>
        <div
          style={{
            width: 34, height: 34, borderRadius: "50%", flexShrink: 0,
            background: "var(--g)", display: "grid", placeItems: "center",
            color: "#fff", fontSize: 13, fontWeight: 700,
          }}
        >
          {(question.author.name ?? "?")[0].toUpperCase()}
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: "var(--tx)" }}>
              {question.author.name}
            </span>
            {question.place && (
              <span
                style={{
                  fontSize: 10.5, color: "var(--o)", fontWeight: 600,
                  background: "rgba(223,111,59,.1)", padding: "2px 7px", borderRadius: 7,
                }}
              >
                {question.place.name}
              </span>
            )}
            <span style={{ fontSize: 10.5, color: "var(--tm)", marginLeft: "auto" }}>
              {timeAgo(question.createdAt)}
            </span>
          </div>
          <p style={{ fontSize: 14, color: "var(--tx)", marginTop: 5, lineHeight: 1.55 }}>
            {question.text}
          </p>
        </div>
      </div>

      {/* Poll options */}
      {isPoll && question.pollOptions.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 6, marginBottom: 10 }}>
          {question.pollOptions.map((opt) => {
            const pct = totalVotes > 0 ? Math.round((opt.voteCount / totalVotes) * 100) : 0;
            return (
              <button
                key={opt.id}
                onClick={() => votePoll(opt.id)}
                style={{
                  position: "relative", textAlign: "left", overflow: "hidden",
                  border: "1.5px solid rgba(11,89,47,.15)", borderRadius: 9,
                  padding: "8px 12px", background: "none", cursor: auth ? "pointer" : "default",
                }}
              >
                <div
                  style={{
                    position: "absolute", inset: 0, left: 0,
                    width: `${pct}%`, background: "rgba(11,89,47,.07)",
                    borderRadius: 7,
                  }}
                />
                <span style={{ position: "relative", fontSize: 12.5, fontWeight: 500, color: "var(--tx)" }}>
                  {opt.label}
                </span>
                <span style={{ position: "relative", fontSize: 11, color: "var(--tm)", marginLeft: 8 }}>
                  {pct}%
                </span>
              </button>
            );
          })}
          <p style={{ fontSize: 11, color: "var(--tm)", marginTop: 2 }}>
            {totalVotes} lượt bình chọn
          </p>
        </div>
      )}

      {/* Footer: answer count + toggle */}
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <button
          onClick={loadAnswers}
          style={{
            fontSize: 12, fontWeight: 600, color: "var(--g)",
            background: "rgba(11,89,47,.06)", border: "none",
            padding: "4px 11px", borderRadius: 9, cursor: "pointer",
          }}
        >
          {loadingA ? "…" : expanded ? "Ẩn câu trả lời" : `💬 ${totalAnswers} câu trả lời`}
        </button>
      </div>

      {/* Answers list */}
      {expanded && (
        <div style={{ marginTop: 12 }}>
          {answers.length === 0 && (
            <p style={{ fontSize: 12.5, color: "var(--tm)", fontStyle: "italic" }}>
              Chưa có câu trả lời nào.
            </p>
          )}
          {answers.map((a) => (
            <AnswerCard key={a.id} answer={a} auth={auth} userId={userId} />
          ))}

          {/* Inline reply box */}
          {auth && (
            <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
              <input
                value={replyText}
                onChange={(e) => setReplyText(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && sendReply()}
                placeholder="Viết câu trả lời…"
                style={{
                  flex: 1, border: "1.5px solid rgba(11,89,47,.15)",
                  borderRadius: 9, padding: "7px 12px",
                  fontSize: 12.5, fontFamily: "inherit", outline: "none",
                }}
              />
              <button
                onClick={sendReply}
                disabled={sending || !replyText.trim()}
                style={{
                  fontSize: 12.5, fontWeight: 600, padding: "7px 14px",
                  background: "var(--g)", color: "#fff", border: "none",
                  borderRadius: 9, cursor: sending ? "wait" : "pointer",
                }}
              >
                {sending ? "…" : "Gửi"}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
