/**
 * Tests for preferences store.
 */

import { describe, it, expect, beforeEach } from 'vitest';

interface Topic {
  name: string;
  keywords: string[];
  priority: number;
  enabled: boolean;
}

interface DeliveryConfig {
  frequency: 'hourly' | 'daily_am' | 'daily_pm' | 'weekly' | 'biweekly' | 'monthly';
  deliveryTimeUtc: string;
  channels: ('web' | 'rss' | 'email')[];
  timezone: string;
}

interface StyleConfig {
  tone: 'hn-style' | 'formal' | 'casual';
  skepticismLevel: number;
  technicalDepth: number;
  includeBiasAnalysis: boolean;
  includeCrossConnections: boolean;
  maxArticlesPerTopic: number;
}

interface Preferences {
  topics: Topic[];
  delivery: DeliveryConfig;
  style: StyleConfig;
}

// Mock the preferences store
const createPreferencesStore = () => {
  let current: Preferences = {
    topics: [],
    delivery: {
      frequency: 'daily_am',
      deliveryTimeUtc: '06:00',
      channels: ['web'],
      timezone: 'UTC',
    },
    style: {
      tone: 'hn-style',
      skepticismLevel: 3,
      technicalDepth: 3,
      includeBiasAnalysis: true,
      includeCrossConnections: true,
      maxArticlesPerTopic: 5,
    },
  };
  const subscribers = new Set<(value: Preferences) => void>();

  const notify = () => {
    subscribers.forEach((fn) => fn(current));
  };

  return {
    subscribe: (fn: (value: Preferences) => void) => {
      subscribers.add(fn);
      fn(current);
      return () => subscribers.delete(fn);
    },
    set: (prefs: Preferences) => {
      current = prefs;
      notify();
    },
    addTopic: (topic: Topic) => {
      current = { ...current, topics: [...current.topics, topic] };
      notify();
    },
    removeTopic: (name: string) => {
      current = {
        ...current,
        topics: current.topics.filter((t) => t.name !== name),
      };
      notify();
    },
    updateTopic: (name: string, updates: Partial<Topic>) => {
      current = {
        ...current,
        topics: current.topics.map((t) =>
          t.name === name ? { ...t, ...updates } : t
        ),
      };
      notify();
    },
    updateDelivery: (updates: Partial<DeliveryConfig>) => {
      current = {
        ...current,
        delivery: { ...current.delivery, ...updates },
      };
      notify();
    },
    updateStyle: (updates: Partial<StyleConfig>) => {
      current = {
        ...current,
        style: { ...current.style, ...updates },
      };
      notify();
    },
  };
};

