import React from 'react';
import { LoadingProps } from '../../types';

export default function LoadingSpinner({ size = 'md', color = 'text-primary-600' }: LoadingProps) {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8',
    lg: 'w-12 h-12'
  };

  return (
    <div className="flex justify-center items-center">
      <div className={`animate-spin rounded-full border-2 border-gray-300 border-t-current ${sizeClasses[size]} ${color}`}></div>
    </div>
  );
}