import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const useServices = (filters?: any) => {
  return useQuery({
    queryKey: ['services', filters],
    queryFn: async () => {
      const response = await axios.get(`${API_URL}/api/services/search`, { params: filters });
      return response.data;
    },
  });
};

export const useServiceCategories = () => {
  return useQuery({
    queryKey: ['categories'],
    queryFn: async () => {
      const response = await axios.get(`${API_URL}/api/services/categories`);
      return response.data;
    },
  });
};

export const useRecommendations = () => {
  return useQuery({
    queryKey: ['recommendations'],
    queryFn: async () => {
      const response = await axios.get(`${API_URL}/api/services/recommendations`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });
      return response.data;
    },
  });
};
