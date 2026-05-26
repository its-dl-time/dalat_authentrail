import type { CrowdLevel } from "@prisma/client";
import { prisma } from "./prisma";

// Keywords → crowd level (Vietnamese)
const CROWD_MAP: [CrowdLevel, string[]][] = [
  ["very_busy", ["rất đông", "quá đông", "cực đông"]],
  ["busy",      ["đông", "khá đông", "nhiều người"]],
  ["moderate",  ["bình thường", "vừa phải", "không quá đông"]],
  ["empty",     ["vắng", "ít người", "không đông"]],
];

function detectCrowd(text: string): CrowdLevel | null {
  const lower = text.toLowerCase();
  for (const [level, kws] of CROWD_MAP) {
    if (kws.some((k) => lower.includes(k))) return level;
  }
  return null;
}

// Aggregates answers from the last 24 h → updates LiveStatus for a place.
// Called fire-and-forget after each new answer is posted.
export async function aggregateLiveStatus(placeId: string): Promise<void> {
  const since = new Date(Date.now() - 24 * 3600 * 1000);

  const answers = await prisma.answer.findMany({
    where: { createdAt: { gte: since }, question: { placeId } },
    select: { text: true, pollOption: { select: { label: true } } },
    take: 100,
  });

  if (answers.length === 0) return;

  const tally: Record<string, number> = { very_busy: 0, busy: 0, moderate: 0, empty: 0 };
  const priceNotes: string[] = [];
  const viewNotes:  string[] = [];
  let goCount = 0, noGoCount = 0;

  for (const ans of answers) {
    const full = [ans.text, ans.pollOption?.label].filter(Boolean).join(" ");
    if (!full) continue;

    const crowd = detectCrowd(full);
    if (crowd && crowd !== "unknown") tally[crowd]++;

    const lower = full.toLowerCase();
    if (lower.match(/giá|đắt|rẻ|tiền/)) priceNotes.push(ans.text ?? "");
    if (lower.match(/view|cảnh|đẹp|khung cảnh/)) viewNotes.push(ans.text ?? "");
    if (lower.match(/nên đến|recommend|worth|ok lắm/)) goCount++;
    if (lower.match(/không nên|tránh|thất vọng|tệ/)) noGoCount++;
  }

  const [topLevel, topCount] = (Object.entries(tally) as [CrowdLevel, number][]).reduce(
    (a, b) => (b[1] > a[1] ? b : a),
  );
  const crowded: CrowdLevel = topCount > 0 ? topLevel : "unknown";

  const confidence = Math.min(1, answers.length / 20);
  const expiresAt  = new Date(Date.now() + 6 * 3600 * 1000);

  await prisma.liveStatus.upsert({
    where:  { placeId },
    update: {
      crowded,
      priceNote:       priceNotes[0] ?? null,
      viewNote:        viewNotes[0]  ?? null,
      recommendedToGo: goCount > noGoCount ? true : noGoCount > goCount ? false : null,
      confidence,
      answerCount:     answers.length,
      lastVerifiedAt:  new Date(),
      expiresAt,
    },
    create: {
      placeId, crowded,
      priceNote:       priceNotes[0] ?? null,
      viewNote:        viewNotes[0]  ?? null,
      recommendedToGo: goCount > noGoCount ? true : noGoCount > goCount ? false : null,
      confidence,
      answerCount:     answers.length,
      expiresAt,
    },
  });
}
