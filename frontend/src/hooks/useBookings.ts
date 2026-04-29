import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { bookingService } from '../services/bookingService';
import toast from 'react-hot-toast';

export const useBookings = () => {
  return useQuery({ queryKey: ['bookings'], queryFn: bookingService.getBookings });
};

export const useCreateBooking = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: bookingService.createBooking,
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['bookings'] }); toast.success('Booking created!'); },
    onError: () => toast.error('Failed to create booking'),
  });
};

export const useEmergencyBooking = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: bookingService.createEmergencyBooking,
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['bookings'] }); toast.success('Emergency booking created!'); },
    onError: () => toast.error('Failed to create emergency booking'),
  });
};

export const useUpdateBookingStatus = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => bookingService.updateBookingStatus(id, status),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['bookings'] }); toast.success('Status updated'); },
    onError: () => toast.error('Failed to update status'),
  });
};
