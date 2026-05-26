import { Hono } from "hono";
import { Platform, RiskLevel, TrustLevel } from "@prisma/client";
import { prisma } from "../lib/prisma";

export const placesRouter = new Hono();

// ─── GET /api/places ──────────────────────────────────────────────────────────
// Query: q, category, risk_level, page (1-based), page_size (max 50)

placesRouter.get("/", async (c) => {
  try {
    const q          = c.req.query("q")          || undefined;
    const category   = c.req.query("category")   || undefined;
    const rlParam    = c.req.query("risk_level");
    const page       = Math.max(1, parseInt(c.req.query("page")      || "1",  10));
    const pageSize   = Math.min(50, Math.max(1, parseInt(c.req.query("page_size") || "20", 10)));

    const riskLevel = rlParam && Object.values(RiskLevel).includes(rlParam as RiskLevel)
      ? (rlParam as RiskLevel)
      : undefined;

    const where = {
      ...(q        && { name: { contains: q, mode: "insensitive" as const } }),
      ...(category && { category }),
      ...(riskLevel && { riskScore: { riskLevel } }),
    };

    const [total, places] = await Promise.all([
      prisma.place.count({ where }),
      prisma.place.findMany({
        where,
        include: {
          riskScore:   { select: { riskScore: true, riskLevel: true } },
          liveStatus:  { select: { crowded: true, confidence: true, lastVerifiedAt: true, expiresAt: true } },
        },
        orderBy: { weightedRating: "desc" },
        skip:  (page - 1) * pageSize,
        take:  pageSize,
      }),
    ]);

    return c.json({
      ok: true,
      data: places,
      meta: { total, page, pageSize, totalPages: Math.ceil(total / pageSize) },
    });
  } catch (err) {
    console.error("GET /places:", err);
    return c.json({ ok: false, error: "Failed to fetch places" }, 500);
  }
});

// ─── GET /api/places/:id ──────────────────────────────────────────────────────
// Returns full place card: Place + RiskScore + PlatformSummaries + LiveStatus

placesRouter.get("/:id", async (c) => {
  try {
    const id = c.req.param("id");

    const place = await prisma.place.findUnique({
      where: { id },
      include: {
        riskScore:         true,
        platformSummaries: true,
        liveStatus:        true,
      },
    });

    if (!place) return c.json({ ok: false, error: "Place not found" }, 404);

    return c.json({ ok: true, data: place });
  } catch (err) {
    console.error("GET /places/:id:", err);
    return c.json({ ok: false, error: "Failed to fetch place" }, 500);
  }
});

// ─── GET /api/places/:id/reviews ──────────────────────────────────────────────
// Query: platform, trust_level, page, page_size
// Ordered by trust score desc so highest-quality reviews appear first

placesRouter.get("/:id/reviews", async (c) => {
  try {
    const placeId  = c.req.param("id");
    const platParam = c.req.query("platform");
    const tlParam   = c.req.query("trust_level");
    const page      = Math.max(1, parseInt(c.req.query("page")      || "1",  10));
    const pageSize  = Math.min(50, Math.max(1, parseInt(c.req.query("page_size") || "20", 10)));

    const platform   = platParam && Object.values(Platform).includes(platParam as Platform)
      ? (platParam as Platform) : undefined;
    const trustLevel = tlParam && Object.values(TrustLevel).includes(tlParam as TrustLevel)
      ? (tlParam as TrustLevel) : undefined;

    const where = {
      placeId,
      ...(platform   && { platform }),
      ...(trustLevel && { trustLevel }),
    };

    const [total, reviews] = await Promise.all([
      prisma.review.count({ where }),
      prisma.review.findMany({
        where,
        orderBy: [{ finalTrustScore: "desc" }, { contentCreatedAt: "desc" }],
        skip: (page - 1) * pageSize,
        take: pageSize,
      }),
    ]);

    return c.json({
      ok: true,
      data: reviews,
      meta: { total, page, pageSize, totalPages: Math.ceil(total / pageSize) },
    });
  } catch (err) {
    console.error("GET /places/:id/reviews:", err);
    return c.json({ ok: false, error: "Failed to fetch reviews" }, 500);
  }
});

// ─── GET /api/places/:id/risk ─────────────────────────────────────────────────
// Full risk breakdown: all sub-scores, topComplaints, riskReasons

placesRouter.get("/:id/risk", async (c) => {
  try {
    const placeId = c.req.param("id");

    const risk = await prisma.riskScore.findUnique({ where: { placeId } });

    if (!risk) return c.json({ ok: false, error: "Risk data not found" }, 404);

    return c.json({ ok: true, data: risk });
  } catch (err) {
    console.error("GET /places/:id/risk:", err);
    return c.json({ ok: false, error: "Failed to fetch risk score" }, 500);
  }
});
