/**
 * Tests for loading store.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';

// Mock the loading store
const createLoadingStore = () => {
  let state = {
    isLoading: false,
    message: '',
    progress: undefined as number | undefined,
  };
  const subscribers = new Set<(value: typeof state) => void>();

  const notify = () => {
    subscribers.forEach((fn) => fn(state));
  };

  return {
    subscribe: (fn: (value: typeof state) => void) => {
      subscribers.add(fn);
      fn(state);
      return () => subscribers.delete(fn);
    },
    start: (message = 'Loading...') => {
      state = { isLoading: true, message, progress: undefined };
      notify();
    },
    stop: () => {
      state = { isLoading: false, message: '', progress: undefined };
      notify();
    },
    setProgress: (progress: number) => {
      state = { ...state, progress };
      notify();
    },
    setMessage: (message: string) => {
      state = { ...state, message };
      notify();
    },
  };
};

describe('Loading Store', () => {
  let loading: ReturnType<typeof createLoadingStore>;

  beforeEach(() => {
    loading = createLoadingStore();
  });

  describe('initial state', () => {
    it('should not be loading initially', () => {
      let state = { isLoading: true, message: '', progress: undefined };
      loading.subscribe((v) => (state = v));
      expect(state.isLoading).toBe(false);
    });

    it('should have empty message initially', () => {
      let state = { isLoading: false, message: 'test', progress: undefined };
      loading.subscribe((v) => (state = v));
      expect(state.message).toBe('');
    });

    it('should have undefined progress initially', () => {
      let state = { isLoading: false, message: '', progress: 50 as number | undefined };
      loading.subscribe((v) => (state = v));
      expect(state.progress).toBeUndefined();
    });
  });

  describe('start', () => {
    it('should set isLoading to true', () => {
      loading.start();

      let state = { isLoading: false, message: '', progress: undefined };
      loading.subscribe((v) => (state = v));
      expect(state.isLoading).toBe(true);
    });

    it('should use default message', () => {
      loading.start();

      let state = { isLoading: false, message: '', progress: undefined };
      loading.subscribe((v) => (state = v));
      expect(state.message).toBe('Loading...');
    });

    it('should use custom message', () => {
      loading.start('Fetching articles...');

      let state = { isLoading: false, message: '', progress: undefined };
      loading.subscribe((v) => (state = v));
      expect(state.message).toBe('Fetching articles...');
    });
  });

  describe('stop', () => {
    it('should set isLoading to false', () => {
      loading.start();
      loading.stop();

      let state = { isLoading: true, message: '', progress: undefined };
      loading.subscribe((v) => (state = v));
      expect(state.isLoading).toBe(false);
    });

    it('should clear message', () => {
      loading.start('Loading...');
      loading.stop();

      let state = { isLoading: false, message: 'test', progress: undefined };
      loading.subscribe((v) => (state = v));
      expect(state.message).toBe('');
    });

    it('should clear progress', () => {
      loading.start();
      loading.setProgress(50);
      loading.stop();

      let state = { isLoading: false, message: '', progress: 50 as number | undefined };
      loading.subscribe((v) => (state = v));
      expect(state.progress).toBeUndefined();
    });
  });

  describe('setProgress', () => {
    it('should update progress', () => {
      loading.start();
      loading.setProgress(50);

      let state = { isLoading: false, message: '', progress: undefined as number | undefined };
      loading.subscribe((v) => (state = v));
      expect(state.progress).toBe(50);
    });

    it('should update progress multiple times', () => {
      loading.start();

      let state = { isLoading: false, message: '', progress: undefined as number | undefined };
      loading.subscribe((v) => (state = v));

      loading.setProgress(25);
      expect(state.progress).toBe(25);

      loading.setProgress(50);
      expect(state.progress).toBe(50);

      loading.setProgress(75);
      expect(state.progress).toBe(75);

      loading.setProgress(100);
      expect(state.progress).toBe(100);
    });
  });

  describe('setMessage', () => {
    it('should update message', () => {
      loading.start('Initial');
      loading.setMessage('Updated message');

      let state = { isLoading: false, message: '', progress: undefined };
      loading.subscribe((v) => (state = v));
      expect(state.message).toBe('Updated message');
    });
  });

  describe('workflow', () => {
    it('should handle complete loading workflow', () => {
      const states: Array<{ isLoading: boolean; message: string; progress?: number }> = [];
      loading.subscribe((v) => states.push({ ...v }));

      loading.start('Searching...');
      loading.setProgress(20);
      loading.setMessage('Fetching...');
      loading.setProgress(50);
      loading.setMessage('Analyzing...');
      loading.setProgress(80);
      loading.stop();

      expect(states[0].isLoading).toBe(false);
      expect(states[1].isLoading).toBe(true);
      expect(states[1].message).toBe('Searching...');
      expect(states[states.length - 1].isLoading).toBe(false);
    });
  });
});

describe('Loading Progress Validation', () => {
  it('should accept 0 as valid progress', () => {
    const loading = createLoadingStore();
    loading.start();
    loading.setProgress(0);

    let state = { isLoading: false, message: '', progress: undefined as number | undefined };
    loading.subscribe((v) => (state = v));
    expect(state.progress).toBe(0);
  });

  it('should accept 100 as valid progress', () => {
    const loading = createLoadingStore();
    loading.start();
    loading.setProgress(100);

    let state = { isLoading: false, message: '', progress: undefined as number | undefined };
    loading.subscribe((v) => (state = v));
    expect(state.progress).toBe(100);
  });
});
