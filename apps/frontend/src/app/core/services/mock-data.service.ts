import { Injectable } from '@angular/core';
import { Place, CommunityPost } from '../models/place.model';

@Injectable({ providedIn: 'root' })
export class MockDataService {

  getPlaces(): Place[] {
    return [
      {
        id: 1,
        name: 'Langbiang Summit Trail',
        location: 'Lạc Dương, Đà Lạt',
        type: 'Trekking',
        riskLevel: 'low',
        score: 87,
        fbScore: 4.7,
        gmScore: 4.8,
        ttScore: 4.6,
        reviewCount: 1240,
        color: '#0B592F',
        activeUsers: 5,
        description: 'Cung đường trekking nổi tiếng nhất Đà Lạt với tầm nhìn panorama toàn thành phố.',
        aiSummary: 'Địa điểm được đánh giá cao nhất khu vực Lạc Dương. Hướng dẫn viên địa phương chuyên nghiệp, cơ sở hạ tầng tốt. Nên xuất phát sớm trước 7:00 để tránh đông.',
        openHours: '05:00 – 17:00',
        priceRange: '150.000 – 300.000đ',
        bestTime: 'Sáng sớm 5:00–8:00',
        distance: '12km từ trung tâm',
        complaints: [
          { icon: '👥', text: 'Đông vào cuối tuần và lễ tết, nên đặt tour trước.', sources: [{ label: 'Facebook', type: 'fb' }, { label: 'Google Maps', type: 'gm' }] },
          { icon: '🌧', text: 'Đường trơn khi mưa, cần giày trekking phù hợp.', sources: [{ label: 'TikTok', type: 'tt' }] }
        ]
      },
      {
        id: 2,
        name: 'The Loft Coffee & Roastery',
        location: 'Trung tâm Đà Lạt',
        type: 'Cà phê',
        riskLevel: 'low',
        score: 91,
        fbScore: 4.9,
        gmScore: 4.8,
        ttScore: 4.7,
        reviewCount: 890,
        color: '#EEB627',
        activeUsers: 3,
        description: 'Quán cà phê rang xay tại chỗ với không gian vintage độc đáo giữa lòng Đà Lạt.',
        aiSummary: 'Quán cà phê được review cao nhất trung tâm. Hạt rang đặc biệt từ nông trại Cầu Đất. Khuyến nghị đặt chỗ trước vào cuối tuần.',
        openHours: '07:00 – 22:00',
        priceRange: '45.000 – 90.000đ',
        bestTime: 'Sáng 8:00–11:00',
        distance: '2km từ Hồ Xuân Hương',
        complaints: [
          { icon: '⏳', text: 'Chờ đồ lâu vào giờ cao điểm buổi sáng cuối tuần.', sources: [{ label: 'Google Maps', type: 'gm' }] }
        ]
      },
      {
        id: 3,
        name: 'Đồi Chè Cầu Đất',
        location: 'Cầu Đất, Đà Lạt',
        type: 'Nông trại',
        riskLevel: 'low',
        score: 84,
        fbScore: 4.5,
        gmScore: 4.6,
        ttScore: 4.8,
        reviewCount: 620,
        color: '#2d6a4f',
        activeUsers: 4,
        description: 'Đồi chè xanh mướt trải dài với sương mù buổi sáng tạo khung cảnh thơ mộng.',
        aiSummary: 'Điểm chụp ảnh được yêu thích nhất Đà Lạt trên TikTok. Sương mù đẹp nhất lúc 6:00–8:30 sáng. Có hướng dẫn tham quan vườn chè.',
        openHours: '06:00 – 17:30',
        priceRange: '50.000 – 120.000đ',
        bestTime: 'Sáng sớm 6:00–8:30',
        distance: '25km từ trung tâm',
        complaints: [
          { icon: '🚗', text: 'Đường lên dốc hẹp, khó đi với xe lớn buổi sáng sớm.', sources: [{ label: 'Facebook', type: 'fb' }] },
          { icon: '🌫', text: 'Sương tan nhanh sau 9:00, nên đến sớm để có ảnh đẹp.', sources: [{ label: 'TikTok', type: 'tt' }, { label: 'Google Maps', type: 'gm' }] }
        ]
      },
      {
        id: 4,
        name: 'Hồ Xuân Hương',
        location: 'Trung tâm Đà Lạt',
        type: 'Danh lam',
        riskLevel: 'medium',
        score: 72,
        fbScore: 4.2,
        gmScore: 4.3,
        ttScore: 3.9,
        reviewCount: 2100,
        color: '#4a90e2',
        activeUsers: 8,
        description: 'Hồ nước trung tâm thành phố, biểu tượng của Đà Lạt với đường đi bộ quanh hồ.',
        aiSummary: 'Địa điểm check-in phổ biến nhưng thường rất đông khách. Buổi sáng sớm và chiều tối là thời điểm đẹp nhất. Khu vực xung quanh đang được cải tạo.',
        openHours: 'Cả ngày',
        priceRange: 'Miễn phí',
        bestTime: 'Sáng 6:00–8:00 hoặc chiều 17:00–19:00',
        distance: '0km (trung tâm)',
        complaints: [
          { icon: '👥', text: 'Rất đông khách du lịch, khó chụp ảnh đẹp vào cuối tuần.', sources: [{ label: 'Google Maps', type: 'gm' }, { label: 'TikTok', type: 'tt' }] },
          { icon: '🗑', text: 'Vệ sinh khu vực một số điểm chưa tốt.', sources: [{ label: 'Facebook', type: 'fb' }] }
        ]
      },
      {
        id: 5,
        name: 'Vườn Dâu Tây La Oai',
        location: 'Xuân Thọ, Đà Lạt',
        type: 'Nông trại',
        riskLevel: 'low',
        score: 88,
        fbScore: 4.7,
        gmScore: 4.6,
        ttScore: 4.9,
        reviewCount: 445,
        color: '#e84393',
        activeUsers: 2,
        description: 'Vườn dâu tây hữu cơ cho phép tự hái, trải nghiệm nông nghiệp thực sự.',
        aiSummary: 'Trải nghiệm hái dâu được đánh giá chân thực và vui vẻ. Dâu ngọt, giá hợp lý. Thích hợp cho gia đình và trẻ em.',
        openHours: '07:00 – 17:00',
        priceRange: '80.000 – 150.000đ',
        bestTime: 'Buổi sáng 8:00–11:00',
        distance: '15km từ trung tâm',
        complaints: [
          { icon: '📅', text: 'Cần đặt trước vào mùa cao điểm tháng 12–2.', sources: [{ label: 'Facebook', type: 'fb' }] }
        ]
      },
      {
        id: 6,
        name: 'Chợ Đêm Đà Lạt',
        location: 'Trung tâm Đà Lạt',
        type: 'Ẩm thực',
        riskLevel: 'high',
        score: 58,
        fbScore: 3.8,
        gmScore: 3.6,
        ttScore: 4.1,
        reviewCount: 3200,
        color: '#DF6F3B',
        activeUsers: 12,
        description: 'Chợ đêm sầm uất với đặc sản địa phương, đồ lưu niệm và ẩm thực đường phố.',
        aiSummary: 'Nhiều phản ánh về giá cả không minh bạch và chất lượng không đồng đều. Nên thương lượng giá và chọn quán có menu rõ ràng.',
        openHours: '17:00 – 23:00',
        priceRange: '20.000 – 200.000đ',
        bestTime: 'Chiều 17:00–19:00 (trước khi đông)',
        distance: '0km (trung tâm)',
        complaints: [
          { icon: '💰', text: 'Giá "chặt chém" khách du lịch, cần hỏi giá trước khi mua.', sources: [{ label: 'Google Maps', type: 'gm' }, { label: 'Facebook', type: 'fb' }] },
          { icon: '🌊', text: 'Rất đông và chật chội, dễ mất đồ cá nhân.', sources: [{ label: 'TikTok', type: 'tt' }] }
        ]
      }
    ];
  }

