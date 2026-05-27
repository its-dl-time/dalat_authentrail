import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './home.component.html',
  styleUrl: './home.component.scss'
})
export class HomeComponent {
  constructor(private router: Router) {}

  navigate(path: string) {
    this.router.navigate([path]);
  }

  features = [
    { icon: '🔍', cls: 'g', title: 'Risk Score AI', desc: 'Tổng hợp dữ liệu từ Facebook, Google Maps, TikTok — lọc qua AI cho ra điểm rủi ro minh bạch.' },
    { icon: '👥', cls: 'o', title: 'Cộng Đồng Xác Thực', desc: 'Người dùng tại chỗ báo cáo real-time. Mỗi review được gắn GPS và xác minh chéo.' },
    { icon: '🤖', cls: 'y', title: 'AI Lập Lịch Thông Minh', desc: 'Agent AI tạo hành trình cá nhân hóa, cập nhật theo thời tiết và mật độ khách.' },
  ];

  stats = [
    { n: '240+', l: 'Địa điểm xác thực' },
    { n: '18K', l: 'Review đã phân tích' },
    { n: '3', l: 'Nền tảng tổng hợp' },
  ];
}