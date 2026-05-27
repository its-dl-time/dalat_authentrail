export interface Place {
  id: number;
  name: string;
  location: string;
  type: string;
  riskLevel: 'low' | 'medium' | 'high';
  score: number;
  fbScore: number;
  gmScore: number;
  ttScore: number;
  reviewCount: number;
  color: string;
  activeUsers: number;
  description: string;
  aiSummary: string;
  complaints: Complaint[];
  openHours: string;
  priceRange: string;
  bestTime: string;
  distance: string;
}

export interface Complaint {
  icon: string;
  text: string;
  sources: { label: string; type: 'fb' | 'gm' | 'tt' }[];
}

export interface CommunityPost {
  id: number;
  place: string;
  time: string;
  type: 'question' | 'review' | 'tip';
  author: string;
  av: string;
  rank: number;
  answers: number;
  questionsUsed: number;
  txt: string;
  likes: number;
  dislikes: number;
  gps: number;
  verified?: boolean;
  fromFeedback?: boolean;
}
