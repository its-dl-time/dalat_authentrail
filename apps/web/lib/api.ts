// API client — all fetch calls to the Hono backend
// TODO: set NEXT_PUBLIC_API_URL in .env.local (Railway URL after deployment)

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:4000";

// ─── Response types (match Prisma output shape) ───────────────────────────────

export type RiskLevel   = "low" | "medium" | "high";
export type Platform    = "google_maps" | "facebook" | "tiktok";
export type TrustLevel  = "low" | "medium" | "high";
export type CrowdLevel  = "empty" | "moderate" | "busy" | "very_busy" | "unknown";

export interface PlaceListItem {
  id:               string;
  name:             string;
  category:         string;
  address?:         string | null;
  lat:              number;
  lng:              number;
  googleMapsUrl?:   string | null;
  coverImageUrl?:   string | null;
  imageUrls:        string[];
  googleMapsRating?: number | null;
  weightedRating?:  number | null;
  riskScore?:       { riskScore: number; riskLevel: RiskLevel } | null;
  liveStatus?:      { crowded: CrowdLevel; confidence: number; lastVerifiedAt: string; expiresAt: string } | null;
}

export interface RiskScore {
  id:                      string;
  placeId:                 string;
  riskScore:               number;
  riskLevel:               RiskLevel;
  dataQualityRisk:         number;
  sentimentGap:            number;
  negativeSocialVsMapsGap: number;
  topicGap:                number;
  engagementGap:           number;
  coverageRisk:            number;
  googleMapsAvgSentiment:  number;
  socialAvgSentiment:      number;
  topComplaints:           string[];
  riskReasons:             string[];
  computedAt:              string;
  updatedAt:               string;
}

export interface PlatformSummary {
  id:                     string;
  placeId:                string;
  platform:               Platform;
  recordCount:            number;
  usefulRecordCount:      number;
  avgSentimentScore:      number;
  negativeSentimentRatio: number;
  avgQualityScore:        number;
  avgServiceScore:        number;
  avgPriceScore:          number;
  avgSceneryScore:        number;
  avgCrowdedScore:        number;
  avgFoodDrinkScore:      number;
  avgCleanlinessScore:    number;
  avgLocationScore:       number;
  googleMapsRatingAvg?:   number | null;
  googleMapsRatingMaster?: number | null;
  updatedAt:              string;
}

export interface LiveStatus {
  crowded:          CrowdLevel;
  confidence:       number;
  answerCount:      number;
  lastVerifiedAt:   string;
  expiresAt:        string;
  priceNote?:       string | null;
  viewNote?:        string | null;
  recommendedToGo?: boolean | null;
}

export interface PlaceFull extends PlaceListItem {
  riskScore?:         RiskScore | null;
  platformSummaries:  PlatformSummary[];
  liveStatus?:        LiveStatus | null;
}

export interface Review {
  id:                string;
  placeId:           string;
  platform:          Platform;
  contentText?:      string | null;
  translatedTextVi?: string | null;
  language?:         string | null;
  rating?:           number | null;
  finalTrustScore:   number;
  trustLevel:        TrustLevel;
  qualityScore:      number;
  sentimentScore:    number;
  serviceScore:      number;
  priceScore:        number;
  sceneryScore:      number;
  hasRiskFlag:       boolean;
  riskFlags:         string[];
  authorKey:         string;
  engagementCount:   number;
  contentCreatedAt?: string | null;
  scrapedAt:         string;
}

export interface PageMeta {
  total:      number;
  page:       number;
  pageSize:   number;
  totalPages: number;
}

// ─── Low-level fetch ──────────────────────────────────────────────────────────

type ApiOk<T>  = { ok: true;  data: T };
type ApiErr    = { ok: false; error: string };
type ApiResult<T> = ApiOk<T> | ApiErr;

async function apiFetch<T>(path: string, opts?: RequestInit): Promise<ApiResult<T>> {
  try {
    const res = await fetch(`${API_BASE}/api${path}`, {
      next: { revalidate: 60 },
      ...opts,
    });
    const body = await res.json().catch(() => ({ ok: false, error: `HTTP ${res.status}` }));
    return body as ApiResult<T>;
  } catch {
    return { ok: false, error: "API unavailable — backend chưa được khởi động" };
  }
}

