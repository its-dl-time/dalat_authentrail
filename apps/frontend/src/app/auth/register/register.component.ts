import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="register-container">
      <div class="container">
        <h1>📝 Đăng Ký</h1>
        <p class="coming-soon">🔄 Component đang được phát triển...</p>
      </div>
    </div>
  `,
  styles: [`
    .register-container { padding: 2rem 0; text-align: center; }
    .coming-soon { color: #DF6F3B; font-size: 18px; }
  `]
})
export class RegisterComponent {}
