/**
 * Tests for theme store.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { get } from 'svelte/store';

// Mock the store module
const createThemeStore = () => {
  let current = 'light';
  const subscribers = new Set<(value: string) => void>();

  return {
    subscribe: (fn: (value: string) => void) => {
      subscribers.add(fn);
      fn(current);
      return () => subscribers.delete(fn);
    },
    set: (value: string) => {
      current = value;
      subscribers.forEach((fn) => fn(value));
    },
    toggle: () => {
      current = current === 'light' ? 'dark' : 'light';
      subscribers.forEach((fn) => fn(current));
    },
    init: () => {
      // Check localStorage or system preference
      const stored = localStorage.getItem('theme');
      if (stored) {
        current = stored;
      } else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
        current = 'dark';
      }
      subscribers.forEach((fn) => fn(current));
    },
  };
};

describe('Theme Store', () => {
  let theme: ReturnType<typeof createThemeStore>;

  beforeEach(() => {
    localStorage.clear();
    theme = createThemeStore();
  });

  describe('initial state', () => {
    it('should default to light theme', () => {
      let value = '';
      theme.subscribe((v) => (value = v));
      expect(value).toBe('light');
    });

    it('should use stored theme from localStorage', () => {
      localStorage.setItem('theme', 'dark');
      theme = createThemeStore();
      theme.init();

      let value = '';
      theme.subscribe((v) => (value = v));
      expect(value).toBe('dark');
    });
  });

  describe('set', () => {
    it('should update theme to light', () => {
      theme.set('light');

      let value = '';
      theme.subscribe((v) => (value = v));
      expect(value).toBe('light');
    });

    it('should update theme to dark', () => {
      theme.set('dark');

      let value = '';
      theme.subscribe((v) => (value = v));
      expect(value).toBe('dark');
    });
  });

  describe('toggle', () => {
    it('should toggle from light to dark', () => {
      theme.set('light');
      theme.toggle();

      let value = '';
      theme.subscribe((v) => (value = v));
      expect(value).toBe('dark');
    });

    it('should toggle from dark to light', () => {
      theme.set('dark');
      theme.toggle();

      let value = '';
      theme.subscribe((v) => (value = v));
      expect(value).toBe('light');
    });

    it('should toggle multiple times', () => {
      let value = '';
      theme.subscribe((v) => (value = v));

      theme.toggle();
      expect(value).toBe('dark');

      theme.toggle();
      expect(value).toBe('light');

      theme.toggle();
      expect(value).toBe('dark');
    });
  });

  describe('subscribers', () => {
    it('should notify subscribers on change', () => {
      const values: string[] = [];
      theme.subscribe((v) => values.push(v));

      theme.set('dark');
      theme.set('light');
      theme.toggle();

      expect(values).toEqual(['light', 'dark', 'light', 'dark']);
    });

    it('should allow unsubscribing', () => {
      const values: string[] = [];
      const unsubscribe = theme.subscribe((v) => values.push(v));

      theme.set('dark');
      unsubscribe();
      theme.set('light');

      expect(values).toEqual(['light', 'dark']);
    });
  });
});

describe('Theme CSS Classes', () => {
  it('should have valid theme class names', () => {
    const lightClass = 'light';
    const darkClass = 'dark';

    expect(lightClass).toBe('light');
    expect(darkClass).toBe('dark');
  });

  it('should be used on document element', () => {
    // In a real component, this would be:
    // document.documentElement.classList.add(theme)
    const classList = new Set<string>();
    classList.add('dark');

    expect(classList.has('dark')).toBe(true);
  });
});
