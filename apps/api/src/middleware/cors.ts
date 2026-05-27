import { cors } from "hono/cors";
import { env } from "../lib/env";

const ALLOWED = env.CORS_ORIGIN
  .split(",")
  .map((o) => o.trim())
  .filter(Boolean);

export const corsMiddleware = cors({
  origin: (origin) => {
    if (!origin) return ALLOWED[0];
    if (ALLOWED.includes(origin)) return origin;
    // allow all Vercel preview deployments for the same project
    if (origin.endsWith(".vercel.app")) return origin;
    return ALLOWED[0];
  },
  allowHeaders: ["Content-Type", "Authorization", "X-User-Id", "X-User-Email", "X-User-Name"],
  allowMethods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
  credentials: true,
});
