import { Component, signal, computed } from '@angular/core';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MockDataService } from '../../core/services/mock-data.service';
import { Place } from '../../core/models/place.model';

@Component({
  selector: 'app-search',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './search.component.html',
  styleUrl: './search.component.scss'
})
export class SearchComponent {
  searchQuery = signal('');
  selectedType = signal('all');
  activeRisk = signal('all');

  allPlaces: Place[] = [];

  types = [
    { value: 'all', label: 'Tất cả' },
    { value: 'Trekking', label: 'Trekking' },
    { value: 'Cà phê', label: 'Cà phê' },
    { value: 'Nông trại', label: 'Nông trại' },
    { value: 'Danh lam', label: 'Danh lam' },
    { value: 'Ẩm thực', label: 'Ẩm thực' },
  ];

  riskChips = [
    { value: 'all', label: 'Tất cả', cls: 'all' },
    { value: 'low', label: '● Thấp', cls: 'low' },
    { value: 'medium', label: '● Trung bình', cls: 'med' },
    { value: 'high', label: '● Cao', cls: 'high' },
  ];

  constructor(private mockData: MockDataService, private router: Router) {
    this.allPlaces = this.mockData.getPlaces();
  }

  get filteredPlaces(): Place[] {
    return this.allPlaces.filter(p => {
      const matchSearch = p.name.toLowerCase().includes(this.searchQuery().toLowerCase())
        || p.location.toLowerCase().includes(this.searchQuery().toLowerCase());
      const matchType = this.selectedType() === 'all' || p.type === this.selectedType();
      const matchRisk = this.activeRisk() === 'all' || p.riskLevel === this.activeRisk();
      return matchSearch && matchType && matchRisk;
    });
  }

  getRiskClass(level: string): string {
    return level === 'low' ? 'rl' : level === 'medium' ? 'rm' : 'rh';
  }

  getRiskLabel(level: string): string {
    return level === 'low' ? 'Thấp' : level === 'medium' ? 'Trung bình' : 'Cao';
  }

  getScoreBarWidth(score: number): string {
    return `${score}%`;
  }

  goDetail(id: number) {
    this.router.navigate(['place', id]);
  }
}