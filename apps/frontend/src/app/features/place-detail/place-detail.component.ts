import { Component, OnInit, signal } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { MockDataService } from '../../core/services/mock-data.service';
import { Place } from '../../core/models/place.model';

@Component({
  selector: 'app-place-detail',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './place-detail.component.html',
  styleUrl: './place-detail.component.scss'
})
export class PlaceDetailComponent implements OnInit {
  place = signal<Place | null>(null);
  activeTab = signal<'overview' | 'community' | 'similar'>('overview');

  similarPlaces: Place[] = [];

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private mockData: MockDataService
  ) {}

  ngOnInit() {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    const all = this.mockData.getPlaces();
    const found = all.find(p => p.id === id) || all[0];
    this.place.set(found);
    this.similarPlaces = all.filter(p => p.id !== found.id).slice(0, 3);
  }

  goBack() { this.router.navigate(['explore']); }
  goPlace(id: number) { this.router.navigate(['place', id]); }
  goPlanner() { this.router.navigate(['ai-planner']); }
  goCommunity() { this.router.navigate(['community']); }

  getRiskClass(level: string): string {
    return level === 'low' ? 'rl' : level === 'medium' ? 'rm' : 'rh';
  }
  getRiskLabel(level: string): string {
    return level === 'low' ? 'Rủi ro Thấp' : level === 'medium' ? 'Rủi ro Trung bình' : 'Rủi ro Cao';
  }
  getScoreStatus(score: number): string {
    return score >= 80 ? 'Đáng tin cậy cao' : score >= 60 ? 'Khá tin cậy' : 'Cần thận trọng';
  }
}