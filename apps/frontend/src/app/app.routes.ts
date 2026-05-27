import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', redirectTo: 'home', pathMatch: 'full' },
  { path: 'home', loadComponent: () => import('./features/home/home.component').then(m => m.HomeComponent) },
  { path: 'explore', loadComponent: () => import('./features/search/search.component').then(m => m.SearchComponent) },
  { path: 'place/:id', loadComponent: () => import('./features/place-detail/place-detail.component').then(m => m.PlaceDetailComponent) },
  { path: 'community', loadComponent: () => import('./features/community/community.component').then(m => m.CommunityComponent) },
  { path: 'ai-planner', loadComponent: () => import('./features/ai-planner/ai-planner.component').then(m => m.AIPlannerComponent) },  { path: 'profile', loadComponent: () => import('./features/profile/profile.component').then(m => m.ProfileComponent) },
  { path: '**', redirectTo: 'home' }
];