import { Component, signal } from '@angular/core';
import { RouterOutlet, RouterLink, Router, NavigationEnd } from '@angular/router';
import { CommonModule } from '@angular/common';
import { filter } from 'rxjs/operators';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, CommonModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss'
})
export class AppComponent {
  isLoggedIn = signal(false);
  showLoginModal = signal(false);
  activeRoute = signal('home');

  navLinks = [
    { path: 'explore', label: 'Khám Phá' },
    { path: 'community', label: 'Cộng Đồng' },
    { path: 'ai-planner', label: 'AI Agent' },
  ];

  constructor(private router: Router) {
    this.router.events.pipe(
      filter(e => e instanceof NavigationEnd)
    ).subscribe((e: any) => {
      this.activeRoute.set(e.urlAfterRedirects.replace('/', '').split('/')[0] || 'home');
    });
  }

  navigate(path: string) {
    this.router.navigate([path]);
  }

  doLogin() {
    this.isLoggedIn.set(true);
    this.showLoginModal.set(false);
  }

  isActive(path: string): boolean {
    return this.activeRoute() === path;
  }
}