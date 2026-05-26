import { PrismaClient } from "@prisma/client";

type PrismaGlobal = { prisma?: PrismaClient };
const globalForPrisma = globalThis as PrismaGlobal;

export const prisma: PrismaClient =
  globalForPrisma.prisma ??
  new PrismaClient({
    log: process.env.NODE_ENV === "development" ? ["query", "error", "warn"] : ["error"],
  });

if (process.env.NODE_ENV !== "production") {
  globalForPrisma.prisma = prisma;
}
