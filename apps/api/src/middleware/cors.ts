import { cors } from "hono/cors";
import { env } from "../lib/env";

export const corsMiddleware = cors({
  origin: env.CORS_ORIGIN,
  allowHeaders: ["Content-Type", "Authorization", "X-User-Id", "X-User-Email", "X-User-Name"],
  allowMethods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
  credentials: true,
});
