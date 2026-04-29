import React from 'react';

export default function Login() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full">
        <h2 className="text-3xl font-bold text-center mb-8">Sign In</h2>
        <form className="space-y-6">
          <input type="email" placeholder="Email" className="input" />
          <input type="password" placeholder="Password" className="input" />
          <button className="btn btn-primary w-full">Sign In</button>
        </form>
      </div>
    </div>
  );
}