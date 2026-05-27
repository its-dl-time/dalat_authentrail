import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-compare',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="compare-container">
      <div class="container">
        <h1>So Sánh Địa Điểm</h1>
        <p class="coming-soon">🔄 Component đang được phát triển...</p>
      </div>
    </div>
  `,
  styles: [`
    .compare-container { padding: 2rem 0; text-align: center; }
    .coming-soon { color: #DF6F3B; font-size: 18px; }
  `]
})
export class CompareComponent {}

