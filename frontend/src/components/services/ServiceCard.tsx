import React from 'react';
import { Link } from 'react-router-dom';
import { StarIcon, MapPinIcon, ClockIcon } from '@heroicons/react/24/solid';
import { Service } from '../../types';
import { formatPriceINR } from '../../utils/currency';
import ProviderBadge from '../verification/ProviderBadge';
import ProviderProfileModal from '../verification/ProviderProfileModal';
import { CheckCircle } from 'lucide-react';

interface ServiceCardProps {
  service: Service;
}

export default function ServiceCard({ service }: ServiceCardProps) {
  const [viewingProviderId, setViewingProviderId] = React.useState<string | null>(null);

  const serviceId = service._id || (service as any).id;
  const providerName = service.provider_name || 'Provider';
  const rating = service.rating ?? 0;
  const reviewsCount = service.reviews_count ?? 0;
  const duration = service.duration ?? 60;
  const images = service.images ?? [];
  const city = (service.location as any)?.city || service.city || '';
  const price = service.price ?? service.price_per_hour ?? 0;
  const serviceName = service.name || service.title || 'Service';

  const formatDuration = (minutes: number) => {
    if (minutes < 60) return `${minutes}m`;
    const hours = Math.floor(minutes / 60);
    const rem = minutes % 60;
    return rem > 0 ? `${hours}h ${rem}m` : `${hours}h`;
  };

  return (
    <Link to={`/services/${serviceId}`} className="block">
      <div className="card-hover group">
        {/* Service Image */}
        <div className="relative h-48 bg-gray-200 rounded-lg mb-4 overflow-hidden">
          {images.length > 0 ? (
            <img
              src={images[0]}
              alt={serviceName}
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            />
          ) : (
            <div className="w-full h-full bg-gradient-to-br from-teal-100 to-emerald-100 flex items-center justify-center">
              <span className="text-teal-600 font-semibold text-lg">{service.category}</span>
            </div>
          )}

          {service.distance && (
            <div className="absolute top-2 right-2 bg-white/90 backdrop-blur-sm px-2 py-1 rounded-full text-xs font-medium text-gray-700">
              {service.distance.toFixed(1)} km
            </div>
          )}
        </div>

        {/* Service Info */}
        <div className="space-y-3">
          <div>
            <h3 className="font-semibold text-lg text-gray-900 group-hover:text-teal-600 transition-colors">
              {serviceName}
            </h3>
            <p className="text-gray-600 text-sm line-clamp-2">{service.description}</p>
          </div>

          {/* Provider Info */}
          <div className="flex items-center space-x-2">
            <div
              className="flex items-center space-x-2 cursor-pointer hover:opacity-80 transition-all"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                if (service.provider_id) setViewingProviderId(service.provider_id);
              }}
            >
              <div className="w-8 h-8 bg-teal-50 border border-teal-100 rounded-full flex items-center justify-center">
                <span className="text-xs font-bold text-teal-600">{providerName.charAt(0)}</span>
              </div>
              <div className="flex flex-col">
                <span className="text-sm font-bold text-gray-700 leading-tight">{providerName}</span>
                <span className="text-[10px] font-black text-teal-600 uppercase flex items-center gap-0.5">
                  <CheckCircle size={10} className="fill-teal-50" /> Verified
                </span>
              </div>
            </div>
            {service.provider_id && (
              <ProviderBadge providerId={service.provider_id} variant="compact" />
            )}
          </div>

          {viewingProviderId && (
            <div onClick={e => e.preventDefault()}>
              <ProviderProfileModal
                providerId={viewingProviderId}
                onClose={() => setViewingProviderId(null)}
              />
            </div>
          )}

          {/* Rating */}
          <div className="flex items-center space-x-2">
            <div className="flex items-center">
              <StarIcon className="w-4 h-4 text-yellow-400" />
              <span className="text-sm font-medium text-gray-700 ml-1">{rating.toFixed(1)}</span>
            </div>
            <span className="text-sm text-gray-500">({reviewsCount} reviews)</span>
          </div>

          {/* Details */}
          <div className="flex items-center justify-between text-sm text-gray-600">
            <div className="flex items-center space-x-1">
              <ClockIcon className="w-4 h-4" />
              <span>{formatDuration(duration)}</span>
            </div>
            {city && (
              <div className="flex items-center space-x-1">
                <MapPinIcon className="w-4 h-4" />
                <span>{city}</span>
              </div>
            )}
          </div>

          {/* Price */}
          <div className="flex items-center justify-between">
            <span className="text-lg font-semibold text-teal-600">{formatPriceINR(price)}/hr</span>
            <span className="badge badge-primary">{service.category}</span>
          </div>
        </div>
      </div>
    </Link>
  );
}
