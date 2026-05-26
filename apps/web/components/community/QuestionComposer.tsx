"use client";

import { useState } from "react";
import type { AuthHeaders, QuestionType } from "@/lib/api";
import { createQuestion } from "@/lib/api";

interface Props {
  placeId: string;
  auth?:   AuthHeaders;
  onDone?: (question: unknown) => void;
}

export default function QuestionComposer({ placeId, auth, onDone }: Props) {
  const [open,        setOpen]        = useState(false);
  const [type,        setType]        = useState<QuestionType>("open");
  const [text,        setText]        = useState("");
  const [opts,        setOpts]        = useState(["", ""]);
  const [loading,     setLoading]     = useState(false);
  const [error,       setError]       = useState("");

  if (!open) {
    return (
      <button
        onClick={() => auth ? setOpen(true) : undefined}
        style={{
          width: "100%", padding: "12px 16px",
          background: auth ? "rgba(11,89,47,.06)" : "rgba(0,0,0,.03)",
          border: "1.5px dashed",
          borderColor: auth ? "rgba(11,89,47,.2)" : "rgba(0,0,0,.1)",
          borderRadius: 12, textAlign: "left",
          fontSize: 13, color: auth ? "var(--tm)" : "#aaa",
          cursor: auth ? "pointer" : "default",
          marginBottom: 16,
        }}
      >
        {auth ? "✏️ Đặt câu hỏi về địa điểm này…" : "🔒 Đăng nhập để đặt câu hỏi"}
      </button>
    );
  }

  async function submit() {
    if (!auth || !text.trim()) return;
    setLoading(true);
    setError("");

    const pollOptions = type === "poll" ? opts.filter((o) => o.trim()) : undefined;
    if (type === "poll" && (!pollOptions || pollOptions.length < 2)) {
      setError("Poll cần ít nhất 2 lựa chọn.");
      setLoading(false);
      return;
    }

    const res = await createQuestion({ placeId, type, text: text.trim(), pollOptions }, auth);
    if (res.ok) {
      onDone?.(res.data);
      setOpen(false);
      setText("");
      setOpts(["", ""]);
      setType("open");
    } else {
      setError(res.error);
    }
    setLoading(false);
  }

  return (
    <div
      style={{
        background: "#fff", borderRadius: 14,
        border: "1.5px solid rgba(11,89,47,.15)",
        padding: 16, marginBottom: 16,
      }}
    >
      {/* Type toggle */}
      <div style={{ display: "flex", gap: 6, marginBottom: 12 }}>
        {(["open", "poll"] as QuestionType[]).map((t) => (
          <button
            key={t}
            onClick={() => setType(t)}
            style={{
              fontSize: 11.5, fontWeight: 600, padding: "4px 12px", borderRadius: 10,
              background: type === t ? "var(--g)" : "rgba(11,89,47,.07)",
              color:      type === t ? "#fff"     : "var(--g)",
              border:     "none", cursor: "pointer",
            }}
          >
            {t === "open" ? "Câu hỏi mở" : "Bình chọn"}
          </button>
        ))}
      </div>

      {/* Question text */}
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Ví dụ: Hiện tại chỗ này có đông không?"
        rows={2}
        style={{
          width: "100%", resize: "vertical",
          border: "1.5px solid rgba(11,89,47,.15)", borderRadius: 9,
          padding: "9px 12px", fontSize: 13, fontFamily: "inherit",
          outline: "none", color: "var(--tx)",
        }}
      />

      {/* Poll options */}
      {type === "poll" && (
        <div style={{ marginTop: 10 }}>
          {opts.map((opt, i) => (
            <div key={i} style={{ display: "flex", gap: 6, marginBottom: 6 }}>
              <input
                value={opt}
                onChange={(e) => {
                  const next = [...opts];
                  next[i] = e.target.value;
                  setOpts(next);
                }}
                placeholder={`Lựa chọn ${i + 1}`}
                style={{
                  flex: 1, border: "1.5px solid rgba(11,89,47,.12)",
                  borderRadius: 8, padding: "7px 10px", fontSize: 12.5,
                  fontFamily: "inherit", outline: "none",
                }}
              />
              {opts.length > 2 && (
                <button
                  onClick={() => setOpts(opts.filter((_, j) => j !== i))}
                  style={{ fontSize: 14, background: "none", border: "none", cursor: "pointer", color: "var(--o)" }}
                >
                  ✕
                </button>
              )}
            </div>
          ))}
          {opts.length < 4 && (
            <button
              onClick={() => setOpts([...opts, ""])}
              style={{
                fontSize: 11.5, color: "var(--g)", background: "none",
                border: "none", cursor: "pointer", fontWeight: 600,
              }}
            >
              + Thêm lựa chọn
            </button>
          )}
        </div>
      )}

      {error && <p style={{ fontSize: 12, color: "var(--o)", marginTop: 8 }}>{error}</p>}

      {/* Actions */}
      <div style={{ display: "flex", gap: 8, marginTop: 12, justifyContent: "flex-end" }}>
        <button
          onClick={() => setOpen(false)}
          style={{
            fontSize: 12.5, padding: "7px 14px", borderRadius: 10,
            background: "none", border: "1px solid rgba(0,0,0,.1)",
            cursor: "pointer", color: "var(--tm)",
          }}
        >
          Huỷ
        </button>
        <button
          onClick={submit}
          disabled={loading || !text.trim()}
          style={{
            fontSize: 12.5, fontWeight: 600, padding: "7px 16px", borderRadius: 10,
            background: loading || !text.trim() ? "#ccc" : "var(--g)",
            border: "none", cursor: loading ? "wait" : "pointer", color: "#fff",
          }}
        >
          {loading ? "Đang gửi…" : "Đăng câu hỏi"}
        </button>
      </div>
    </div>
  );
}
