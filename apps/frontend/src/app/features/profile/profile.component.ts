import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';

interface Badge { icon: string; name: string; label: string; earned: boolean; }

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './profile.component.html',
  styleUrl: './profile.component.scss'
})
export class ProfileComponent {
  activeTab = signal<'activity' | 'badges' | 'stats'>('activity');

  stats = [
    { n: '47', l: 'Địa điểm đã ghé' },
    { n: '128', l: 'Câu hỏi đã hỏi' },
    { n: '85', l: 'Câu trả lời' },
    { n: '4', l: 'Hạng hiện tại' },
  ];

  badges: Badge[] = [
    { icon: '🏔', name: 'Trail Blazer', label: 'Trekking 5+ địa điểm', earned: true },
    { icon: '☕', name: 'Caffeine Explorer', label: 'Check-in 10 quán cà phê', earned: true },
    { icon: '📸', name: 'Lens Master', label: 'Ảnh được like 100+', earned: true },
    { icon: '🌿', name: 'Farm Friend', label: 'Thăm 3 nông trại', earned: true },
    { icon: '🔍', name: 'Fact Checker', label: 'Xác minh 20 review', earned: false },
    { icon: '👑', name: 'Top Contributor', label: 'Top 5% cộng đồng', earned: false },
  ];

  activities = [
    { icon: '📍', txt: 'Check-in Langbiang Summit Trail', time: '2 giờ trước', score: '+15 điểm' },
    { icon: '💬', txt: 'Trả lời câu hỏi về The Loft Coffee', time: 'Hôm qua', score: '+8 điểm' },
    { icon: '⭐', txt: 'Review Đồi Chè Cầu Đất', time: '2 ngày trước', score: '+12 điểm' },
    { icon: '✅', txt: 'Xác minh thông tin Hồ Xuân Hương', time: '3 ngày trước', score: '+5 điểm' },
    { icon: '📸', txt: 'Đăng ảnh Vườn Dâu La Oai', time: '1 tuần trước', score: '+10 điểm' },
  ];

  constructor(private router: Router) {}

  navigate(path: string) { this.router.navigate([path]); }
}