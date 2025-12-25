/**
 * Tests for user store.
 */

import { describe, it, expect, beforeEach } from 'vitest';

interface User {
  id: string;
  email: string;
  subscriptionTier: 'free' | 'basic' | 'pro';
}

// Mock the user store
const createUserStore = () => {
  let current: User | null = null;
  const subscribers = new Set<(value: User | null) => void>();

  return {
    subscribe: (fn: (value: User | null) => void) => {
      subscribers.add(fn);
      fn(current);
      return () => subscribers.delete(fn);
    },
    set: (user: User | null) => {
      current = user;
      subscribers.forEach((fn) => fn(current));
    },
    login: (user: User) => {
      current = user;
      subscribers.forEach((fn) => fn(current));
    },
    logout: () => {
      current = null;
      subscribers.forEach((fn) => fn(current));
    },
    updateTier: (tier: 'free' | 'basic' | 'pro') => {
      if (current) {
        current = { ...current, subscriptionTier: tier };
        subscribers.forEach((fn) => fn(current));
      }
    },
  };
};

describe('User Store', () => {
  let user: ReturnType<typeof createUserStore>;

  beforeEach(() => {
    user = createUserStore();
  });

  describe('initial state', () => {
    it('should be null initially', () => {
      let value: User | null = {} as User;
      user.subscribe((v) => (value = v));
      expect(value).toBeNull();
    });
  });

  describe('login', () => {
    it('should set user on login', () => {
      const userData: User = {
        id: 'user-123',
        email: 'test@example.com',
        subscriptionTier: 'free',
      };

      user.login(userData);

      let value: User | null = null;
      user.subscribe((v) => (value = v));
      expect(value).toEqual(userData);
    });

    it('should notify subscribers on login', () => {
      const values: (User | null)[] = [];
      user.subscribe((v) => values.push(v));

      user.login({
        id: 'user-123',
        email: 'test@example.com',
        subscriptionTier: 'free',
      });

      expect(values.length).toBe(2);
      expect(values[0]).toBeNull();
      expect(values[1]).not.toBeNull();
    });
  });

  describe('logout', () => {
    it('should set user to null on logout', () => {
      user.login({
        id: 'user-123',
        email: 'test@example.com',
        subscriptionTier: 'free',
      });

      user.logout();

      let value: User | null = {} as User;
      user.subscribe((v) => (value = v));
      expect(value).toBeNull();
    });
  });

  describe('updateTier', () => {
    it('should update subscription tier', () => {
      user.login({
        id: 'user-123',
        email: 'test@example.com',
        subscriptionTier: 'free',
      });

      user.updateTier('pro');

      let value: User | null = null;
      user.subscribe((v) => (value = v));
      expect(value?.subscriptionTier).toBe('pro');
    });

    it('should not update if no user is logged in', () => {
      user.updateTier('pro');

      let value: User | null = {} as User;
      user.subscribe((v) => (value = v));
      expect(value).toBeNull();
    });

    it('should preserve other user data', () => {
      const userData: User = {
        id: 'user-123',
        email: 'test@example.com',
        subscriptionTier: 'free',
      };

      user.login(userData);
      user.updateTier('basic');

      let value: User | null = null;
      user.subscribe((v) => (value = v));
      expect(value?.id).toBe('user-123');
      expect(value?.email).toBe('test@example.com');
      expect(value?.subscriptionTier).toBe('basic');
    });
  });

  describe('subscription tiers', () => {
    it('should accept free tier', () => {
      user.login({
        id: 'user-1',
        email: 'free@example.com',
        subscriptionTier: 'free',
      });

      let value: User | null = null;
      user.subscribe((v) => (value = v));
      expect(value?.subscriptionTier).toBe('free');
    });

    it('should accept basic tier', () => {
      user.login({
        id: 'user-1',
        email: 'basic@example.com',
        subscriptionTier: 'basic',
      });

      let value: User | null = null;
      user.subscribe((v) => (value = v));
      expect(value?.subscriptionTier).toBe('basic');
    });

    it('should accept pro tier', () => {
      user.login({
        id: 'user-1',
        email: 'pro@example.com',
        subscriptionTier: 'pro',
      });

      let value: User | null = null;
      user.subscribe((v) => (value = v));
      expect(value?.subscriptionTier).toBe('pro');
    });
  });
});

describe('User Authentication Flow', () => {
  it('should handle login -> update -> logout flow', () => {
    const user = createUserStore();
    const states: (User | null)[] = [];
    user.subscribe((v) => states.push(v));

    user.login({
      id: 'user-123',
      email: 'test@example.com',
      subscriptionTier: 'free',
    });

    user.updateTier('pro');
    user.logout();

    expect(states[0]).toBeNull();
    expect(states[1]?.subscriptionTier).toBe('free');
    expect(states[2]?.subscriptionTier).toBe('pro');
    expect(states[3]).toBeNull();
  });
});
