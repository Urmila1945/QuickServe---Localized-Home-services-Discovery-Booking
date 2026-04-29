import React from 'react';

export default function Register() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full">
        <h2 className="text-3xl font-bold text-center mb-8">Sign Up</h2>
        <form className="space-y-6">
          <input type="text" placeholder="Full Name" className="input" />
          <input type="email" placeholder="Email" className="input" />
          <input type="tel" placeholder="Phone" className="input" />
          <input type="password" placeholder="Password" className="input" />
          <button className="btn btn-primary w-full">Sign Up</button>
        </form>
      </div>
    </div>
  );
}