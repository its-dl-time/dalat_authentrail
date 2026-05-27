import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-ranking',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="ranking-container">
      <div class="container">
        <h1>🏆 Bảng Xếp Hạng</h1>
        <p class="coming-soon">🔄 Component đang được phát triển...</p>
      </div>
    </div>
  `,
  styles: [`
    .ranking-container { padding: 2rem 0; text-align: center; }
    .coming-soon { color: #DF6F3B; font-size: 18px; }
  `]
})
export class RankingComponent {}
