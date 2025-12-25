/**
 * Tests for formatting utilities.
 */

import { describe, it, expect } from 'vitest';

// Utility functions to test
const formatDate = (date: Date | string, options?: Intl.DateTimeFormatOptions): string => {
  const d = typeof date === 'string' ? new Date(date) : date;
  return new Intl.DateTimeFormat('en-US', options).format(d);
};

const formatRelativeTime = (date: Date | string): string => {
  const d = typeof date === 'string' ? new Date(date) : date;
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffSecs = Math.floor(diffMs / 1000);
  const diffMins = Math.floor(diffSecs / 60);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSecs < 60) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return formatDate(d, { month: 'short', day: 'numeric' });
};

const formatNumber = (num: number, options?: Intl.NumberFormatOptions): string => {
  return new Intl.NumberFormat('en-US', options).format(num);
};

const formatCompactNumber = (num: number): string => {
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
  if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
  return num.toString();
};

const formatPercentage = (value: number, decimals = 0): string => {
  return `${(value * 100).toFixed(decimals)}%`;
};

const formatDuration = (seconds: number): string => {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
  const hours = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  return `${hours}h ${mins}m`;
};

const truncateText = (text: string, maxLength: number, suffix = '...'): string => {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength - suffix.length) + suffix;
};