  getCommunityPosts(): CommunityPost[] {
    return [
      { id: 1, place: 'Langbiang Summit Trail', time: '5 phút trước', type: 'question', author: 'Minh Trung', av: 'MT', rank: 3, answers: 4, questionsUsed: 2, txt: 'Hôm nay Langbiang có sương mù không? Mình dự định đi sáng mai lúc 6h.', likes: 12, dislikes: 0, gps: 1, verified: true },
      { id: 2, place: 'The Loft Coffee', time: '23 phút trước', type: 'review', author: 'Lan Anh', av: 'LA', rank: 5, answers: 0, questionsUsed: 3, txt: 'The Loft hôm nay còn 2 bàn trống tầng 2. Cà phê ngon như mọi khi, không gian yên tĩnh.', likes: 28, dislikes: 1, gps: 1, verified: true },
      { id: 3, place: 'Đồi Chè Cầu Đất', time: '1 giờ trước', type: 'tip', author: 'Hoàng Nam', av: 'HN', rank: 4, answers: 2, questionsUsed: 5, txt: 'Tips: Đến Cầu Đất trước 6:30 để có sương mù đẹp nhất. Mang áo ấm vì lạnh hơn trung tâm nhiều!', likes: 45, dislikes: 0, gps: 2, verified: true },
      { id: 4, place: 'Hồ Xuân Hương', time: '2 giờ trước', type: 'question', author: 'Thu Hà', av: 'TH', rank: 2, answers: 6, questionsUsed: 1, txt: 'Đường đi bộ quanh hồ có đang sửa chữa không? Mình nghe nói đang cải tạo?', likes: 8, dislikes: 0, gps: 0, verified: false },
      { id: 5, place: 'Chợ Đêm Đà Lạt', time: '3 giờ trước', type: 'review', author: 'Quang Huy', av: 'QH', rank: 1, answers: 0, questionsUsed: 0, txt: 'Chợ đêm tối nay đông kinh khủng. Giá bánh tráng nướng bị hét 50k/cái. Cẩn thận!', likes: 67, dislikes: 2, gps: 1, verified: false }
    ];
  }
}
