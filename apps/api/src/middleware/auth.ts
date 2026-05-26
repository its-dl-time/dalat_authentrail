import { createMiddleware } from "hono/factory";
import { prisma } from "../lib/prisma";
import type { HonoEnv } from "../types";

// Reads X-User-Id / X-User-Email / X-User-Name headers sent by the web app
// and upserts a User row, then stores the internal DB id in context.
export const authMiddleware = createMiddleware<HonoEnv>(async (c, next) => {
  const googleId = c.req.header("X-User-Id");
  const email    = c.req.header("X-User-Email");
  const name     = c.req.header("X-User-Name") ?? "Người dùng";

  if (googleId && email) {
    try {
      const user = await prisma.user.upsert({
        where:  { email },
        update: { name },
        create: { email, name },
        select: { id: true },
      });
      c.set("userId", user.id);
    } catch {
      // auth failure is non-fatal; protected routes check for userId
    }
  }

  await next();
});

export function requireAuth(c: { get: (k: "userId") => string | undefined }): string | undefined {
  return c.get("userId");
}
