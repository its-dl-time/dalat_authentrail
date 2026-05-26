import { z } from "zod";

const envSchema = z.object({
  NODE_ENV:     z.enum(["development", "production", "test"]).default("development"),
  PORT:         z.coerce.number().default(4000),
  DATABASE_URL: z.string().min(1, "DATABASE_URL is required"),
  REDIS_URL:    z.string().default("redis://localhost:6379"),
  NEXTAUTH_SECRET: z.string().default("dev-secret-change-in-production"),
  CORS_ORIGIN:  z.string().default("http://localhost:3000"),
});

const parsed = envSchema.safeParse(process.env);

if (!parsed.success) {
  console.error("❌ Invalid environment variables:");
  console.error(parsed.error.flatten().fieldErrors);
  process.exit(1);
}

export const env = parsed.data;
