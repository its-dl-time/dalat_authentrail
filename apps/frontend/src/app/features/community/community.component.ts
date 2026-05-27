import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MockDataService } from '../../core/services/mock-data.service';
import { CommunityPost } from '../../core/models/place.model';

@Component({
  selector: 'app-community',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './community.component.html',
  styleUrl: './community.component.scss'
})
export class CommunityComponent {
  posts = signal<CommunityPost[]>([]);
  activeFilter = signal('all');
  searchQuery = signal('');
  composerText = signal('');
  composerPlace = signal('');
  showComposer = signal(false);

  filters = [
    { value: 'all', label: 'Tất cả' },
    { value: 'question', label: '❓ Câu hỏi' },
    { value: 'review', label: '⭐ Review' },
    { value: 'tip', label: '💡 Mẹo' },
  ];

  suggestedQuestions = [
    { q: 'Langbiang hôm nay có sương mù không?', place: 'Langbiang', time: '5 người hỏi hôm nay' },
    { q: 'The Loft Coffee còn bàn trống không?', place: 'The Loft Coffee', time: '3 người hỏi hôm nay' },
    { q: 'Đường lên Cầu Đất có khó đi không?', place: 'Cầu Đất', time: '8 người hỏi tuần này' },
  ];

  constructor(private mockData: MockDataService) {
    this.posts.set(this.mockData.getCommunityPosts());
  }

  get filteredPosts(): CommunityPost[] {
    return this.posts().filter(p => {
      const matchFilter = this.activeFilter() === 'all' || p.type === this.activeFilter();
      const matchSearch = p.txt.toLowerCase().includes(this.searchQuery().toLowerCase())
        || p.place.toLowerCase().includes(this.searchQuery().toLowerCase());
      return matchFilter && matchSearch;
    });
  }

  submitPost() {
    if (!this.composerText().trim()) return;
    const newPost: CommunityPost = {
      id: Date.now(),
      place: this.composerPlace() || 'Đà Lạt',
      time: 'Vừa xong',
      type: 'review',
      author: 'An Nhiên',
      av: 'AN',
      rank: 4,
      answers: 0,
      questionsUsed: 0,
      txt: this.composerText(),
      likes: 0,
      dislikes: 0,
      gps: 0,
      verified: false
    };
    this.posts.update(p => [newPost, ...p]);
    this.composerText.set('');
    this.composerPlace.set('');
    this.showComposer.set(false);
  }

  likePost(post: CommunityPost) {
    this.posts.update(posts => posts.map(p => p.id === post.id ? { ...p, likes: p.likes + 1 } : p));
  }

  useQuestion(q: string) {
    this.composerText.set(q);
    this.showComposer.set(true);
  }

  getTypeLabel(type: string): string {
    return type === 'question' ? '❓ Câu hỏi' : type === 'review' ? '⭐ Review' : '💡 Mẹo';
  }
  getTypeClass(type: string): string {
    return type === 'question' ? 'q' : type === 'review' ? 'r' : 't';
  }
}