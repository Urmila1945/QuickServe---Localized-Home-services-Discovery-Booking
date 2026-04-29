import React from 'react';
import { Link } from 'react-router-dom';
import { ExclamationTriangleIcon } from '@heroicons/react/24/solid';

export default function EmergencyButton() {
  return (
    <Link
      to="/emergency"
      className="fixed bottom-6 right-6 z-50 bg-red-600 hover:bg-red-700 text-white p-4 rounded-full shadow-lg emergency-pulse transition-all duration-300 hover:scale-110"
      title="Emergency Booking"
    >
      <ExclamationTriangleIcon className="w-6 h-6" />
      <span className="sr-only">Emergency Booking</span>
    </Link>
  );
}