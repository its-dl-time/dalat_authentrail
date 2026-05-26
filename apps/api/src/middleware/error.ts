import type { Context } from "hono";
import type { ApiError } from "@dalat/types";

export function errorResponse(c: Context, status: number, message: string, code?: string) {
  const body: ApiError = { ok: false, error: message, ...(code ? { code } : {}) };
  return c.json(body, status as Parameters<typeof c.json>[1]);
}

export function notFound(c: Context) {
  return errorResponse(c, 404, "Not found", "NOT_FOUND");
}
