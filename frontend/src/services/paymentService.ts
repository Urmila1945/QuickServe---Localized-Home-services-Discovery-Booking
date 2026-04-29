import api from './api';

export const paymentService = {
  createPaymentIntent: async (
    bookingId: string,
    paymentMethod: string = 'card',
    applyWallet: boolean = false,
    couponCode?: string
  ) => {
    const response = await api.post('/api/payments/create-payment-intent', {
      booking_id: bookingId,
      payment_method: paymentMethod,
      apply_wallet: applyWallet,
      coupon_code: couponCode
    });
    return response.data;
  },

  confirmPayment: async (paymentId: string, paymentDetails?: any) => {
    const response = await api.post(`/api/payments/confirm-payment/${paymentId}`, {
      payment_details: paymentDetails
    });
    return response.data;
  },

  getPaymentHistory: async (status?: string, limit: number = 50) => {
    const params = new URLSearchParams();
    if (status) params.append('status', status);
    params.append('limit', limit.toString());
    
    const response = await api.get(`/api/payments/history?${params.toString()}`);
    return response.data;
  },

  getPaymentDetails: async (paymentId: string) => {
    const response = await api.get(`/api/payments/${paymentId}`);
    return response.data;
  },

  requestRefund: async (paymentId: string, reason: string, amount?: number) => {
    const response = await api.post(`/api/payments/refund/${paymentId}`, {
      reason,
      refund_amount: amount
    });
    return response.data;
  },

  releaseEscrow: async (bookingId: string, rating?: number, review?: string) => {
    const response = await api.post(`/api/payments/release-escrow/${bookingId}`, {
      rating,
      review
    });
    return response.data;
  },

  getAvailablePaymentMethods: async () => {
    const response = await api.get('/api/payments/methods/available');
    return response.data;
  },

  createSplitPayment: async (bookingId: string, splitWith: string[]) => {
    const response = await api.post('/api/payments/split-payment', {
      booking_id: bookingId,
      split_with: splitWith
    });
    return response.data;
  },

  topupWallet: async (amount: number, paymentMethod: string = 'upi') => {
    const response = await api.post('/api/payments/wallet/topup', {
      amount,
      payment_method: paymentMethod
    });
    return response.data;
  },

  getWalletBalance: async () => {
    const response = await api.get('/api/payments/wallet/balance');
    return response.data;
  },

  getPaymentAnalytics: async () => {
    const response = await api.get('/api/payments/analytics');
    return response.data;
  }
};
