import axios from 'axios';
import type {
  AuthResponse,
  User,
  Service,
  Booking,
  SearchFilters,
  Review,
  Message,
  Conversation,
  LocationData,
  DashboardData,
  Category,
  AIResponse,
  DemandPrediction,
  FakeReviewDetection,
  LoyaltyData,
  TimeSlot,
  SmartTimeSlot
} from '../types';

// IMPORTANT: Keep empty so Vite's /api proxy is used and CORS is avoided.
// Do NOT set VITE_API_URL to http://localhost:8000 — that bypasses the proxy.
const API_BASE_URL = import.meta.env.VITE_API_URL || '';


const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  timeout: 30000,
});

// Request interceptor to add token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle token storage
api.interceptors.response.use(
  (response) => {
    // Store token if present in response
    if (response.data?.access_token) {
      localStorage.setItem('token', response.data.access_token);
    }
    return response;
  },
  (error) => {
    // Clear token on 401
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  register: async (userData: any): Promise<AuthResponse> => {
    const response = await api.post('/api/auth/register', userData);
    return response.data;
  },

  login: async (email: string, password: string): Promise<AuthResponse> => {
    const response = await api.post('/api/auth/login', { email, password });
    return response.data;
  },

  googleLogin: async (credential: string): Promise<AuthResponse> => {
    const response = await api.post('/api/auth/google', { credential });
    return response.data;
  },

  getMe: async (): Promise<User> => {
    const response = await api.get('/api/auth/me');
    return response.data;
  },

  logout: async () => {
    await api.post('/api/auth/logout');
  }
};

// Services API
export const servicesAPI = {
  search: async (filters: SearchFilters): Promise<{ services: Service[]; total: number }> => {
    const response = await api.get('/api/services/search', { params: filters });
    return response.data;
  },

  getCategories: async (): Promise<Category[]> => {
    const response = await api.get('/api/services/categories');
    return response.data;
  },

  getCities: async (): Promise<any[]> => {
    const response = await api.get('/api/services/cities');
    return response.data;
  },

  getById: async (id: string): Promise<Service> => {
    const response = await api.get(`/api/services/${id}`);
    return response.data;
  },

  getRecommendations: async (latitude?: number, longitude?: number): Promise<Service[]> => {
    const params: any = {};
    if (latitude != null) params.latitude = latitude;
    if (longitude != null) params.longitude = longitude;
    const response = await api.get('/api/services/recommendations', { params });
    const data = response.data;
    // Backend now always returns {recommendations:[], total:N}
    return Array.isArray(data) ? data : (data?.recommendations || []);
  },

  voiceHail: async (text: string): Promise<{ service: string; urgency: string; original_text: string }> => {
    const response = await api.post('/api/services/voice-hail', { text });
    return response.data;
  },

  getEmergency: async (category: string, latitude: number, longitude: number): Promise<Service[]> => {
    const response = await api.get('/api/services/emergency', {
      params: { category, latitude, longitude }
    });
    return response.data;
  },

  create: async (serviceData: Partial<Service>): Promise<Service> => {
    const response = await api.post('/api/services/', serviceData);
    return response.data;
  },
};

// Bookings API
export const bookingsAPI = {
  create: async (bookingData: Partial<Booking>): Promise<any> => {
    const response = await api.post('/api/bookings/', bookingData);
    return response.data;
  },

  createEmergency: async (serviceId: string, location: any, notes: string = ''): Promise<Booking> => {
    const response = await api.post('/api/bookings/emergency', {
      service_id: serviceId,
      location,
      notes
    });
    return response.data;
  },

  getUserBookings: async (): Promise<Booking[]> => {
    const response = await api.get('/api/bookings/');
    return Array.isArray(response.data) ? response.data : (response.data?.bookings || []);
  },

  updateStatus: async (bookingId: string, status: string): Promise<Booking> => {
    const response = await api.put(`/api/bookings/${bookingId}/status`, null, { params: { status } });
    return response.data;
  },

  getDetails: async (bookingId: string): Promise<Booking> => {
    const response = await api.get(`/api/bookings/${bookingId}`);
    return response.data;
  },
};

// Slots API
export const slotsAPI = {
  getAvailability: async (providerId: string, date: string): Promise<TimeSlot[]> => {
    const response = await api.get(`/api/slots/availability/${providerId}`, {
      params: { date }
    });
    return response.data;
  },

  bookSlot: async (providerId: string, date: string, startTime: string, serviceId: string): Promise<any> => {
    const response = await api.post('/api/slots/book', {
      provider_id: providerId,
      date,
      start_time: startTime,
      service_id: serviceId
    });
    return response.data;
  },

  getMyBookings: async (): Promise<any[]> => {
    const response = await api.get('/api/slots/my-bookings');
    return response.data;
  },

  getSmartScheduling: async (date: string): Promise<{ date: string; slots: SmartTimeSlot[] }> => {
    const response = await api.get('/api/slots/smart-scheduling', {
      params: { date }
    });
    return response.data;
  },
};

// Reviews API
export const reviewsAPI = {
  create: async (reviewData: Partial<Review>): Promise<Review> => {
    const response = await api.post('/api/reviews/', reviewData);
    return response.data;
  },

  getByService: async (serviceId: string): Promise<Review[]> => {
    const response = await api.get(`/api/reviews/service/${serviceId}`);
    return response.data;
  },

  getByProvider: async (providerId: string): Promise<{ reviews: Review[]; average_rating: number; total: number }> => {
    const response = await api.get(`/api/reviews/provider/${providerId}`);
    return response.data;
  },

  markHelpful: async (reviewId: string): Promise<void> => {
    await api.post(`/api/reviews/${reviewId}/helpful`);
  },

  delete: async (reviewId: string): Promise<void> => {
    await api.delete(`/api/reviews/${reviewId}`);
  },
};

// Chat API
export const chatAPI = {
  createConversation: async (participantId: string, bookingId?: string): Promise<Conversation> => {
    const response = await api.post('/api/chat/conversations', {
      participant_id: participantId,
      booking_id: bookingId
    });
    return response.data;
  },

  getConversations: async (): Promise<Conversation[]> => {
    const response = await api.get('/api/chat/conversations');
    return response.data;
  },

  sendMessage: async (conversationId: string, message: string): Promise<Message> => {
    const response = await api.post('/api/chat/messages', {
      conversation_id: conversationId,
      message
    });
    return response.data;
  },

  getMessages: async (conversationId: string): Promise<Message[]> => {
    const response = await api.get(`/api/chat/messages/${conversationId}`);
    return response.data;
  },

  getUnreadCount: async (): Promise<{ unread_count: number }> => {
    const response = await api.get('/api/chat/unread-count');
    return response.data;
  },

  getQuickReplies: async (): Promise<{ quick_replies: string[] }> => {
    const response = await api.get('/api/chat/quick-replies');
    return response.data;
  },

  searchConversations: async (query: string): Promise<{ results: Message[]; count: number }> => {
    const response = await api.get('/api/chat/search', { params: { query } });
    return response.data;
  },
};

// Tracking API
export const trackingAPI = {
  updateLocation: async (latitude: number, longitude: number, accuracy?: number, speed?: number): Promise<void> => {
    await api.post('/api/tracking/update-location', {
      latitude,
      longitude,
      accuracy,
      speed
    });
  },

  getLocation: async (bookingId: string): Promise<LocationData> => {
    const response = await api.get(`/api/tracking/location/${bookingId}`);
    return response.data;
  },

  getNearbyProviders: async (latitude: number, longitude: number, serviceType?: string, radiusKm: number = 5): Promise<any> => {
    const response = await api.get('/api/tracking/nearby-providers', {
      params: { latitude, longitude, service_type: serviceType, radius_km: radiusKm }
    });
    return response.data;
  },
};

// Dashboard API
export const dashboardAPI = {
  getCustomer: async (): Promise<DashboardData> => {
    const response = await api.get('/api/dashboard/customer');
    return response.data;
  },

  getFavourites: async (): Promise<any> => {
    try {
      const response = await api.get('/api/dashboard/customer/favourites');
      return response.data;
    } catch {
      return { favourites: [] };
    }
  },

  getBlockParties: async (): Promise<any> => {
    try {
      const response = await api.get('/api/dashboard/customer/block-parties');
      return response.data;
    } catch {
      return { block_parties: [] };
    }
  },

  getQuotes: async (): Promise<any> => {
    try {
      const response = await api.get('/api/dashboard/customer/quotes');
      return response.data;
    } catch {
      return { quotes: [] };
    }
  },

  getMaintenance: async (): Promise<any> => {
    try {
      const response = await api.get('/api/dashboard/customer/maintenance');
      return response.data;
    } catch {
      return { items: [] };
    }
  },

  getProvider: async (): Promise<DashboardData> => {
    const response = await api.get('/api/dashboard/provider');
    return response.data;
  },

  getAdmin: async (): Promise<DashboardData> => {
    const response = await api.get('/api/dashboard/admin');
    return response.data;
  },
};

export const providerAPI = {
  getActiveJob: async (): Promise<any> => {
    const response = await api.get('/api/provider/active-job');
    return response.data;
  },
  getRouteDensity: async (date: string): Promise<any> => {
    const response = await api.get('/api/provider/route-density', { params: { date } });
    return response.data;
  },
  getSurgePricing: async (): Promise<any> => {
    const response = await api.get('/api/provider/surge-pricing');
    return response.data;
  },
  getSkillGapAlerts: async (): Promise<any> => {
    const response = await api.get('/api/provider/skill-gap-alerts');
    return response.data;
  },
};

// AI Features API
export const aiAPI = {
  chatbot: async (message: string): Promise<AIResponse> => {
    const response = await api.post('/api/ai/chatbot', null, {
      params: { message }
    });
    return response.data;
  },

  analyzeARFrame: async (imageBase64: string): Promise<{ issue: string; estCost: number; service: string }> => {
    const response = await api.post('/api/ai/analyze-ar-frame', { image_base64: imageBase64 });
    return response.data;
  },


  voiceSearch: async (transcript: string, location?: { latitude: number; longitude: number }): Promise<any> => {
    const response = await api.post('/api/ai/voice-search', {
      transcript,
      location
    });
    return response.data;
  },

  getRecommendations: async (): Promise<{ recommendations: Service[]; based_on: string }> => {
    const response = await api.get('/api/ai/recommendations');
    return response.data;
  },

  predictDemand: async (category: string, date?: string): Promise<DemandPrediction> => {
    const response = await api.get('/api/ai/demand-prediction', {
      params: { category, date }
    });
    return response.data;
  },

  detectFakeReview: async (reviewText: string, rating: number): Promise<FakeReviewDetection> => {
    const response = await api.post('/api/ai/detect-fake-review', {
      review_text: reviewText,
      rating
    });
    return response.data;
  },

  smartMatch: async (serviceType: string, location: { latitude: number; longitude: number }, urgency: string = 'normal'): Promise<any> => {
    const response = await api.post('/api/ai/smart-match', {
      service_type: serviceType,
      location,
      urgency
    });
    return response.data;
  },

  getAnalytics: async (): Promise<any> => {
    const response = await api.get('/api/ai/analytics');
    return response.data;
  },
};

// Loyalty API
export const loyaltyAPI = {
  getPoints: async (): Promise<LoyaltyData> => {
    const response = await api.get('/api/loyalty/points');
    return response.data;
  },

  earnPoints: async (bookingId: string): Promise<any> => {
    const response = await api.post('/api/loyalty/earn', {
      booking_id: bookingId
    });
    return response.data;
  },

  redeemPoints: async (points: number): Promise<any> => {
    const response = await api.post('/api/loyalty/redeem', { points });
    return response.data;
  },

  generateReferral: async (): Promise<{ referral_code: string }> => {
    const response = await api.post('/api/loyalty/referral/generate');
    return response.data;
  },

  applyReferral: async (code: string): Promise<any> => {
    const response = await api.post(`/api/loyalty/referral/apply/${code}`);
    return response.data;
  },
};

// Payments API
export const paymentsAPI = {
  createIntent: async (
    bookingId: string,
    paymentMethod: string = 'card',
    applyWallet: boolean = false,
    couponCode?: string
  ): Promise<any> => {
    const response = await api.post('/api/payments/create-payment-intent', {
      booking_id: bookingId,
      payment_method: paymentMethod,
      apply_wallet: applyWallet,
      coupon_code: couponCode,
    });
    return response.data;
  },

  confirmPayment: async (paymentId: string, paymentDetails?: any): Promise<any> => {
    const response = await api.post(`/api/payments/confirm-payment/${paymentId}`, {
      payment_details: paymentDetails,
    });
    return response.data;
  },

  getPaymentHistory: async (status?: string, limit: number = 50): Promise<any> => {
    const response = await api.get('/api/payments/history', { params: { status, limit } });
    return response.data;
  },

  requestRefund: async (paymentId: string, reason: string, refundAmount?: number): Promise<any> => {
    const response = await api.post(`/api/payments/refund/${paymentId}`, {
      reason,
      refund_amount: refundAmount,
    });
    return response.data;
  },

  releaseEscrow: async (bookingId: string, rating?: number, review?: string): Promise<any> => {
    const response = await api.post(`/api/payments/release-escrow/${bookingId}`, { rating, review });
    return response.data;
  },

  getAvailablePaymentMethods: async (): Promise<any> => {
    const response = await api.get('/api/payments/methods/available');
    return response.data;
  },

  topupWallet: async (amount: number, paymentMethod: string = 'upi'): Promise<any> => {
    const response = await api.post('/api/payments/wallet/topup', { amount, payment_method: paymentMethod });
    return response.data;
  },

  getWalletBalance: async (): Promise<any> => {
    const response = await api.get('/api/payments/wallet/balance');
    return response.data;
  },
};

// Queue API
export const queueAPI = {
  join: async (data: any): Promise<any> => {
    const res = await api.post('/api/queue/join', data);
    return res.data;
  },
  getStatus: async (queueId: string): Promise<any> => {
    const res = await api.get(`/api/queue/status/${queueId}`);
    return res.data;
  },
  skip: async (queueId: string, data: any): Promise<any> => {
    const res = await api.post(`/api/queue/skip/${queueId}`, data);
    return res.data;
  }
};

// Surge API
export const surgeAPI = {
  calculate: async (data: any): Promise<any> => {
    const res = await api.post('/api/surge/calculate', data);
    return res.data;
  },
  getPredictions: async (): Promise<any> => {
    const res = await api.get('/api/surge/predictions');
    return res.data;
  },
  notifyPriceDrop: async (data: any): Promise<any> => {
    const res = await api.post('/api/surge/notify-price-drop', data);
    return res.data;
  }
};

// Gamification API
export const gamificationAPI = {
  getProfile: async (): Promise<any> => {
    const res = await api.get('/api/gamification/profile');
    return res.data;
  },
  getChallenges: async (): Promise<any> => {
    const res = await api.get('/api/gamification/challenges');
    return res.data;
  },
  dailySpin: async (): Promise<any> => {
    const res = await api.post('/api/gamification/daily-spin');
    return res.data;
  },
  getLeaderboard: async (): Promise<any> => {
    const res = await api.get('/api/gamification/leaderboard');
    return res.data;
  },
  updateProgress: async (data: any): Promise<any> => {
    const res = await api.post('/api/gamification/update-progress', data);
    return res.data;
  }
};

// Predictive Maintenance API
export const predictiveAPI = {
  getPredictions: async (): Promise<any> => {
    const res = await api.get('/api/predictive/predictions');
    return res.data;
  },
  getHealthScore: async (): Promise<any> => {
    const res = await api.get('/api/predictive/health-score');
    return res.data;
  },
  smartSchedule: async (data: any): Promise<any> => {
    const res = await api.post('/api/predictive/smart-schedule', data);
    return res.data;
  },
  getCalendar: async (): Promise<any> => {
    const res = await api.get('/api/predictive/get-calendar');
    return res.data;
  },
  setReminder: async (data: any): Promise<any> => {
    const res = await api.post('/api/predictive/set-reminder', data);
    return res.data;
  }
};

// Mood Sync API
export const moodSyncAPI = {
  updateMood: async (data: any): Promise<any> => {
    const res = await api.post('/api/mood-sync/update-mood', data);
    return res.data;
  },
  findByMood: async (params: any): Promise<any> => {
    const res = await api.get('/api/mood-sync/find-by-mood', { params });
    return res.data;
  },
  moodBasedPricing: async (data: any): Promise<any> => {
    const res = await api.post('/api/mood-sync/mood-based-pricing', data);
    return res.data;
  },
  getDashboard: async (): Promise<any> => {
    const res = await api.get('/api/mood-sync/mood-dashboard');
    return res.data;
  },
  getInsights: async (): Promise<any> => {
    const res = await api.get('/api/mood-sync/mood-insights');
    return res.data;
  }
};

// Community API
export const communityAPI = {
  getActiveChallenges: async (): Promise<any> => {
    const res = await api.get('/api/community/active-challenges');
    return res.data;
  },
  neighborhoodBattle: async (data: any): Promise<any> => {
    const res = await api.post('/api/community/neighborhood-battle', data);
    return res.data;
  },
  getNeighborhoodStats: async (neighborhood: string): Promise<any> => {
    const res = await api.get('/api/community/neighborhood-stats', { 
      params: { neighborhood } 
    });
    return res.data;
  },
  getTopProviders: async (neighborhood: string): Promise<any[]> => {
    const res = await api.get('/api/community/top-providers', {
      params: { neighborhood }
    });
    return res.data;
  }
};

// Bundles API
export const bundlesAPI = {
  getRecommendations: async (): Promise<any> => {
    const res = await api.get('/api/bundles/recommendations');
    return res.data;
  },
  createCustom: async (data: any): Promise<any> => {
    const res = await api.post('/api/bundles/create-custom', data);
    return res.data;
  },
  optimize: async (data: any): Promise<any> => {
    const res = await api.post('/api/bundles/optimize', data);
    return res.data;
  }
};

// Events API
export const eventsAPI = {
  getUpcoming: async (): Promise<any> => {
    const res = await api.get('/api/events/upcoming');
    return res.data;
  },
  bid: async (eventId: string, data: any): Promise<any> => {
    const res = await api.post(`/api/events/bid/${eventId}`, data);
    return res.data;
  },
  showcase: async (eventId: string): Promise<any> => {
    const res = await api.post(`/api/events/showcase/${eventId}`);
    return res.data;
  }
};

// Swap API
export const swapAPI = {
  createOffer: async (data: any): Promise<any> => {
    const res = await api.post('/api/swap/create-offer', data);
    return res.data;
  },
  browse: async (): Promise<any> => {
    const res = await api.get('/api/swap/browse');
    return res.data;
  },
  requestSwap: async (offerId: string, data: any): Promise<any> => {
    const res = await api.post(`/api/swap/request-swap/${offerId}`, data);
    return res.data;
  }
};

// AR Preview API
export const arPreviewAPI = {
  uploadSpace: async (formData: FormData): Promise<any> => {
    const res = await api.post('/api/ar-preview/upload-space', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return res.data;
  },
  generatePreview: async (data: any): Promise<any> => {
    const res = await api.post('/api/ar-preview/generate-preview', data);
    return res.data;
  },
  bookFromPreview: async (previewId: string, data: any): Promise<any> => {
    const res = await api.post(`/api/ar-preview/book-from-preview/${previewId}`, data);
    return res.data;
  }
};

// Roulette API
export const rouletteAPI = {
  spin: async (data: any): Promise<any> => {
    const res = await api.post('/api/roulette/spin', data);
    return res.data;
  },
  getMysteryBox: async (): Promise<any> => {
    const res = await api.get('/api/roulette/mystery-box');
    return res.data;
  },
  getSurpriseRecommendations: async (): Promise<any> => {
    const res = await api.get('/api/roulette/surprise-recommendations');
    return res.data;
  }
};

// AI Concierge API
export const aiConciergeAPI = {
  chat: async (data: any): Promise<any> => {
    const res = await api.post('/api/ai-concierge/chat', data);
    return res.data;
  },
  getProactiveSuggestions: async (): Promise<any> => {
    const res = await api.get('/api/ai-concierge/proactive-suggestions');
    return res.data;
  },
  scheduleCoordination: async (data: any): Promise<any> => {
    const res = await api.post('/api/ai-concierge/schedule-coordination', data);
    return res.data;
  }
};

// Work Verification API
export const workVerificationAPI = {
  submitEvidence: async (formData: FormData): Promise<any> => {
    const res = await api.post('/api/work-verification/verify-work', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },
  checkin: async (bookingId: string, latitude: number, longitude: number): Promise<any> => {
    const fd = new FormData();
    fd.append('booking_id', bookingId);
    fd.append('latitude', String(latitude));
    fd.append('longitude', String(longitude));
    const res = await api.post('/api/work-verification/checkin', fd);
    return res.data;
  },
  getTrustScore: async (providerId: string): Promise<any> => {
    const res = await api.get(`/api/work-verification/trust-score/${providerId}`);
    return res.data;
  },
  getGallery: async (providerId: string): Promise<any> => {
    const res = await api.get(`/api/work-verification/gallery/${providerId}`);
    return res.data;
  },
  getBadge: async (providerId: string): Promise<any> => {
    const res = await api.get(`/api/work-verification/badge/${providerId}`);
    return res.data;
  },
};

// Receipt API
export const receiptAPI = {
  generate: (transactionId: string) => {
    const token = localStorage.getItem('token');
    // Use window.location.origin so the Vite proxy handles /api/* → backend
    const base = import.meta.env.VITE_API_URL || window.location.origin;
    return `${base}/api/payments/generate-receipt/${transactionId}${token ? `?token=${token}` : ''}`;
  },
  getBookingReceipt: (bookingId: string) => {
    const token = localStorage.getItem('token');
    const base = import.meta.env.VITE_API_URL || window.location.origin;
    return `${base}/api/payments/receipt/${bookingId}${token ? `?token=${token}` : ''}`;
  },
  verify: async (hash: string): Promise<any> => {
    const res = await api.get(`/api/payments/verify/receipt/${hash}`);
    return res.data;
  },
  demoTransaction: async (serviceName: string, amount: number, method = 'upi'): Promise<any> => {
    const res = await api.post('/api/payments/demo-transaction', {
      service_name: serviceName, amount, payment_method: method,
    });
    return res.data;
  },
};

export const aptitudeAPI = {
  getQuestions: async (category: string): Promise<any> => {
    const response = await api.get(`/api/aptitude/questions/${category}`);
    return response.data;
  },
};

export const notificationsAPI = {
  getNotifications: async (): Promise<any[]> => {
    const response = await api.get('/api/notifications/');
    return response.data;
  },
  markAsRead: async (id: string): Promise<any> => {
    const response = await api.put(`/api/notifications/${id}/read`);
    return response.data;
  },
  markAllAsRead: async (): Promise<any> => {
    const response = await api.put('/api/notifications/read-all');
    return response.data;
  },
  deleteNotification: async (id: string): Promise<any> => {
    const response = await api.delete(`/api/notifications/${id}`);
    return response.data;
  },
};

export default api;