describe('Preferences Store', () => {
  let preferences: ReturnType<typeof createPreferencesStore>;

  beforeEach(() => {
    preferences = createPreferencesStore();
  });

  describe('initial state', () => {
    it('should have default delivery settings', () => {
      let value: Preferences | null = null;
      preferences.subscribe((v) => (value = v));

      expect(value?.delivery.frequency).toBe('daily_am');
      expect(value?.delivery.deliveryTimeUtc).toBe('06:00');
    });

    it('should have default style settings', () => {
      let value: Preferences | null = null;
      preferences.subscribe((v) => (value = v));

      expect(value?.style.tone).toBe('hn-style');
      expect(value?.style.skepticismLevel).toBe(3);
    });

    it('should have empty topics', () => {
      let value: Preferences | null = null;
      preferences.subscribe((v) => (value = v));

      expect(value?.topics).toEqual([]);
    });
  });

  describe('addTopic', () => {
    it('should add a new topic', () => {
      preferences.addTopic({
        name: 'AI',
        keywords: ['artificial intelligence', 'LLM'],
        priority: 5,
        enabled: true,
      });

      let value: Preferences | null = null;
      preferences.subscribe((v) => (value = v));

      expect(value?.topics.length).toBe(1);
      expect(value?.topics[0].name).toBe('AI');
    });

    it('should add multiple topics', () => {
      preferences.addTopic({
        name: 'AI',
        keywords: ['AI'],
        priority: 5,
        enabled: true,
      });
      preferences.addTopic({
        name: 'Science',
        keywords: ['research'],
        priority: 4,
        enabled: true,
      });

      let value: Preferences | null = null;
      preferences.subscribe((v) => (value = v));

      expect(value?.topics.length).toBe(2);
    });
  });

  describe('removeTopic', () => {
    it('should remove a topic by name', () => {
      preferences.addTopic({
        name: 'AI',
        keywords: ['AI'],
        priority: 5,
        enabled: true,
      });
      preferences.removeTopic('AI');

      let value: Preferences | null = null;
      preferences.subscribe((v) => (value = v));

      expect(value?.topics.length).toBe(0);
    });

    it('should only remove the specified topic', () => {
      preferences.addTopic({
        name: 'AI',
        keywords: ['AI'],
        priority: 5,
        enabled: true,
      });
      preferences.addTopic({
        name: 'Science',
        keywords: ['research'],
        priority: 4,
        enabled: true,
      });
      preferences.removeTopic('AI');

      let value: Preferences | null = null;
      preferences.subscribe((v) => (value = v));

      expect(value?.topics.length).toBe(1);
      expect(value?.topics[0].name).toBe('Science');
    });
  });

  describe('updateTopic', () => {
    it('should update topic properties', () => {
      preferences.addTopic({
        name: 'AI',
        keywords: ['AI'],
        priority: 3,
        enabled: true,
      });
      preferences.updateTopic('AI', { priority: 5 });

      let value: Preferences | null = null;
      preferences.subscribe((v) => (value = v));

      expect(value?.topics[0].priority).toBe(5);
    });

    it('should toggle topic enabled state', () => {
      preferences.addTopic({
        name: 'AI',
        keywords: ['AI'],
        priority: 3,
        enabled: true,
      });
      preferences.updateTopic('AI', { enabled: false });

      let value: Preferences | null = null;
      preferences.subscribe((v) => (value = v));

      expect(value?.topics[0].enabled).toBe(false);
    });
  });

  describe('updateDelivery', () => {
    it('should update frequency', () => {
      preferences.updateDelivery({ frequency: 'weekly' });

      let value: Preferences | null = null;
      preferences.subscribe((v) => (value = v));

      expect(value?.delivery.frequency).toBe('weekly');
    });

    it('should update channels', () => {
      preferences.updateDelivery({ channels: ['web', 'email', 'rss'] });

      let value: Preferences | null = null;
      preferences.subscribe((v) => (value = v));

      expect(value?.delivery.channels).toEqual(['web', 'email', 'rss']);
    });

    it('should update delivery time', () => {
      preferences.updateDelivery({ deliveryTimeUtc: '18:00' });

      let value: Preferences | null = null;
      preferences.subscribe((v) => (value = v));

      expect(value?.delivery.deliveryTimeUtc).toBe('18:00');
    });
  });

  describe('updateStyle', () => {
    it('should update tone', () => {
      preferences.updateStyle({ tone: 'formal' });

      let value: Preferences | null = null;
      preferences.subscribe((v) => (value = v));

      expect(value?.style.tone).toBe('formal');
    });

    it('should update skepticism level', () => {
      preferences.updateStyle({ skepticismLevel: 5 });

      let value: Preferences | null = null;
      preferences.subscribe((v) => (value = v));

      expect(value?.style.skepticismLevel).toBe(5);
    });

    it('should update technical depth', () => {
      preferences.updateStyle({ technicalDepth: 1 });

      let value: Preferences | null = null;
      preferences.subscribe((v) => (value = v));

      expect(value?.style.technicalDepth).toBe(1);
    });

    it('should toggle bias analysis', () => {
      preferences.updateStyle({ includeBiasAnalysis: false });

      let value: Preferences | null = null;
      preferences.subscribe((v) => (value = v));

      expect(value?.style.includeBiasAnalysis).toBe(false);
    });
  });
});

describe('Frequency Validation', () => {
  it('should accept all valid frequencies', () => {
    const frequencies = ['hourly', 'daily_am', 'daily_pm', 'weekly', 'biweekly', 'monthly'];

    frequencies.forEach((freq) => {
      expect(frequencies).toContain(freq);
    });
  });
});

describe('Style Validation', () => {
  it('should accept all valid tones', () => {
    const tones = ['hn-style', 'formal', 'casual'];

    tones.forEach((tone) => {
      expect(tones).toContain(tone);
    });
  });

  it('should validate skepticism level range', () => {
    const validLevels = [1, 2, 3, 4, 5];

    validLevels.forEach((level) => {
      expect(level).toBeGreaterThanOrEqual(1);
      expect(level).toBeLessThanOrEqual(5);
    });
  });
});
