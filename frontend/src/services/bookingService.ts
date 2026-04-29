import api from './api';

export const bookingService = {
  createBooking: async (data: any) => {
    const response = await api.post('/api/bookings/', data);
    return response.data;
  },

  createEmergencyBooking: async (data: any) => {
    const response = await api.post('/api/bookings/emergency', data);
    return response.data;
  },

  getBookings: async () => {
    const response = await api.get('/api/bookings/');
    return response.data;
  },

  getBookingById: async (id: string) => {
    const response = await api.get(`/api/bookings/${id}`);
    return response.data;
  },

  updateBookingStatus: async (id: string, status: string) => {
    const response = await api.put(`/api/bookings/${id}/status`, null, { params: { status } });
    return response.data;
  },

  cancelBooking: async (id: string) => {
    const response = await api.delete(`/api/bookings/${id}`);
    return response.data;
  }
};
