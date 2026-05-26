import Redis from "ioredis";
import { env } from "./env";

export const redis = new Redis(env.REDIS_URL, {
  lazyConnect: true,
  enableOfflineQueue: false,
  retryStrategy: (times: number) => {
    if (times > 3) return null;
    return Math.min(times * 200, 2000);
  },
});

redis.on("error", (err: Error) => {
  if (process.env.NODE_ENV === "development") {
    console.warn("⚠️  Redis unavailable:", err.message);
  }
});
