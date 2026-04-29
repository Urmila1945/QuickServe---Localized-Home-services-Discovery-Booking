import api from './authService';
import { Service, SearchFilters, ServiceCategory } from '../types';

export const servicesService = {
  async searchServices(filters: SearchFilters & { 
    q?: string; 
    limit?: number; 
    skip?: number; 
  }): Promise<Service[]> {
    try {
      const params = new URLSearchParams();
      
      if (filters.q) params.append('q', filters.q);
      if (filters.category) params.append('category', filters.category);
      if ((filters as any).location?.lat) params.append('lat', (filters as any).location.lat.toString());
      if ((filters as any).location?.lng) params.append('lng', (filters as any).location.lng.toString());
      if (filters.radius) params.append('radius', filters.radius.toString());
      if (filters.min_price) params.append('price_min', filters.min_price.toString());
      if (filters.max_price) params.append('price_max', filters.max_price.toString());
      if (filters.min_rating) params.append('rating_min', filters.min_rating.toString());
      if ((filters as any).sort_by) params.append('sort_by', (filters as any).sort_by);
      if (filters.limit) params.append('limit', filters.limit.toString());
      if (filters.skip) params.append('skip', filters.skip.toString());

      const response = await api.get(`/services/search?${params.toString()}`);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to search services');
    }
  },

  async getService(id: string): Promise<Service> {
    try {
      const response = await api.get(`/services/${id}`);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to get service');
    }
  },

  async getRecommendations(location?: { lat: number; lng: number }, limit = 10): Promise<Service[]> {
    try {
      const params = new URLSearchParams();
      if (location?.lat) params.append('lat', location.lat.toString());
      if (location?.lng) params.append('lng', location.lng.toString());
      params.append('limit', limit.toString());

      const response = await api.get(`/services/recommendations?${params.toString()}`);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to get recommendations');
    }
  },

  async getCategories(): Promise<ServiceCategory[]> {
    try {
      const response = await api.get('/services/categories');
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to get categories');
    }
  },

  async createService(serviceData: any): Promise<Service> {
    try {
      const response = await api.post('/services/', serviceData);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to create service');
    }
  },

  async updateService(id: string, serviceData: any): Promise<Service> {
    try {
      const response = await api.put(`/services/${id}`, serviceData);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to update service');
    }
  },

  async deleteService(id: string): Promise<void> {
    try {
      await api.delete(`/services/${id}`);
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to delete service');
    }
  },

  async getSimilarServices(serviceId: string, limit = 5): Promise<Service[]> {
    try {
      const response = await api.get(`/services/${serviceId}/similar?limit=${limit}`);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to get similar services');
    }
  },
};