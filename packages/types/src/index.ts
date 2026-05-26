// ─── Place ────────────────────────────────────────────────────────────────────

export type PlaceCategory =
  | "Quán cà phê"
  | "Nhà hàng"
  | "Địa điểm du lịch"
  | "Lưu trú"
  | "Mua sắm"
  | "Giải trí"
  | "Khác";

export type RiskLevel = "low" | "medium" | "high";
export type TrustLevel = "low" | "medium" | "high";
export type Platform = "google_maps" | "facebook" | "tiktok";

export interface PlaceLocation {
  lat: number;
  lng: number;
  address?: string;
  googleMapsUrl?: string;
}

export interface Place {
  id: string;
  name: string;
  category: PlaceCategory;
  location: PlaceLocation;
  coverImageUrl?: string;
  imageUrls: string[];
  googleMapsRating: number | null;
  weightedRating: number | null;
  riskScore: number | null;
  riskLevel: RiskLevel | null;
  liveStatus?: LiveStatus | null;
  createdAt: string;
  updatedAt: string;
}

export interface PlaceSummary {
  id: string;
  name: string;
  category: PlaceCategory;
  location: PlaceLocation;
  coverImageUrl?: string;
  googleMapsRating: number | null;
  weightedRating: number | null;
  riskScore: number | null;
  riskLevel: RiskLevel | null;
  liveStatus?: Pick<LiveStatus, "crowded" | "confidence" | "lastVerifiedAt"> | null;
}

// ─── Risk ─────────────────────────────────────────────────────────────────────

export interface RiskBreakdown {
  placeId: string;
  riskScore: number;
  riskLevel: RiskLevel;
  dataQualityRisk: number;
  sentimentGap: number;
  negativeSocialVsMapsGap: number;
  topicGap: number;
  engagementGap: number;
  coverageRisk: number;
  googleMapsAvgSentiment: number;
  socialAvgSentiment: number;
  platformAgreement: number;
  topComplaints: string[];
  riskReasons: string[];
}

export interface PlatformSummary {
  placeId: string;
  platform: Platform;
  recordCount: number;
  usefulRecordCount: number;
  avgSentimentScore: number;
  negativeSentimentRatio: number;
  avgQualityScore: number;
  avgServiceScore: number;
  avgPriceScore: number;
  avgSceneryScore: number;
  avgCrowdedScore: number;
  avgFoodDrinkScore: number;
  avgCleanlinessScore: number;
  avgLocationScore: number;
  googleMapsRatingAvg?: number;
  googleMapsRatingMaster?: number;
}

// ─── Review ───────────────────────────────────────────────────────────────────

export interface Review {
  id: string;
  placeId: string;
  platform: Platform;
  contentText: string | null;
  rating: number | null;
  sentimentScore: number;
  qualityScore: number;
  trustLevel: TrustLevel;
  finalTrustScore: number;
  language: string | null;
  translatedTextVi: string | null;
  authorKey: string;
  engagementCount: number;
  hasRiskFlag: boolean;
  riskFlags: string[];
  serviceScore: number;
  priceScore: number;
  sceneryScore: number;
  contentCreatedAt: string;
  scrapedAt: string;
}

export interface ReviewPage {
  reviews: Review[];
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
}

// ─── Search ───────────────────────────────────────────────────────────────────

export interface SearchParams {
  q?: string;
  category?: PlaceCategory;
  riskLevel?: RiskLevel;
  minRating?: number;
  maxRiskScore?: number;
  page?: number;
  pageSize?: number;
}

export interface SearchResult {
  places: PlaceSummary[];
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
}

// ─── Community (Phase 2) ──────────────────────────────────────────────────────

export type QuestionType = "poll" | "open";
export type VerificationLabel =
  | "at_location"
  | "recently_visited"
  | "local"
  | "regular_user"
  | "unverified";

export interface PollOption {
  id: string;
  label: string;
  voteCount: number;
}

export interface Question {
  id: string;
  placeId: string;
  placeName: string;
  authorId: string;
  authorName: string;
  type: QuestionType;
  text: string;
  pollOptions?: PollOption[];
  answerCount: number;
  expiresAt: string;
  createdAt: string;
}

export interface Answer {
  id: string;
  questionId: string;
  placeId: string;
  authorId: string;
  authorName: string;
  verificationLabel: VerificationLabel;
  text: string | null;
  pollOptionId: string | null;
  imageUrl: string | null;
  likeCount: number;
  dislikeCount: number;
  createdAt: string;
}

export interface UserReputation {
  userId: string;
  totalAnswers: number;
  likeScore: number;
  badge: "new" | "contributor" | "trusted" | "local_expert";
  rank: number;
}

// ─── Live Status (Phase 2) ────────────────────────────────────────────────────

export interface LiveStatus {
  placeId: string;
  crowded: "empty" | "moderate" | "busy" | "very_busy" | "unknown";
  priceNote: string | null;
  viewNote: string | null;
  recommendedToGo: boolean | null;
  confidence: number;
  answerCount: number;
  lastVerifiedAt: string;
  expiresAt: string;
}

// ─── Auth / User ──────────────────────────────────────────────────────────────

export interface User {
  id: string;
  email: string;
  name: string;
  avatarUrl: string | null;
  reputation: UserReputation | null;
  createdAt: string;
}

// ─── API Response wrappers ────────────────────────────────────────────────────

export interface ApiSuccess<T> {
  ok: true;
  data: T;
}

export interface ApiError {
  ok: false;
  error: string;
  code?: string;
}

export type ApiResponse<T> = ApiSuccess<T> | ApiError;
