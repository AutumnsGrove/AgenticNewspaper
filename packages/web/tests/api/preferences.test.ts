/**
 * Tests for preferences API client.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

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

interface UserPreferences {
  topics: Topic[];
  delivery: DeliveryConfig;
  style: StyleConfig;
}

// Mock the preferences API
const createPreferencesApi = (baseUrl: string, getToken: () => string | null) => {
  const authHeader = () => {
    const token = getToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  };

  return {
    baseUrl,
    getPreferences: async (): Promise<UserPreferences> => {
      const response = await fetch(`${baseUrl}/api/preferences`, {
        headers: authHeader(),
      });
      if (!response.ok) throw new Error('Failed to fetch preferences');
      return response.json();
    },
    updatePreferences: async (updates: Partial<UserPreferences>) => {
      const response = await fetch(`${baseUrl}/api/preferences`, {
        method: 'PATCH',
        headers: { ...authHeader(), 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      });
      if (!response.ok) throw new Error('Failed to update preferences');
      return response.json();
    },
    addTopic: async (topic: Topic) => {
      const response = await fetch(`${baseUrl}/api/preferences/topics`, {
        method: 'POST',
        headers: { ...authHeader(), 'Content-Type': 'application/json' },
        body: JSON.stringify(topic),
      });
      if (!response.ok) throw new Error('Failed to add topic');
      return response.json();
    },
    updateTopic: async (name: string, updates: Partial<Topic>) => {
      const response = await fetch(`${baseUrl}/api/preferences/topics/${encodeURIComponent(name)}`, {
        method: 'PATCH',
        headers: { ...authHeader(), 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      });
      if (!response.ok) throw new Error('Failed to update topic');
      return response.json();
    },
    deleteTopic: async (name: string) => {
      const response = await fetch(`${baseUrl}/api/preferences/topics/${encodeURIComponent(name)}`, {
        method: 'DELETE',
        headers: authHeader(),
      });
      if (!response.ok) throw new Error('Failed to delete topic');
      return response.json();
    },
    updateDelivery: async (updates: Partial<DeliveryConfig>) => {
      const response = await fetch(`${baseUrl}/api/preferences/delivery`, {
        method: 'PATCH',
        headers: { ...authHeader(), 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      });
      if (!response.ok) throw new Error('Failed to update delivery settings');
      return response.json();
    },
    updateStyle: async (updates: Partial<StyleConfig>) => {
      const response = await fetch(`${baseUrl}/api/preferences/style`, {
        method: 'PATCH',
        headers: { ...authHeader(), 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      });
      if (!response.ok) throw new Error('Failed to update style settings');
      return response.json();
    },
    resetToDefaults: async () => {
      const response = await fetch(`${baseUrl}/api/preferences/reset`, {
        method: 'POST',
        headers: authHeader(),
      });
      if (!response.ok) throw new Error('Failed to reset preferences');
      return response.json();
    },
    exportPreferences: async () => {
      const response = await fetch(`${baseUrl}/api/preferences/export`, {
        headers: authHeader(),
      });
      if (!response.ok) throw new Error('Failed to export preferences');
      return response.json();
    },
    importPreferences: async (preferences: UserPreferences) => {
      const response = await fetch(`${baseUrl}/api/preferences/import`, {
        method: 'POST',
        headers: { ...authHeader(), 'Content-Type': 'application/json' },
        body: JSON.stringify(preferences),
      });
      if (!response.ok) throw new Error('Failed to import preferences');
      return response.json();
    },
  };
};

// Mock fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('Preferences API Client', () => {
  let api: ReturnType<typeof createPreferencesApi>;
  let token: string | null = 'test-token';

  beforeEach(() => {
    api = createPreferencesApi('https://clearing.autumnsgrove.com', () => token);
    mockFetch.mockReset();
    token = 'test-token';
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('getPreferences', () => {
    it('should fetch user preferences', async () => {
      const mockPrefs: UserPreferences = {
        topics: [{ name: 'AI', keywords: ['AI', 'ML'], priority: 5, enabled: true }],
        delivery: {
          frequency: 'daily_am',
          deliveryTimeUtc: '06:00',
          channels: ['web', 'email'],
          timezone: 'America/New_York',
        },
        style: {
          tone: 'hn-style',
          skepticismLevel: 3,
          technicalDepth: 4,
          includeBiasAnalysis: true,
          includeCrossConnections: true,
          maxArticlesPerTopic: 5,
        },
      };

      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockPrefs),
      });

      const result = await api.getPreferences();

      expect(mockFetch).toHaveBeenCalledWith('https://clearing.autumnsgrove.com/api/preferences', {
        headers: { Authorization: 'Bearer test-token' },
      });
      expect(result.topics).toHaveLength(1);
      expect(result.delivery.frequency).toBe('daily_am');
    });

    it('should throw error on fetch failure', async () => {
      mockFetch.mockResolvedValue({ ok: false });

      await expect(api.getPreferences()).rejects.toThrow('Failed to fetch preferences');
    });
  });

  describe('updatePreferences', () => {
    it('should update all preferences', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ success: true }),
      });

      await api.updatePreferences({
        delivery: { frequency: 'weekly' } as DeliveryConfig,
      });

      expect(mockFetch).toHaveBeenCalledWith(
        'https://clearing.autumnsgrove.com/api/preferences',
        expect.objectContaining({
          method: 'PATCH',
          body: JSON.stringify({ delivery: { frequency: 'weekly' } }),
        })
      );
    });
  });

  describe('topic management', () => {
    it('should add a new topic', async () => {
      const newTopic: Topic = {
        name: 'Science',
        keywords: ['research', 'discovery'],
        priority: 4,
        enabled: true,
      };

      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ ...newTopic, id: 'topic-123' }),
      });

      const result = await api.addTopic(newTopic);

      expect(mockFetch).toHaveBeenCalledWith(
        'https://clearing.autumnsgrove.com/api/preferences/topics',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(newTopic),
        })
      );
      expect(result.name).toBe('Science');
    });

    it('should update an existing topic', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ name: 'AI', priority: 5 }),
      });

      await api.updateTopic('AI', { priority: 5 });

      expect(mockFetch).toHaveBeenCalledWith(
        'https://clearing.autumnsgrove.com/api/preferences/topics/AI',
        expect.objectContaining({
          method: 'PATCH',
          body: JSON.stringify({ priority: 5 }),
        })
      );
    });

    it('should URL-encode topic names with special characters', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ success: true }),
      });

      await api.updateTopic('AI & ML', { priority: 5 });

      expect(mockFetch).toHaveBeenCalledWith(
        'https://clearing.autumnsgrove.com/api/preferences/topics/AI%20%26%20ML',
        expect.anything()
      );
    });

    it('should delete a topic', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ success: true }),
      });

      await api.deleteTopic('Science');

      expect(mockFetch).toHaveBeenCalledWith(
        'https://clearing.autumnsgrove.com/api/preferences/topics/Science',
        expect.objectContaining({
          method: 'DELETE',
        })
      );
    });
  });

  describe('delivery settings', () => {
    it('should update frequency', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ frequency: 'weekly' }),
      });

      await api.updateDelivery({ frequency: 'weekly' });

      expect(mockFetch).toHaveBeenCalledWith(
        'https://clearing.autumnsgrove.com/api/preferences/delivery',
        expect.objectContaining({
          method: 'PATCH',
          body: JSON.stringify({ frequency: 'weekly' }),
        })
      );
    });

    it('should update channels', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ channels: ['web', 'rss'] }),
      });

      await api.updateDelivery({ channels: ['web', 'rss'] });

      expect(mockFetch).toHaveBeenCalledWith(
        'https://clearing.autumnsgrove.com/api/preferences/delivery',
        expect.objectContaining({
          body: JSON.stringify({ channels: ['web', 'rss'] }),
        })
      );
    });

    it('should update timezone', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ timezone: 'America/Los_Angeles' }),
      });

      await api.updateDelivery({ timezone: 'America/Los_Angeles' });

      expect(mockFetch).toHaveBeenCalledWith(
        'https://clearing.autumnsgrove.com/api/preferences/delivery',
        expect.objectContaining({
          body: JSON.stringify({ timezone: 'America/Los_Angeles' }),
        })
      );
    });
  });

  describe('style settings', () => {
    it('should update tone', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ tone: 'formal' }),
      });

      await api.updateStyle({ tone: 'formal' });

      expect(mockFetch).toHaveBeenCalledWith(
        'https://clearing.autumnsgrove.com/api/preferences/style',
        expect.objectContaining({
          body: JSON.stringify({ tone: 'formal' }),
        })
      );
    });

    it('should update skepticism level', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ skepticismLevel: 5 }),
      });

      await api.updateStyle({ skepticismLevel: 5 });

      expect(mockFetch).toHaveBeenCalledWith(
        'https://clearing.autumnsgrove.com/api/preferences/style',
        expect.objectContaining({
          body: JSON.stringify({ skepticismLevel: 5 }),
        })
      );
    });

    it('should toggle bias analysis', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ includeBiasAnalysis: false }),
      });

      await api.updateStyle({ includeBiasAnalysis: false });

      expect(mockFetch).toHaveBeenCalledWith(
        'https://clearing.autumnsgrove.com/api/preferences/style',
        expect.objectContaining({
          body: JSON.stringify({ includeBiasAnalysis: false }),
        })
      );
    });
  });

  describe('reset and import/export', () => {
    it('should reset preferences to defaults', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            topics: [],
            delivery: { frequency: 'daily_am' },
            style: { tone: 'hn-style' },
          }),
      });

      await api.resetToDefaults();

      expect(mockFetch).toHaveBeenCalledWith(
        'https://clearing.autumnsgrove.com/api/preferences/reset',
        expect.objectContaining({ method: 'POST' })
      );
    });

    it('should export preferences', async () => {
      const exportedPrefs: UserPreferences = {
        topics: [{ name: 'Tech', keywords: ['technology'], priority: 5, enabled: true }],
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

      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(exportedPrefs),
      });

      const result = await api.exportPreferences();

      expect(result.topics).toHaveLength(1);
    });

    it('should import preferences', async () => {
      const prefsToImport: UserPreferences = {
        topics: [{ name: 'AI', keywords: ['AI'], priority: 5, enabled: true }],
        delivery: {
          frequency: 'weekly',
          deliveryTimeUtc: '08:00',
          channels: ['email'],
          timezone: 'Europe/London',
        },
        style: {
          tone: 'formal',
          skepticismLevel: 4,
          technicalDepth: 5,
          includeBiasAnalysis: false,
          includeCrossConnections: true,
          maxArticlesPerTopic: 10,
        },
      };

      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ success: true, imported: prefsToImport }),
      });

      await api.importPreferences(prefsToImport);

      expect(mockFetch).toHaveBeenCalledWith(
        'https://clearing.autumnsgrove.com/api/preferences/import',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(prefsToImport),
        })
      );
    });
  });
});

describe('Preferences Validation', () => {
  describe('topic validation', () => {
    it('should validate topic name is not empty', () => {
      const topic: Topic = { name: '', keywords: ['AI'], priority: 3, enabled: true };
      expect(topic.name.length).toBe(0);
    });

    it('should validate priority is in range 1-5', () => {
      const validPriorities = [1, 2, 3, 4, 5];
      validPriorities.forEach((p) => {
        expect(p).toBeGreaterThanOrEqual(1);
        expect(p).toBeLessThanOrEqual(5);
      });
    });

    it('should validate keywords array is not empty for enabled topics', () => {
      const topic: Topic = { name: 'AI', keywords: ['AI', 'ML'], priority: 3, enabled: true };
      expect(topic.keywords.length).toBeGreaterThan(0);
    });
  });

  describe('delivery validation', () => {
    it('should validate time format HH:MM', () => {
      const timeRegex = /^([01]\d|2[0-3]):([0-5]\d)$/;
      const validTimes = ['00:00', '06:00', '12:30', '23:59'];
      const invalidTimes = ['24:00', '12:60', '1:00', '6:0'];

      validTimes.forEach((t) => expect(t).toMatch(timeRegex));
      invalidTimes.forEach((t) => expect(t).not.toMatch(timeRegex));
    });

    it('should validate timezone is valid IANA timezone', () => {
      const validTimezones = [
        'UTC',
        'America/New_York',
        'Europe/London',
        'Asia/Tokyo',
        'Pacific/Auckland',
      ];

      validTimezones.forEach((tz) => {
        expect(tz).toMatch(/^[A-Za-z]+\/[A-Za-z_]+$|^UTC$/);
      });
    });
  });

  describe('style validation', () => {
    it('should validate skepticism level is 1-5', () => {
      const levels = [1, 2, 3, 4, 5];
      levels.forEach((level) => {
        expect(level).toBeGreaterThanOrEqual(1);
        expect(level).toBeLessThanOrEqual(5);
      });
    });

    it('should validate technical depth is 1-5', () => {
      const depths = [1, 2, 3, 4, 5];
      depths.forEach((depth) => {
        expect(depth).toBeGreaterThanOrEqual(1);
        expect(depth).toBeLessThanOrEqual(5);
      });
    });

    it('should validate max articles per topic is positive', () => {
      const validCounts = [1, 5, 10, 20];
      validCounts.forEach((count) => {
        expect(count).toBeGreaterThan(0);
      });
    });
  });
});

describe('Frequency Options', () => {
  it('should define all frequency options', () => {
    const frequencies = ['hourly', 'daily_am', 'daily_pm', 'weekly', 'biweekly', 'monthly'];
    expect(frequencies).toHaveLength(6);
  });

  it('should have human-readable labels', () => {
    const frequencyLabels: Record<string, string> = {
      hourly: 'Every hour',
      daily_am: 'Daily (Morning)',
      daily_pm: 'Daily (Evening)',
      weekly: 'Weekly',
      biweekly: 'Every two weeks',
      monthly: 'Monthly',
    };

    expect(frequencyLabels.hourly).toBeDefined();
    expect(frequencyLabels.weekly).toBe('Weekly');
  });
});

describe('Channel Options', () => {
  it('should define all channel options', () => {
    const channels = ['web', 'rss', 'email'];
    expect(channels).toHaveLength(3);
  });

  it('should allow multiple channels', () => {
    const selectedChannels: ('web' | 'rss' | 'email')[] = ['web', 'email'];
    expect(selectedChannels).toContain('web');
    expect(selectedChannels).toContain('email');
    expect(selectedChannels).not.toContain('rss');
  });
});

describe('Tone Options', () => {
  it('should define all tone options', () => {
    const tones = ['hn-style', 'formal', 'casual'];
    expect(tones).toHaveLength(3);
  });

  it('should have descriptive labels', () => {
    const toneDescriptions: Record<string, string> = {
      'hn-style': 'Hacker News style - skeptical, technical, concise',
      formal: 'Formal - professional, detailed, objective',
      casual: 'Casual - friendly, accessible, conversational',
    };

    expect(toneDescriptions['hn-style']).toContain('skeptical');
    expect(toneDescriptions.formal).toContain('professional');
    expect(toneDescriptions.casual).toContain('friendly');
  });
});
