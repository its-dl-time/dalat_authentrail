import { Hono } from "hono";
import { logger } from "hono/logger";
import { serve } from "@hono/node-server";
import type { Server as HttpServer } from "http";
import { corsMiddleware } from "./middleware/cors";
import { notFound } from "./middleware/error";
import { placesRouter } from "./routes/places";
import { questionsRouter } from "./routes/questions";
import { answersRouter } from "./routes/answers";
import { initSocket } from "./lib/socket";
import { env } from "./lib/env";

const app = new Hono();

// ─── Global middleware ─────────────────────────────────────────────────────
app.use("*", corsMiddleware);
app.use("*", logger());

// ─── Health check ──────────────────────────────────────────────────────────
app.get("/health", (c) => c.json({ ok: true, env: env.NODE_ENV }));

// ─── API routes ────────────────────────────────────────────────────────────
const api = new Hono();
api.route("/places",    placesRouter);
api.route("/questions", questionsRouter);
api.route("/answers",   answersRouter);

app.route("/api", api);

// ─── 404 ───────────────────────────────────────────────────────────────────
app.notFound(notFound);

// ─── Start ─────────────────────────────────────────────────────────────────
const httpServer = serve({ fetch: app.fetch, port: env.PORT }, () => {
  console.log(`🚀 API running on http://localhost:${env.PORT}`);
});

// Attach Socket.io to the same http server
initSocket(httpServer as unknown as HttpServer);

export default app;
