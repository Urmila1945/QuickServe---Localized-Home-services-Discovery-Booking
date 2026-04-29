import React from 'react';
import { Link } from 'react-router-dom';
import { Category } from '../../types';

interface CategoryCardProps {
  category: Category;
}

export default function CategoryCard({ category }: CategoryCardProps) {
  return (
    <Link
      to={`/services?category=${encodeURIComponent(category.name)}`}
      className="block group"
    >
      <div className="card-hover text-center p-6">
        <div className="text-4xl mb-3">{category.icon || '🔧'}</div>
        <h3 className="font-semibold text-gray-900 group-hover:text-primary-600 transition-colors mb-2">
          {category.name}
        </h3>
        {category.description && (
          <p className="text-sm text-gray-600 line-clamp-2">
            {category.description}
          </p>
        )}
      </div>
    </Link>
  );
}
