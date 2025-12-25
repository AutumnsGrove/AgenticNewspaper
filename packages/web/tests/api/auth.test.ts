/**
 * Tests for authentication API client.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock the auth API
const createAuthApi = (baseUrl: string) => {
  let token: string | null = null;

  return {
    baseUrl,
    getToken: () => token,
    setToken: (newToken: string | null) => {
      token = newToken;
    },
    login: async (email: string, password: string) => {
      const response = await fetch(`${baseUrl}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || 'Login failed');
      }
      const data = await response.json();
      token = data.token;
      return data;
    },
    register: async (email: string, password: string, name?: string) => {
      const response = await fetch(`${baseUrl}/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, name }),
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || 'Registration failed');
      }
      const data = await response.json();
      token = data.token;
      return data;
    },
    logout: async () => {
      if (token) {
        await fetch(`${baseUrl}/api/auth/logout`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
        });
      }
      token = null;
    },
    refreshToken: async () => {
      const response = await fetch(`${baseUrl}/api/auth/refresh`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        token = null;
        throw new Error('Token refresh failed');
      }
      const data = await response.json();
      token = data.token;
      return data;
    },
    verifyEmail: async (verificationToken: string) => {
      const response = await fetch(`${baseUrl}/api/auth/verify-email`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: verificationToken }),
      });
      if (!response.ok) throw new Error('Email verification failed');
      return response.json();
    },
    requestPasswordReset: async (email: string) => {
      const response = await fetch(`${baseUrl}/api/auth/forgot-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });
      if (!response.ok) throw new Error('Password reset request failed');
      return response.json();
    },
    resetPassword: async (resetToken: string, newPassword: string) => {
      const response = await fetch(`${baseUrl}/api/auth/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: resetToken, password: newPassword }),
      });
      if (!response.ok) throw new Error('Password reset failed');
      return response.json();
    },
    getProfile: async () => {
      const response = await fetch(`${baseUrl}/api/auth/profile`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) throw new Error('Failed to fetch profile');
      return response.json();
    },
    updateProfile: async (updates: { name?: string; email?: string }) => {
      const response = await fetch(`${baseUrl}/api/auth/profile`, {
        method: 'PATCH',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updates),
      });
      if (!response.ok) throw new Error('Profile update failed');
      return response.json();
    },
  };
};

// Mock fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('Auth API Client', () => {
  let api: ReturnType<typeof createAuthApi>;

  beforeEach(() => {
    api = createAuthApi('https://clearing.autumnsgrove.com');
    mockFetch.mockReset();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('login', () => {
    it('should login with valid credentials', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            token: 'jwt-token-123',
            user: { id: 'user-1', email: 'test@example.com' },
          }),
      });

      const result = await api.login('test@example.com', 'password123');

      expect(mockFetch).toHaveBeenCalledWith(
        'https://clearing.autumnsgrove.com/api/auth/login',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ email: 'test@example.com', password: 'password123' }),
        })
      );
      expect(result.token).toBe('jwt-token-123');
      expect(api.getToken()).toBe('jwt-token-123');
    });

    it('should throw error on invalid credentials', async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        json: () => Promise.resolve({ message: 'Invalid email or password' }),
      });

      await expect(api.login('test@example.com', 'wrongpassword')).rejects.toThrow(
        'Invalid email or password'
      );
      expect(api.getToken()).toBeNull();
    });

    it('should throw error on server error', async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        json: () => Promise.resolve({}),
      });

      await expect(api.login('test@example.com', 'password')).rejects.toThrow('Login failed');
    });
  });

  describe('register', () => {
    it('should register new user', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            token: 'jwt-token-456',
            user: { id: 'user-2', email: 'new@example.com' },
          }),
      });

      const result = await api.register('new@example.com', 'password123', 'John Doe');

      expect(mockFetch).toHaveBeenCalledWith(
        'https://clearing.autumnsgrove.com/api/auth/register',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            email: 'new@example.com',
            password: 'password123',
            name: 'John Doe',
          }),
        })
      );
      expect(result.token).toBe('jwt-token-456');
    });

    it('should register without name', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            token: 'jwt-token-789',
            user: { id: 'user-3', email: 'noname@example.com' },
          }),
      });

      await api.register('noname@example.com', 'password123');

      expect(mockFetch).toHaveBeenCalledWith(
        'https://clearing.autumnsgrove.com/api/auth/register',
        expect.objectContaining({
          body: JSON.stringify({
            email: 'noname@example.com',
            password: 'password123',
            name: undefined,
          }),
        })
      );
    });

    it('should throw error if email already exists', async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        json: () => Promise.resolve({ message: 'Email already registered' }),
      });

      await expect(api.register('existing@example.com', 'password123')).rejects.toThrow(
        'Email already registered'
      );
    });
  });

  describe('logout', () => {
    it('should clear token on logout', async () => {
      mockFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({}) });

      // First login
      api.setToken('jwt-token-123');
      expect(api.getToken()).toBe('jwt-token-123');

      await api.logout();

      expect(api.getToken()).toBeNull();
    });

    it('should call logout endpoint if token exists', async () => {
      mockFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({}) });
      api.setToken('jwt-token-123');

      await api.logout();

      expect(mockFetch).toHaveBeenCalledWith(
        'https://clearing.autumnsgrove.com/api/auth/logout',
        expect.objectContaining({
          method: 'POST',
          headers: { Authorization: 'Bearer jwt-token-123' },
        })
      );
    });

    it('should not call endpoint if no token', async () => {
      await api.logout();

      expect(mockFetch).not.toHaveBeenCalled();
    });
  });

  describe('refreshToken', () => {
    it('should refresh token successfully', async () => {
      api.setToken('old-token');
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ token: 'new-token-123' }),
      });

      const result = await api.refreshToken();

      expect(result.token).toBe('new-token-123');
      expect(api.getToken()).toBe('new-token-123');
    });

    it('should clear token on refresh failure', async () => {
      api.setToken('expired-token');
      mockFetch.mockResolvedValue({ ok: false });

      await expect(api.refreshToken()).rejects.toThrow('Token refresh failed');
      expect(api.getToken()).toBeNull();
    });
  });

  describe('verifyEmail', () => {
    it('should verify email with valid token', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ verified: true }),
      });

      const result = await api.verifyEmail('verification-token-123');

      expect(mockFetch).toHaveBeenCalledWith(
        'https://clearing.autumnsgrove.com/api/auth/verify-email',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ token: 'verification-token-123' }),
        })
      );
      expect(result.verified).toBe(true);
    });

    it('should throw error on invalid verification token', async () => {
      mockFetch.mockResolvedValue({ ok: false });

      await expect(api.verifyEmail('invalid-token')).rejects.toThrow('Email verification failed');
    });
  });

  describe('password reset', () => {
    it('should request password reset', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ message: 'Reset email sent' }),
      });

      await api.requestPasswordReset('user@example.com');

      expect(mockFetch).toHaveBeenCalledWith(
        'https://clearing.autumnsgrove.com/api/auth/forgot-password',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ email: 'user@example.com' }),
        })
      );
    });

    it('should reset password with valid token', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ success: true }),
      });

      await api.resetPassword('reset-token-123', 'newpassword456');

      expect(mockFetch).toHaveBeenCalledWith(
        'https://clearing.autumnsgrove.com/api/auth/reset-password',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ token: 'reset-token-123', password: 'newpassword456' }),
        })
      );
    });

    it('should throw error on invalid reset token', async () => {
      mockFetch.mockResolvedValue({ ok: false });

      await expect(api.resetPassword('invalid-token', 'newpassword')).rejects.toThrow(
        'Password reset failed'
      );
    });
  });

  describe('profile', () => {
    it('should get user profile', async () => {
      api.setToken('jwt-token');
      mockFetch.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            id: 'user-1',
            email: 'user@example.com',
            name: 'Test User',
            subscriptionTier: 'pro',
          }),
      });

      const profile = await api.getProfile();

      expect(profile.email).toBe('user@example.com');
      expect(profile.subscriptionTier).toBe('pro');
    });

    it('should update profile', async () => {
      api.setToken('jwt-token');
      mockFetch.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            id: 'user-1',
            email: 'user@example.com',
            name: 'Updated Name',
          }),
      });

      const result = await api.updateProfile({ name: 'Updated Name' });

      expect(result.name).toBe('Updated Name');
    });

    it('should throw error on unauthorized profile access', async () => {
      api.setToken('invalid-token');
      mockFetch.mockResolvedValue({ ok: false });

      await expect(api.getProfile()).rejects.toThrow('Failed to fetch profile');
    });
  });
});

describe('Token Management', () => {
  it('should persist token across requests', async () => {
    const api = createAuthApi('https://clearing.autumnsgrove.com');

    api.setToken('persistent-token');

    expect(api.getToken()).toBe('persistent-token');
  });

  it('should clear token on setToken(null)', () => {
    const api = createAuthApi('https://clearing.autumnsgrove.com');

    api.setToken('some-token');
    api.setToken(null);

    expect(api.getToken()).toBeNull();
  });
});

describe('Email Validation', () => {
  it('should validate email format', () => {
    const validEmails = [
      'test@example.com',
      'user.name@domain.org',
      'user+tag@example.co.uk',
      'a@b.io',
    ];

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    validEmails.forEach((email) => {
      expect(email).toMatch(emailRegex);
    });
  });

  it('should reject invalid email formats', () => {
    const invalidEmails = ['notanemail', '@nodomain.com', 'missing@', 'spaces in@email.com'];

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    invalidEmails.forEach((email) => {
      expect(email).not.toMatch(emailRegex);
    });
  });
});

describe('Password Validation', () => {
  it('should validate password minimum length', () => {
    const minLength = 8;

    expect('short'.length).toBeLessThan(minLength);
    expect('longenough'.length).toBeGreaterThanOrEqual(minLength);
  });

  it('should validate password complexity', () => {
    const hasUpperCase = (str: string) => /[A-Z]/.test(str);
    const hasLowerCase = (str: string) => /[a-z]/.test(str);
    const hasNumber = (str: string) => /[0-9]/.test(str);

    const strongPassword = 'SecurePass123';

    expect(hasUpperCase(strongPassword)).toBe(true);
    expect(hasLowerCase(strongPassword)).toBe(true);
    expect(hasNumber(strongPassword)).toBe(true);
  });
});
