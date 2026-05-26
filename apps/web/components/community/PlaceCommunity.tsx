"use client";

import { useState, useEffect, useCallback } from "react";
import { useSession } from "next-auth/react";
import type { Question, Answer, AuthHeaders } from "@/lib/api";
import { getQuestions } from "@/lib/api";
import { useSocket } from "@/hooks/useSocket";
import QuestionComposer from "./QuestionComposer";
import QuestionCard from "./QuestionCard";

interface Props {
  placeId: string;
}

export default function PlaceCommunity({ placeId }: Props) {
  const { data: session } = useSession();
  const [questions, setQuestions] = useState<Question[]>([]);
  const [loading,   setLoading]   = useState(true);

  const auth: AuthHeaders | undefined = session?.user
    ? {
        "X-User-Id":    (session.user as { id?: string }).id ?? "",
        "X-User-Email": session.user.email ?? "",
        "X-User-Name":  session.user.name  ?? "Người dùng",
      }
    : undefined;

  const load = useCallback(async () => {
    const res = await getQuestions({ placeId });
    if (res.ok) setQuestions(res.data);
    setLoading(false);
  }, [placeId]);

  useEffect(() => { load(); }, [load]);

  // Real-time: prepend new questions / append new answers
  useSocket(placeId, {
    "question:new": (data) => {
      setQuestions((prev) => [data as Question, ...prev]);
    },
    "answer:new": (data) => {
      const { questionId, answer } = data as { questionId: string; answer: Answer };
      setQuestions((prev) =>
        prev.map((q) => {
          if (q.id !== questionId) return q;
          // Trigger the QuestionCard's appendAnswer via its exposed ref
          (q as unknown as { _appendAnswer?: (a: Answer) => void })._appendAnswer?.(answer);
          return { ...q, _count: { answers: q._count.answers + 1 } };
        }),
      );
    },
  });

  return (
    <div>
      <div style={{ fontFamily: "Unbounded, sans-serif", fontSize: 13, fontWeight: 700, color: "var(--g)", marginBottom: 12 }}>
        💬 Hỏi đáp cộng đồng
      </div>

      <QuestionComposer
        placeId={placeId}
        auth={auth}
        onDone={(q) => setQuestions((prev) => [q as Question, ...prev])}
      />

      {loading && (
        <p style={{ fontSize: 12.5, color: "var(--tm)", textAlign: "center", padding: 20 }}>
          Đang tải…
        </p>
      )}

      {!loading && questions.length === 0 && (
        <div
          style={{
            textAlign: "center", padding: "28px 0",
            color: "var(--tm)", fontSize: 13,
          }}
        >
          <div style={{ fontSize: 28, marginBottom: 8 }}>🌿</div>
          <p>Chưa có câu hỏi nào.<br />Hãy là người đầu tiên đặt câu hỏi!</p>
        </div>
      )}

      {questions.map((q) => (
        <QuestionCard key={q.id} question={q} auth={auth} userId={auth?.["X-User-Id"]} />
      ))}
    </div>
  );
}
