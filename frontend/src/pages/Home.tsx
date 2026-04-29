import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Star } from 'lucide-react';
import EnhancedSearchBar from '../components/ui/EnhancedSearchBar';
import { LocationData } from '../utils/locationService';

const Home: React.FC = () => {
  const navigate = useNavigate();

  const handleSearch = (query: string, location?: LocationData) => {
    const params = new URLSearchParams();
    if (query) params.append('q', query);
    if (location?.latitude) params.append('latitude', location.latitude.toString());
    if (location?.longitude) params.append('longitude', location.longitude.toString());
    navigate(`/services?${params.toString()}`);
  };

  const categories = [
    { 
      name: 'Plumbing', 
      icon: '🔧', 
      color: 'bg-blue-100 text-blue-800',
      image: 'https://images.unsplash.com/photo-1581578731548-c64695cc6952?w=300&h=200&fit=crop'
    },
    { 
      name: 'Electrical', 
      icon: '⚡', 
      color: 'bg-yellow-100 text-yellow-800',
      image: 'https://images.unsplash.com/photo-1621905251189-08b45d6a269e?w=300&h=200&fit=crop'
    },
    { 
      name: 'Cleaning', 
      icon: '🧹', 
      color: 'bg-green-100 text-green-800',
      image: 'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=300&h=200&fit=crop'
    },
    { 
      name: 'Tutoring', 
      icon: '📚', 
      color: 'bg-purple-100 text-purple-800',
      image: 'https://images.unsplash.com/photo-1522202176988-66273c2fd55f?w=300&h=200&fit=crop'
    },
    { 
      name: 'Repair', 
      icon: '🔨', 
      color: 'bg-red-100 text-red-800',
      image: 'https://images.unsplash.com/photo-1504148455328-c376907d081c?w=300&h=200&fit=crop'
    },
    { 
      name: 'Beauty', 
      icon: '💄', 
      color: 'bg-pink-100 text-pink-800',
      image: 'https://images.unsplash.com/photo-1560066984-138dadb4c035?w=300&h=200&fit=crop'
    },
    { 
      name: 'Fitness', 
      icon: '💪', 
      color: 'bg-orange-100 text-orange-800',
      image: 'https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=300&h=200&fit=crop'
    },
    { 
      name: 'Delivery', 
      icon: '📦', 
      color: 'bg-indigo-100 text-indigo-800',
      image: 'https://images.unsplash.com/photo-1566576912321-d58ddd7a6088?w=300&h=200&fit=crop'
    },
  ];

  const features = [
    {
      title: 'AI-Powered Matching',
      description: 'Smart algorithms find the perfect service provider for your needs',
      icon: '🤖',
      image: 'https://images.unsplash.com/photo-1677442136019-21780ecad995?w=400&h=300&fit=crop'
    },
    {
      title: 'Real-time Tracking',
      description: 'Track your service provider in real-time with live updates',
      icon: '📍',
      image: 'https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=400&h=300&fit=crop'
    },
    {
      title: 'Secure Payments',
      description: 'Safe and secure payment processing with multiple options',
      icon: '💳',
      image: 'https://images.unsplash.com/photo-1563013544-824ae1b704d3?w=400&h=300&fit=crop'
    },
    {
      title: 'Verified Providers',
      description: 'All service providers are background-checked and verified',
      icon: '✅',
      image: 'https://images.unsplash.com/photo-1600880292203-757bb62b4baf?w=400&h=300&fit=crop'
    },
  ];

  const testimonials = [
    {
      name: 'Sarah Johnson',
      role: 'Homeowner',
      image: 'https://images.unsplash.com/photo-1494790108755-2616b612b786?w=100&h=100&fit=crop&crop=face',
      text: 'QuickServe helped me find an amazing plumber in minutes! The AI recommendations were spot-on.',
      rating: 5
    },
    {
      name: 'Mike Chen',
      role: 'Business Owner',
      image: 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=100&h=100&fit=crop&crop=face',
      text: 'As a service provider, QuickServe has transformed my business. More bookings, better customers!',
      rating: 5
    },
    {
      name: 'Emily Davis',
      role: 'Busy Parent',
      image: 'https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=100&h=100&fit=crop&crop=face',
      text: 'The emergency service feature saved my day when my washing machine broke. Highly recommended!',
      rating: 5
    }
  ];

  return (
    <div className="min-h-screen">
      {/* Hero Section with Background Image */}
      <div className="relative bg-gradient-to-r from-primary-600 to-primary-800 text-white overflow-hidden">
        <div className="absolute inset-0 bg-black opacity-20"></div>
        <div 
          className="absolute inset-0 bg-cover bg-center"
          style={{
            backgroundImage: 'url(https://images.unsplash.com/photo-1521791136064-7986c2920216?w=1920&h=1080&fit=crop)',
            opacity: 0.3
          }}
        ></div>
        <div className="relative max-w-7xl mx-auto px-4 py-24">
          <div className="text-center">
            <h1 className="text-6xl font-bold mb-6 animate-fade-in">
              Find Local Services
              <span className="block text-primary-200 mt-2">Instantly</span>
            </h1>
            <p className="text-xl mb-8 max-w-2xl mx-auto animate-slide-up">
              Discover, book, and track local service providers with AI-powered recommendations
              and real-time updates. Your trusted partner for all local services.
            </p>
            
            {/* Enhanced Search Bar with Voice and Location */}
            <div className="max-w-2xl mx-auto mb-8 animate-slide-up">
              <EnhancedSearchBar
                onSearch={handleSearch}
                placeholder="What service do you need? (e.g., plumber, cleaner, tutor)"
                className="w-full"
              />
            </div>

            <div className="flex flex-col sm:flex-row gap-4 justify-center animate-slide-up">
              <Link
                to="/services"
                className="bg-white text-primary-600 px-8 py-4 rounded-full font-semibold hover:bg-gray-100 transition-all duration-300 hover:scale-105 shadow-lg"
              >
                🔍 Browse Services
              </Link>
              <Link
                to="/emergency"
                className="bg-red-500 hover:bg-red-600 text-white px-8 py-4 rounded-full font-semibold transition-all duration-300 hover:scale-105 shadow-lg animate-pulse"
              >
                🚨 Emergency Service
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Categories Section with Images */}
      <div className="py-20 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4">
          <h2 className="text-4xl font-bold text-center mb-4">Popular Categories</h2>
          <p className="text-xl text-gray-600 text-center mb-12">Choose from our wide range of professional services</p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {categories.map((category) => (
              <Link
                key={category.name}
                to={`/services?category=${category.name.toLowerCase()}`}
                className="group relative overflow-hidden rounded-2xl shadow-lg hover:shadow-2xl transition-all duration-300 hover:scale-105"
              >
                <div className="aspect-w-16 aspect-h-12">
                  <img 
                    src={category.image} 
                    alt={category.name}
                    className="w-full h-48 object-cover group-hover:scale-110 transition-transform duration-300"
                  />
                </div>
                <div className="absolute inset-0 bg-gradient-to-t from-black/70 to-transparent"></div>
                <div className="absolute bottom-0 left-0 right-0 p-6 text-white">
                  <div className="text-3xl mb-2">{category.icon}</div>
                  <h3 className="font-bold text-lg">{category.name}</h3>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </div>

      {/* Features Section with Images */}
      <div className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4">
          <h2 className="text-4xl font-bold text-center mb-4">Why Choose QuickServe?</h2>
          <p className="text-xl text-gray-600 text-center mb-16">Experience the future of local service booking</p>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            {features.map((feature, index) => (
              <div key={feature.title} className="group text-center hover:scale-105 transition-all duration-300">
                <div className="relative overflow-hidden rounded-2xl shadow-lg mb-6">
                  <img 
                    src={feature.image} 
                    alt={feature.title}
                    className="w-full h-48 object-cover group-hover:scale-110 transition-transform duration-300"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-primary-600/80 to-transparent"></div>
                  <div className="absolute bottom-4 left-4 text-white">
                    <div className="text-4xl mb-2">{feature.icon}</div>
                  </div>
                </div>
                <h3 className="text-xl font-semibold mb-3 text-gray-900">{feature.title}</h3>
                <p className="text-gray-600">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Testimonials Section */}
      <div className="py-20 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4">
          <h2 className="text-4xl font-bold text-center mb-4">What Our Users Say</h2>
          <p className="text-xl text-gray-600 text-center mb-16">Join thousands of satisfied customers</p>
          <div className="grid md:grid-cols-3 gap-8">
            {testimonials.map((testimonial, index) => (
              <div key={index} className="bg-white rounded-2xl shadow-lg p-8 hover:shadow-2xl transition-all duration-300">
                <div className="flex items-center mb-6">
                  <img 
                    src={testimonial.image} 
                    alt={testimonial.name}
                    className="w-16 h-16 rounded-full object-cover mr-4"
                  />
                  <div>
                    <h4 className="font-semibold text-gray-900">{testimonial.name}</h4>
                    <p className="text-gray-600 text-sm">{testimonial.role}</p>
                  </div>
                </div>
                <div className="flex mb-4">
                  {[...Array(testimonial.rating)].map((_, i) => (
                    <Star key={i} className="h-5 w-5 text-yellow-400 fill-yellow-400" />
                  ))}
                </div>
                <p className="text-gray-700 italic">"{testimonial.text}"</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Stats Section with Background */}
      <div className="py-20 bg-gradient-to-r from-primary-600 to-primary-800 text-white relative overflow-hidden">
        <div 
          className="absolute inset-0 bg-cover bg-center opacity-20"
          style={{
            backgroundImage: 'url(https://images.unsplash.com/photo-1557804506-669a67965ba0?w=1920&h=600&fit=crop)'
          }}
        ></div>
        <div className="relative max-w-7xl mx-auto px-4">
          <div className="grid md:grid-cols-4 gap-8 text-center">
            <div className="animate-fade-in">
              <div className="text-5xl font-bold mb-2">10,000+</div>
              <div className="text-primary-200 text-lg">Verified Providers</div>
            </div>
            <div className="animate-fade-in">
              <div className="text-5xl font-bold mb-2">50,000+</div>
              <div className="text-primary-200 text-lg">Happy Customers</div>
            </div>
            <div className="animate-fade-in">
              <div className="text-5xl font-bold mb-2">4.9★</div>
              <div className="text-primary-200 text-lg">Average Rating</div>
            </div>
            <div className="animate-fade-in">
              <div className="text-5xl font-bold mb-2">24/7</div>
              <div className="text-primary-200 text-lg">Support Available</div>
            </div>
          </div>
        </div>
      </div>

      {/* CTA Section */}
      <div className="py-20 bg-white">
        <div className="max-w-4xl mx-auto text-center px-4">
          <div className="mb-8">
            <img 
              src="https://images.unsplash.com/photo-1600880292089-90a7e086ee0c?w=600&h=400&fit=crop"
              alt="Get Started"
              className="w-full max-w-md mx-auto rounded-2xl shadow-2xl"
            />
          </div>
          <h2 className="text-4xl font-bold mb-6">Ready to Get Started?</h2>
          <p className="text-xl text-gray-600 mb-8">
            Join thousands of satisfied customers who trust QuickServe for their local service needs.
          </p>
          <Link
            to="/register"
            className="bg-primary-500 hover:bg-primary-600 text-white px-10 py-4 rounded-full text-lg font-semibold transition-all duration-300 hover:scale-105 shadow-lg inline-block"
          >
            🚀 Sign Up Now - It's Free!
          </Link>
        </div>
      </div>
    </div>
  );
};

export default Home;