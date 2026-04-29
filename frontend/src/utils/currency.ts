// Currency conversion utility
// Data is already in INR, no conversion needed
export const USD_TO_INR = 1;

export const convertToRupees = (usdAmount: number): number => {
  return Math.round(usdAmount * USD_TO_INR);
};

export const formatCurrency = (amount: number, currency: 'INR' | 'USD' = 'INR'): string => {
  if (currency === 'INR') {
    return `₹${amount.toLocaleString('en-IN')}`;
  }
  return `$${amount}`;
};

export const formatPriceINR = (usdAmount: number): string => {
  const rupees = convertToRupees(usdAmount);
  return `₹${rupees.toLocaleString('en-IN')}`;
};

// For backward compatibility - replaces $ with ₹ and converts
export const convertPrice = (price: number | string): string => {
  const numPrice = typeof price === 'string' ? parseFloat(price) : price;
  if (isNaN(numPrice)) return price.toString();
  return formatPriceINR(numPrice);
};