const slugify = (text: string): string => {
  return text
    .toLowerCase()
    .replace(/[^\w\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .trim();
};

const capitalize = (text: string): string => {
  return text.charAt(0).toUpperCase() + text.slice(1).toLowerCase();
};

const titleCase = (text: string): string => {
  return text
    .split(' ')
    .map((word) => capitalize(word))
    .join(' ');
};

describe('Date Formatting', () => {
  describe('formatDate', () => {
    it('should format date with default options', () => {
      const date = new Date('2025-01-15T10:30:00Z');
      const formatted = formatDate(date);
      expect(formatted).toContain('15');
    });

    it('should format date with custom options', () => {
      const date = new Date('2025-06-20T14:00:00Z');
      const formatted = formatDate(date, {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      });
      expect(formatted).toContain('2025');
      expect(formatted).toContain('June');
    });

    it('should accept date string', () => {
      const formatted = formatDate('2025-01-15T10:30:00Z');
      expect(formatted).toBeDefined();
    });

    it('should format with short month', () => {
      const date = new Date('2025-12-25T00:00:00Z');
      const formatted = formatDate(date, { month: 'short', day: 'numeric' });
      expect(formatted).toContain('Dec');
    });
  });

  describe('formatRelativeTime', () => {
    it('should return "just now" for recent times', () => {
      const now = new Date();
      const result = formatRelativeTime(now);
      expect(result).toBe('just now');
    });

    it('should return minutes ago', () => {
      const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000);
      const result = formatRelativeTime(fiveMinutesAgo);
      expect(result).toBe('5m ago');
    });

    it('should return hours ago', () => {
      const threeHoursAgo = new Date(Date.now() - 3 * 60 * 60 * 1000);
      const result = formatRelativeTime(threeHoursAgo);
      expect(result).toBe('3h ago');
    });

    it('should return days ago', () => {
      const twoDaysAgo = new Date(Date.now() - 2 * 24 * 60 * 60 * 1000);
      const result = formatRelativeTime(twoDaysAgo);
      expect(result).toBe('2d ago');
    });

    it('should return formatted date for old dates', () => {
      const tenDaysAgo = new Date(Date.now() - 10 * 24 * 60 * 60 * 1000);
      const result = formatRelativeTime(tenDaysAgo);
      expect(result).not.toContain('ago');
    });
  });
});

describe('Number Formatting', () => {
  describe('formatNumber', () => {
    it('should format integer', () => {
      expect(formatNumber(1234)).toBe('1,234');
    });

    it('should format decimal', () => {
      expect(formatNumber(1234.56)).toBe('1,234.56');
    });

    it('should format with currency', () => {
      const result = formatNumber(99.99, { style: 'currency', currency: 'USD' });
      expect(result).toContain('$');
      expect(result).toContain('99.99');
    });

    it('should format large numbers', () => {
      expect(formatNumber(1000000)).toBe('1,000,000');
    });

    it('should format negative numbers', () => {
      expect(formatNumber(-500)).toBe('-500');
    });
  });

  describe('formatCompactNumber', () => {
    it('should return number as-is for small values', () => {
      expect(formatCompactNumber(500)).toBe('500');
    });

    it('should format thousands with K', () => {
      expect(formatCompactNumber(1500)).toBe('1.5K');
      expect(formatCompactNumber(10000)).toBe('10.0K');
    });

    it('should format millions with M', () => {
      expect(formatCompactNumber(1500000)).toBe('1.5M');
      expect(formatCompactNumber(10000000)).toBe('10.0M');
    });

    it('should handle edge cases', () => {
      expect(formatCompactNumber(999)).toBe('999');
      expect(formatCompactNumber(1000)).toBe('1.0K');
      expect(formatCompactNumber(999999)).toBe('1000.0K');
      expect(formatCompactNumber(1000000)).toBe('1.0M');
    });
  });

  describe('formatPercentage', () => {
    it('should format decimal to percentage', () => {
      expect(formatPercentage(0.5)).toBe('50%');
      expect(formatPercentage(0.75)).toBe('75%');
      expect(formatPercentage(1)).toBe('100%');
    });

    it('should format with decimals', () => {
      expect(formatPercentage(0.756, 1)).toBe('75.6%');
      expect(formatPercentage(0.7567, 2)).toBe('75.67%');
    });

    it('should handle small percentages', () => {
      expect(formatPercentage(0.01)).toBe('1%');
      expect(formatPercentage(0.001, 1)).toBe('0.1%');
    });

    it('should handle values over 100%', () => {
      expect(formatPercentage(1.5)).toBe('150%');
    });
  });
});

describe('Duration Formatting', () => {
  describe('formatDuration', () => {
    it('should format seconds', () => {
      expect(formatDuration(30)).toBe('30s');
      expect(formatDuration(59)).toBe('59s');
    });

    it('should format minutes and seconds', () => {
      expect(formatDuration(60)).toBe('1m 0s');
      expect(formatDuration(90)).toBe('1m 30s');
      expect(formatDuration(3599)).toBe('59m 59s');
    });

    it('should format hours and minutes', () => {
      expect(formatDuration(3600)).toBe('1h 0m');
      expect(formatDuration(5400)).toBe('1h 30m');
      expect(formatDuration(7200)).toBe('2h 0m');
    });

    it('should handle zero', () => {
      expect(formatDuration(0)).toBe('0s');
    });
  });
});

describe('Text Formatting', () => {
  describe('truncateText', () => {
    it('should not truncate short text', () => {
      expect(truncateText('Hello', 10)).toBe('Hello');
    });

    it('should truncate long text with ellipsis', () => {
      expect(truncateText('Hello World', 8)).toBe('Hello...');
    });

    it('should use custom suffix', () => {
      expect(truncateText('Hello World', 9, ' [more]')).toBe('He [more]');
    });

    it('should handle exact length', () => {
      expect(truncateText('Hello', 5)).toBe('Hello');
    });

    it('should handle empty string', () => {
      expect(truncateText('', 10)).toBe('');
    });
  });

  describe('slugify', () => {
    it('should convert to lowercase', () => {
      expect(slugify('Hello World')).toBe('hello-world');
    });

    it('should replace spaces with hyphens', () => {
      expect(slugify('This is a test')).toBe('this-is-a-test');
    });

    it('should remove special characters', () => {
      expect(slugify("Hello! What's up?")).toBe('hello-whats-up');
    });

    it('should collapse multiple hyphens', () => {
      expect(slugify('Hello   World')).toBe('hello-world');
    });

    it('should handle empty string', () => {
      expect(slugify('')).toBe('');
    });
  });

  describe('capitalize', () => {
    it('should capitalize first letter', () => {
      expect(capitalize('hello')).toBe('Hello');
    });

    it('should lowercase rest of string', () => {
      expect(capitalize('HELLO')).toBe('Hello');
    });

    it('should handle single character', () => {
      expect(capitalize('a')).toBe('A');
    });

    it('should handle empty string', () => {
      expect(capitalize('')).toBe('');
    });
  });

  describe('titleCase', () => {
    it('should capitalize each word', () => {
      expect(titleCase('hello world')).toBe('Hello World');
    });

    it('should handle all caps', () => {
      expect(titleCase('HELLO WORLD')).toBe('Hello World');
    });

    it('should handle mixed case', () => {
      expect(titleCase('heLLo WoRLd')).toBe('Hello World');
    });

    it('should handle single word', () => {
      expect(titleCase('hello')).toBe('Hello');
    });
  });
});

describe('Score Formatting', () => {
  it('should format quality scores', () => {
    const formatQualityScore = (score: number): string => {
      if (score >= 0.8) return 'Excellent';
      if (score >= 0.6) return 'Good';
      if (score >= 0.4) return 'Fair';
      return 'Poor';
    };

    expect(formatQualityScore(0.9)).toBe('Excellent');
    expect(formatQualityScore(0.7)).toBe('Good');
    expect(formatQualityScore(0.5)).toBe('Fair');
    expect(formatQualityScore(0.2)).toBe('Poor');
  });

  it('should format bias direction', () => {
    const formatBias = (direction: string): string => {
      const labels: Record<string, string> = {
        left: 'Left-leaning',
        'center-left': 'Center-left',
        center: 'Neutral',
        'center-right': 'Center-right',
        right: 'Right-leaning',
      };
      return labels[direction] || 'Unknown';
    };

    expect(formatBias('left')).toBe('Left-leaning');
    expect(formatBias('center')).toBe('Neutral');
    expect(formatBias('right')).toBe('Right-leaning');
  });

  it('should format confidence levels', () => {
    const formatConfidence = (confidence: number): string => {
      if (confidence >= 0.9) return 'Very High';
      if (confidence >= 0.7) return 'High';
      if (confidence >= 0.5) return 'Moderate';
      if (confidence >= 0.3) return 'Low';
      return 'Very Low';
    };

    expect(formatConfidence(0.95)).toBe('Very High');
    expect(formatConfidence(0.8)).toBe('High');
    expect(formatConfidence(0.6)).toBe('Moderate');
    expect(formatConfidence(0.4)).toBe('Low');
    expect(formatConfidence(0.2)).toBe('Very Low');
  });
});

describe('Array Formatting', () => {
  it('should join with comma and "and"', () => {
    const formatList = (items: string[]): string => {
      if (items.length === 0) return '';
      if (items.length === 1) return items[0];
      if (items.length === 2) return `${items[0]} and ${items[1]}`;
      return `${items.slice(0, -1).join(', ')}, and ${items[items.length - 1]}`;
    };

    expect(formatList([])).toBe('');
    expect(formatList(['Apple'])).toBe('Apple');
    expect(formatList(['Apple', 'Banana'])).toBe('Apple and Banana');
    expect(formatList(['Apple', 'Banana', 'Cherry'])).toBe('Apple, Banana, and Cherry');
  });

  it('should format keyword list', () => {
    const formatKeywords = (keywords: string[]): string => {
      return keywords.map((k) => `#${k.replace(/\s+/g, '-')}`).join(' ');
    };

    expect(formatKeywords(['AI', 'Machine Learning'])).toBe('#AI #Machine-Learning');
  });
});

describe('URL Formatting', () => {
  it('should extract domain from URL', () => {
    const extractDomain = (url: string): string => {
      try {
        const { hostname } = new URL(url);
        return hostname.replace(/^www\./, '');
      } catch {
        return url;
      }
    };

    expect(extractDomain('https://www.example.com/path')).toBe('example.com');
    expect(extractDomain('https://news.ycombinator.com')).toBe('news.ycombinator.com');
  });

  it('should format source name from domain', () => {
    const formatSourceName = (domain: string): string => {
      const known: Record<string, string> = {
        'news.ycombinator.com': 'Hacker News',
        'github.com': 'GitHub',
        'reddit.com': 'Reddit',
      };
      return known[domain] || titleCase(domain.split('.')[0]);
    };

    expect(formatSourceName('news.ycombinator.com')).toBe('Hacker News');
    expect(formatSourceName('github.com')).toBe('GitHub');
    expect(formatSourceName('techcrunch.com')).toBe('Techcrunch');
  });
});

describe('Byte Size Formatting', () => {
  it('should format file sizes', () => {
    const formatBytes = (bytes: number): string => {
      if (bytes === 0) return '0 B';
      const k = 1024;
      const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
    };

    expect(formatBytes(0)).toBe('0 B');
    expect(formatBytes(500)).toBe('500.0 B');
    expect(formatBytes(1024)).toBe('1.0 KB');
    expect(formatBytes(1048576)).toBe('1.0 MB');
    expect(formatBytes(1073741824)).toBe('1.0 GB');
  });
});
