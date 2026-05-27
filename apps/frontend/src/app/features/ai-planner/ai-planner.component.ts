import { Component, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

interface TripPrefs {
  days: number;
  styles: string[];       // multi-select
  budget: string;
  groupType: string;
  avoid: string;
}

interface TimelineItem {
  time: string;
  place: string;
  det: string;
  alert: string | null;
  live: string | null;
}

interface TrackItem {
  time: string;
  place: string;
  status: string;
  type: 'ok' | 'warn' | 'upcoming';
}

interface SuggestedPlace {
  id: string;
  name: string;
  desc: string;
  score: number;
  alert: string | null;
  live: string | null;
  baseTime: string;
  baseDet: string;
}

interface PromptHistoryItem {
  q: string;
  added: string;
}

@Component({
  selector: 'app-ai-planner',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './ai-planner.component.html',
  styleUrl: './ai-planner.component.scss'
})
export class AIPlannerComponent {

  currentStep = signal(1);
  isGenerating = signal(false);
  showAddForm = signal(false);

  // ── Step 1 prefs ────────────────────────────────────────
  prefs = signal<TripPrefs>({
    days: 2,
    styles: [],
    budget: '',
    groupType: '',
    avoid: ''
  });

  styleOptions = [
    { value: 'nature',     emoji: '🏔', label: 'Thiên nhiên / Trekking' },
    { value: 'cafe',       emoji: '☕', label: 'Cà phê / Chill' },
    { value: 'food',       emoji: '🍽', label: 'Ẩm thực đặc sản' },
    { value: 'photo',      emoji: '📸', label: 'Check-in / View đẹp' },
    { value: 'adventure',  emoji: '🧗', label: 'Thể thao mạo hiểm' },
    { value: 'family',     emoji: '👨‍👩‍👧', label: 'Gia đình & Trẻ em' },
  ];

  budgetOptions = [
    { value: 'low',    emoji: '💸', label: '< 300K / ngày' },
    { value: 'mid',    emoji: '💳', label: '300K – 700K' },
    { value: 'high',   emoji: '💎', label: '700K – 1.5M' },
    { value: 'luxury', emoji: '✨', label: '> 1.5M' },
  ];

  groupOptions = [
    { value: 'solo',   emoji: '🧍', label: 'Một mình' },
    { value: 'couple', emoji: '💑', label: 'Cặp đôi' },
    { value: 'group',  emoji: '👯', label: 'Nhóm bạn' },
    { value: 'family', emoji: '👨‍👩‍👧', label: 'Gia đình' },
  ];

  isStyleSelected(val: string): boolean {
    return this.prefs().styles.includes(val);
  }

  toggleStyle(val: string) {
    this.prefs.update(p => {
      const styles = p.styles.includes(val)
        ? p.styles.filter(s => s !== val)
        : [...p.styles, val];
      return { ...p, styles };
    });
  }

  selectBudget(b: string) {
    this.prefs.update(p => ({ ...p, budget: p.budget === b ? '' : b }));
  }

  selectGroup(g: string) {
    this.prefs.update(p => ({ ...p, groupType: p.groupType === g ? '' : g }));
  }

  setDays(d: number) {
    this.prefs.update(p => ({ ...p, days: d }));
  }

  setAvoid(val: string) {
    this.prefs.update(p => ({ ...p, avoid: val }));
  }

  // ── Step 2 – địa điểm ───────────────────────────────────
  readonly allPlaces: SuggestedPlace[] = [
    {
      id: 'caudat',
      name: 'Đồi Chè Cầu Đất',
      desc: 'Thiên nhiên tuyệt đẹp, sương mù buổi sáng. Lý tưởng cho cặp đôi và nhiếp ảnh.',
      score: 84, alert: null,
      live: 'Sương mù đẹp · Xác nhận 12 phút trước',
      baseTime: '06:00', baseDet: 'Săn sương mù buổi sáng sớm · Score 84'
    },
    {
      id: 'loft',
      name: 'The Loft Coffee & Roastery',
      desc: 'Cà phê specialty nổi tiếng, view đẹp, không gian yên tĩnh. Phù hợp vibe chill.',
      score: 91, alert: null,
      live: 'Còn 3 bàn trống · Cập nhật 5 phút trước',
      baseTime: '09:00', baseDet: 'Cà phê sáng · Score 91'
    },
    {
      id: 'phandinh',
      name: 'Phố ẩm thực Phan Đình Phùng',
      desc: 'Ẩm thực đường phố đặc trưng Đà Lạt, bánh mì xíu mại, sữa đậu nành.',
      score: 78, alert: null, live: null,
      baseTime: '12:00', baseDet: 'Ăn trưa đặc sản Đà Lạt'
    },
    {
      id: 'langbiang',
      name: 'Langbiang Summit Trail',
      desc: 'Trekking chinh phục đỉnh núi, view toàn cảnh Đà Lạt. Cần thể lực tốt.',
      score: 87,
      alert: 'Đông hơn bình thường chiều nay',
      live: null,
      baseTime: '14:00', baseDet: 'Trekking chinh phục đỉnh · Score 87'
    },
    {
      id: 'choden',
      name: 'Chợ Đêm Đà Lạt',
      desc: 'Ẩm thực đường phố sầm uất. Nên đến trước 20:00 để tránh đông.',
      score: 72,
      alert: 'Rủi ro cao sau 20:00 — cẩn thận giá cả',
      live: null,
      baseTime: '18:00', baseDet: 'Ẩm thực đường phố buổi tối'
    },
    {
      id: 'xuanhuong',
      name: 'Hồ Xuân Hương',
      desc: 'Hồ nước trung tâm, đạp xe vòng hồ, thư giãn buổi chiều tà.',
      score: 70,
      alert: 'Đông cuối tuần',
      live: null,
      baseTime: '16:30', baseDet: 'Đạp xe & thư giãn ven hồ'
    },
  ];

  suggestedPlaces = signal<SuggestedPlace[]>([...this.allPlaces]);
  selectedPlaceIds = signal<string[]>([]);
  placePrompt = signal('');
  promptHistory = signal<PromptHistoryItem[]>([]);

  isPlaceSelected(id: string): boolean {
    return this.selectedPlaceIds().includes(id);
  }

  togglePlace(id: string) {
    this.selectedPlaceIds.update(ids =>
      ids.includes(id) ? ids.filter(i => i !== id) : [...ids, id]
    );
  }

  submitPlacePrompt() {
    const q = this.placePrompt().trim();
    if (!q) return;

    // Simulate AI adding a new place based on prompt
    const newPlace: SuggestedPlace = {
      id: 'ai_' + Date.now(),
      name: 'Gợi ý AI: ' + q,
      desc: 'Địa điểm được AI thêm theo yêu cầu của bạn. Kiểm tra thực tế trước khi đến.',
      score: 75, alert: null, live: 'Mới thêm bởi AI',
      baseTime: '15:00', baseDet: 'Địa điểm gợi ý theo yêu cầu'
    };

    this.suggestedPlaces.update(p => [...p, newPlace]);
    this.selectedPlaceIds.update(ids => [...ids, newPlace.id]);
    this.promptHistory.update(h => [...h, { q, added: newPlace.name }]);
    this.placePrompt.set('');
  }

  confirmPlaces() {
    // Build timeline from selected places (sorted by score desc, then base time)
    const selected = this.suggestedPlaces()
      .filter(p => this.selectedPlaceIds().includes(p.id))
      .sort((a, b) => a.baseTime.localeCompare(b.baseTime));

    const tl: TimelineItem[] = selected.map(p => ({
      time: p.baseTime,
      place: p.name,
      det: p.baseDet,
      alert: p.alert,
      live: p.live
    }));

    this.timeline.set(tl);
    this.goStep(3);
  }

  // ── Step 3 – timeline ────────────────────────────────────
  timeline = signal<TimelineItem[]>([]);

  addTime = signal('');
  addPlace = signal('');
  addDet = signal('');
  aiInput = signal('');

  addStop() {
    if (!this.addPlace().trim()) return;
    this.timeline.update(tl => [...tl, {
      time: this.addTime() || '—',
      place: this.addPlace(),
      det: this.addDet() || 'Điểm dừng bổ sung',
      alert: null,
      live: null
    }]);
    this.addTime.set('');
    this.addPlace.set('');
    this.addDet.set('');
    this.showAddForm.set(false);
  }

  removeStop(index: number) {
    this.timeline.update(tl => tl.filter((_, i) => i !== index));
  }

  moveStop(index: number, direction: -1 | 1) {
    this.timeline.update(tl => {
      const arr = [...tl];
      const target = index + direction;
      if (target < 0 || target >= arr.length) return arr;
      [arr[index], arr[target]] = [arr[target], arr[index]];
      return arr;
    });
  }

  aiRefine() {
    const input = this.aiInput().trim();
    if (!input) return;
    this.timeline.update(tl => {
      const newTl = [...tl];
      const insertAt = Math.max(Math.floor(newTl.length / 2), 1);
      newTl.splice(insertAt, 0, {
        time: '—',
        place: 'Gợi ý AI',
        det: `"${input}"`,
        alert: null,
        live: 'Được thêm bởi AI'
      });
      return newTl;
    });
    this.aiInput.set('');
  }

  // ── Step 4 – tracking ────────────────────────────────────
  trackItems: TrackItem[] = [
    { time: '08:00', place: 'Ăn sáng', status: 'Đã hoàn thành', type: 'ok' },
    { time: '10:00', place: 'The Loft Coffee', status: 'Đang hoạt động · Còn 3 bàn trống', type: 'ok' },
    { time: '12:00', place: 'Ăn trưa Phan Đình Phùng', status: 'Sắp tới · 2 tiếng nữa', type: 'upcoming' },
    { time: '13:30', place: 'Langbiang Summit Trail', status: '⚠ Đông hơn bình thường chiều nay', type: 'warn' },
  ];

  goStep(step: number) {
    this.currentStep.set(step);
  }

  getTrackDotClass(type: string): string {
    return type === 'ok' ? 'g' : type === 'warn' ? 'o' : 'c';
  }
}