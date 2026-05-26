import { Hono } from "hono";
import { prisma } from "../lib/prisma";
import { emitToPlace } from "../lib/socket";
import { authMiddleware, requireAuth } from "../middleware/auth";
import type { HonoEnv } from "../types";

export const questionsRouter = new Hono<HonoEnv>();
questionsRouter.use("*", authMiddleware);

// GET /api/questions?placeId=&page=1&page_size=10
// placeId is optional — omit for global newsfeed
questionsRouter.get("/", async (c) => {
  const placeId  = c.req.query("placeId") || undefined;
  const page     = Math.max(1, parseInt(c.req.query("page")      || "1",  10));
  const pageSize = Math.min(20, Math.max(1, parseInt(c.req.query("page_size") || "10", 10)));

  const now   = new Date();
  const where = {
    expiresAt: { gt: now },
    ...(placeId ? { placeId } : {}),
  };

  const [total, questions] = await Promise.all([
    prisma.question.count({ where }),
    prisma.question.findMany({
      where,
      include: {
        place:       { select: { id: true, name: true, category: true } },
        author:      { select: { id: true, name: true, avatarUrl: true } },
        pollOptions: true,
        _count:      { select: { answers: true } },
      },
      orderBy: { createdAt: "desc" },
      skip:    (page - 1) * pageSize,
      take:    pageSize,
    }),
  ]);

  return c.json({
    ok: true,
    data: questions,
    meta: { total, page, pageSize, totalPages: Math.ceil(total / pageSize) },
  });
});

// POST /api/questions
questionsRouter.post("/", async (c) => {
  const userId = requireAuth(c);
  if (!userId) return c.json({ ok: false, error: "Cần đăng nhập." }, 401);

  let body: {
    placeId: string;
    type: string;
    text: string;
    pollOptions?: string[];
    expiresHours?: number;
  };
  try { body = await c.req.json(); }
  catch { return c.json({ ok: false, error: "Body không hợp lệ" }, 400); }

  const { placeId, type, text, pollOptions, expiresHours = 24 } = body;
  if (!placeId || !type || !text?.trim())
    return c.json({ ok: false, error: "Thiếu trường bắt buộc (placeId, type, text)" }, 400);
  if (!["poll", "open"].includes(type))
    return c.json({ ok: false, error: "type phải là 'poll' hoặc 'open'" }, 400);
  if (type === "poll" && (!Array.isArray(pollOptions) || pollOptions.length < 2))
    return c.json({ ok: false, error: "Poll cần ít nhất 2 lựa chọn" }, 400);

  const expiresAt = new Date(
    Date.now() + Math.min(72, Math.max(1, expiresHours)) * 3600 * 1000,
  );

  const question = await prisma.question.create({
    data: {
      placeId,
      authorId: userId,
      type: type as "poll" | "open",
      text: text.trim(),
      expiresAt,
      ...(type === "poll" && {
        pollOptions: {
          create: (pollOptions as string[]).map((label) => ({ label: label.trim() })),
        },
      }),
    },
    include: {
      place:       { select: { id: true, name: true, category: true } },
      author:      { select: { id: true, name: true, avatarUrl: true } },
      pollOptions: true,
      _count:      { select: { answers: true } },
    },
  });

  emitToPlace(placeId, "question:new", question);

  return c.json({ ok: true, data: question }, 201);
});