// ─── Place endpoints ──────────────────────────────────────────────────────────

export interface SearchParams {
  q?:          string;
  category?:   string;
  risk_level?: RiskLevel;
  page?:       number;
  page_size?:  number;
}

export async function searchPlaces(params: SearchParams = {}) {
  const qs = new URLSearchParams();
  if (params.q)          qs.set("q",          params.q);
  if (params.category)   qs.set("category",   params.category);
  if (params.risk_level) qs.set("risk_level", params.risk_level);
  if (params.page)       qs.set("page",       String(params.page));
  if (params.page_size)  qs.set("page_size",  String(params.page_size));

  return apiFetch<PlaceListItem[]>(`/places?${qs.toString()}`) as Promise<
    (ApiOk<PlaceListItem[]> & { meta: PageMeta }) | ApiErr
  >;
}

export function getPlace(id: string) {
  return apiFetch<PlaceFull>(`/places/${id}`);
}

export function getPlaceReviews(
  id: string,
  params: { platform?: Platform; trust_level?: TrustLevel; page?: number } = {}
) {
  const qs = new URLSearchParams();
  if (params.platform)    qs.set("platform",    params.platform);
  if (params.trust_level) qs.set("trust_level", params.trust_level);
  if (params.page)        qs.set("page",        String(params.page));
  return apiFetch<Review[]>(`/places/${id}/reviews?${qs.toString()}`);
}

export function getPlaceRisk(id: string) {
  return apiFetch<RiskScore>(`/places/${id}/risk`);
}

// ─── Q&A types ────────────────────────────────────────────────────────────────

export type QuestionType        = "poll" | "open";
export type VerificationLabel   = "at_location" | "recently_visited" | "local" | "regular_user" | "unverified";

export interface UserRef {
  id:        string;
  name:      string;
  avatarUrl?: string | null;
}

export interface PollOption {
  id:         string;
  questionId: string;
  label:      string;
  voteCount:  number;
}

export interface Question {
  id:          string;
  placeId:     string;
  place?:      { id: string; name: string; category: string };
  author:      UserRef;
  type:        QuestionType;
  text:        string;
  expiresAt:   string;
  createdAt:   string;
  pollOptions: PollOption[];
  _count:      { answers: number };
}

export interface Answer {
  id:                string;
  questionId:        string;
  author:            UserRef;
  verificationLabel: VerificationLabel;
  text?:             string | null;
  pollOptionId?:     string | null;
  pollOption?:       { id: string; label: true } | null;
  imageUrl?:         string | null;
  likeCount:         number;
  dislikeCount:      number;
  createdAt:         string;
}

// Headers sent to the API to authenticate the current user
export type AuthHeaders = {
  "X-User-Id":    string;
  "X-User-Email": string;
  "X-User-Name":  string;
};

// ─── Q&A endpoints ────────────────────────────────────────────────────────────

export function getQuestions(params: { placeId?: string; page?: number; page_size?: number } = {}) {
  const qs = new URLSearchParams();
  if (params.placeId)   qs.set("placeId",   params.placeId);
  if (params.page)      qs.set("page",      String(params.page));
  if (params.page_size) qs.set("page_size", String(params.page_size));
  return apiFetch<Question[]>(`/questions?${qs.toString()}`);
}

export function getAnswers(questionId: string) {
  return apiFetch<Answer[]>(`/answers?questionId=${questionId}`);
}

export function createQuestion(
  data: { placeId: string; type: QuestionType; text: string; pollOptions?: string[]; expiresHours?: number },
  auth: AuthHeaders,
) {
  return apiFetch<Question>("/questions", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...auth },
    body: JSON.stringify(data),
    cache: "no-store",
  } as RequestInit);
}

export function postAnswer(
  questionId: string,
  data: { text?: string; pollOptionId?: string },
  auth: AuthHeaders,
) {
  return apiFetch<Answer>(`/answers/${questionId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...auth },
    body: JSON.stringify(data),
    cache: "no-store",
  } as RequestInit);
}

export function voteAnswer(answerId: string, value: 1 | -1, auth: AuthHeaders) {
  return apiFetch<{ likeCount: number; dislikeCount: number }>(`/answers/${answerId}/vote`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...auth },
    body: JSON.stringify({ value }),
    cache: "no-store",
  } as RequestInit);
}
