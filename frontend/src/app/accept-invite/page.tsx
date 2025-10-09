'use client';

import { useSearchParams, useRouter } from 'next/navigation';
import { useState } from 'react';
import { apiClient } from '@/lib/api-client';

export default function AcceptInvitePage() {
  const search = useSearchParams();
  const router = useRouter();
  const token = search.get('token') || '';

  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [message, setMessage] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const submit = async () => {
    setMessage(null);
    if (!token) {
      setMessage('Missing token');
      return;
    }
    if (!password || password !== confirm) {
      setMessage('Passwords must match and be non-empty');
      return;
    }
    setSubmitting(true);
    const res = await apiClient.post('/api/v1/auth/accept-invite', { token, password }, { skipAuth: true });
    setSubmitting(false);
    if (res.error) {
      setMessage(res.error);
    } else {
      setMessage('Success! Redirecting to login...');
      setTimeout(() => router.push('/login'), 1200);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="w-full max-w-md bg-white border border-gray-200 rounded-lg shadow p-6">
        <h1 className="text-xl font-semibold text-gray-900 mb-4">Accept Invitation</h1>
        <p className="text-sm text-gray-600 mb-4">Set your account password to finish setup.</p>
        {message && (
          <div className={`mb-3 text-sm ${message.startsWith('Success') ? 'text-green-700' : 'text-red-700'}`}>{message}</div>
        )}
        <div className="space-y-3">
          <div>
            <label className="block text-sm text-gray-700">New Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-700">Confirm Password</label>
            <input
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>
          <button
            onClick={submit}
            disabled={submitting}
            className={`w-full mt-2 px-4 py-2 rounded-md text-white ${submitting ? 'bg-blue-300' : 'bg-blue-600 hover:bg-blue-700'}`}
          >
            {submitting ? 'Submitting...' : 'Set Password'}
          </button>
        </div>
      </div>
    </div>
  );
}

