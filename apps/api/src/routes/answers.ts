import { Hono } from "hono";
import { prisma } from "../lib/prisma";
import { aggregateLiveStatus } from "../lib/liveStatus";
import { emitToPlace } from "../lib/socket";
import { authMiddleware, requireAuth } from "../middleware/auth";
import type { HonoEnv } from "../types";

export const answersRouter = new Hono<HonoEnv>();
answersRouter.use("*", authMiddleware);

// GET /api/answers?questionId=xxx
answersRouter.get("/", async (c) => {
  const questionId = c.req.query("questionId");
  if (!questionId) return c.json({ ok: false, error: "questionId là bắt buộc" }, 400);

  const answers = await prisma.answer.findMany({
    where: { questionId },
    include: {
      author:     { select: { id: true, name: true, avatarUrl: true } },
      pollOption: { select: { id: true, label: true } },
    },
    orderBy: { likeCount: "desc" },
  });

  return c.json({ ok: true, data: answers });
});

// POST /api/answers/:questionId
answersRouter.post("/:questionId", async (c) => {
  const userId = requireAuth(c);
  if (!userId) return c.json({ ok: false, error: "Cần đăng nhập." }, 401);

  const questionId = c.req.param("questionId");

  let body: { text?: string; pollOptionId?: string };
  try { body = await c.req.json(); }
  catch { return c.json({ ok: false, error: "Body không hợp lệ" }, 400); }

  const { text, pollOptionId } = body;
  if (!text?.trim() && !pollOptionId)
    return c.json({ ok: false, error: "Cần có text hoặc pollOptionId" }, 400);

  const question = await prisma.question.findUnique({
    where:  { id: questionId },
    select: { id: true, placeId: true, expiresAt: true },
  });
  if (!question)              return c.json({ ok: false, error: "Câu hỏi không tồn tại" }, 404);
  if (question.expiresAt < new Date()) return c.json({ ok: false, error: "Câu hỏi đã hết hạn" }, 400);

  const [answer] = await prisma.$transaction([
    prisma.answer.create({
      data: {
        questionId,
        authorId: userId,
        text:         text?.trim() ?? null,
        pollOptionId: pollOptionId ?? null,
      },
      include: {
        author:     { select: { id: true, name: true, avatarUrl: true } },
        pollOption: { select: { id: true, label: true } },
      },
    }),
    ...(pollOptionId
      ? [prisma.pollOption.update({
          where: { id: pollOptionId },
          data:  { voteCount: { increment: 1 } },
        })]
      : []),
  ]);

  // Update LiveStatus and broadcast (fire-and-forget)
  aggregateLiveStatus(question.placeId).catch(console.error);
  emitToPlace(question.placeId, "answer:new", { questionId, answer });

  return c.json({ ok: true, data: answer }, 201);
});

// POST /api/answers/:id/vote  — body: { value: 1 | -1 }
answersRouter.post("/:id/vote", async (c) => {
  const userId = requireAuth(c);
  if (!userId) return c.json({ ok: false, error: "Cần đăng nhập." }, 401);

  const answerId = c.req.param("id");
  let body: { value: number };
  try { body = await c.req.json(); }
  catch { return c.json({ ok: false, error: "Body không hợp lệ" }, 400); }

  const value = body.value === 1 ? 1 : -1;

  const existing = await prisma.vote.findUnique({
    where: { answerId_userId: { answerId, userId } },
  });

  if (existing) {
    if (existing.value === value) {
      // Toggle off
      await prisma.$transaction([
        prisma.vote.delete({ where: { answerId_userId: { answerId, userId } } }),
        prisma.answer.update({
          where: { id: answerId },
          data:  value === 1
            ? { likeCount:    { decrement: 1 } }
            : { dislikeCount: { decrement: 1 } },
        }),
      ]);
    } else {
      // Flip vote
      await prisma.$transaction([
        prisma.vote.update({ where: { answerId_userId: { answerId, userId } }, data: { value } }),
        prisma.answer.update({
          where: { id: answerId },
          data:  value === 1
            ? { likeCount: { increment: 1 }, dislikeCount: { decrement: 1 } }
            : { likeCount: { decrement: 1 }, dislikeCount: { increment: 1 } },
        }),
      ]);
    }
  } else {
    await prisma.$transaction([
      prisma.vote.create({ data: { answerId, userId, value } }),
      prisma.answer.update({
        where: { id: answerId },
        data:  value === 1
          ? { likeCount:    { increment: 1 } }
          : { dislikeCount: { increment: 1 } },
      }),
    ]);
  }

  const updated = await prisma.answer.findUnique({
    where:  { id: answerId },
    select: { likeCount: true, dislikeCount: true },
  });

  return c.json({ ok: true, data: updated });
});
