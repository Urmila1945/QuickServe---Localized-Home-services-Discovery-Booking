export interface User {
  _id?: string;
  id?: string;
  email: string;
  full_name: string;
  name?: string;
  phone?: string;
  role: 'customer' | 'provider' | 'admin';
  location?: Location;
  profile_image?: string;
  is_verified?: boolean;
  rating?: number;
  created_at?: string;
  specializations?: string[];
  reviews_count?: number;
  experience_years?: number;
  current_location?: {
    latitude: number;
    longitude: number;
    last_updated: string;
  };
  provider_profile?: {
    base_rate: number;
    skills: string[];
    bio?: string;
    is_active: boolean;
  };
}

export interface Location {
  latitude: number;
  longitude: number;
  address: string;
}

export interface Service {
  _id: string;
  name?: string;
  title?: string;
  description: string;
  category: string;
  price?: number;
  price_per_hour?: number;
  duration?: number;
  provider_id: string;
  provider_name?: string;
  location?: Location;
  city?: string;
  latitude?: number;
  longitude?: number;
  images?: string[];
  availability?: string[];
  rating?: number;
  reviews_count?: number;
  is_emergency?: boolean;
  is_available?: boolean;
  distance?: number;
  created_at?: string;
}

export type ServiceCategory = 
  | 'plumbing' 
  | 'electrical' 
  | 'cleaning' 
  | 'tutoring' 
  | 'repair' 
  | 'beauty' 
  | 'fitness' 
  | 'delivery';

export interface Booking {
  _id: string;
  service_id: string;
  service_name?: string;
  user_id?: string;
  customer_id?: string;
  provider_id: string;
  provider_name?: string;
  scheduled_date?: string;
  scheduled_time?: string;
  status: BookingStatus;
  amount?: number;
  total_amount?: number;
  location?: Location | { latitude: number; longitude: number; address?: string };
  notes?: string;
  is_emergency?: boolean;
  service_title?: string;
  service_category?: string;
  created_at: string;
  updated_at?: string;
}

export type BookingStatus = 
  | 'pending' 
  | 'confirmed' 
  | 'in_progress' 
  | 'completed' 
  | 'cancelled';

export interface Review {
  _id: string;
  booking_id: string;
  customer_id: string;
  provider_id: string;
  rating: number;
  comment: string;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user_id: string;
}

export interface SearchFilters {
  category?: string;
  city?: string;
  location?: string;
  latitude?: number;
  longitude?: number;
  radius?: number;
  min_rating?: number;
  min_price?: number;
  max_price?: number;
  emergency?: boolean;
  q?: string;
}

export interface Message {
  _id: string;
  conversation_id: string;
  sender_id: string;
  message: string;
  message_type: 'text' | 'image' | 'file';
  timestamp: string;
  read: boolean;
}

export interface Conversation {
  _id: string;
  participants: string[];
  booking_id?: string;
  other_user?: {
    id: string;
    name: string;
    profile_image?: string;
  };
  last_message?: {
    text: string;
    timestamp: string;
  };
  unread_count?: Record<string, number>;
  created_at: string;
  last_message_at: string;
}

export interface LocationData {
  provider_id: string;
  latitude: number;
  longitude: number;
  accuracy?: number;
  speed?: number;
  timestamp: string;
}

export interface DashboardData {
  // Customer
  total_bookings?: number;
  active_bookings?: number;
  loyalty_points?: number;
  recent_bookings?: Booking[];
  
  // Provider
  completed_bookings?: number;
  pending_bookings?: number;
  average_rating?: number;
  total_earnings?: number;
  total_reviews?: number;
  
  // Admin
  total_users?: number;
  total_providers?: number;
  total_revenue?: number;
  today_bookings?: number;
  today_revenue?: number;
  active_services?: number;
  cancelled_bookings?: number;
  total_admins?: number;
  all_users?: User[];
  all_providers?: User[];
  recent_transactions?: any[];
}

export interface Category {
  name: string;
  description: string;
  icon: string;
}

export interface AIResponse {
  response: string;
  timestamp: string;
}

export interface DemandPrediction {
  category: string;
  date: string;
  predicted_demand: number;
  available_providers: number;
  availability_status: 'high' | 'medium' | 'low';
  recommendation: string;
}

export interface FakeReviewDetection {
  review_text: string;
  rating: number;
  authenticity_score: number;
  is_suspicious: boolean;
  suspicious_indicators: number;
  reasons: string[];
  verdict: string;
}

export interface LoyaltyData {
  points: number;
  tier: 'bronze' | 'silver' | 'gold' | 'platinum';
  discount: number;
}

export interface TimeSlot {
  start_time: string;
  end_time: string;
  is_available: boolean;
}

export interface SmartTimeSlot {
  time: string;
  price: number;
  weather: string;
  demand: 'low' | 'medium' | 'high';
  discount?: number;
}