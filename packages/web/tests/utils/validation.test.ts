/**
 * Tests for validation utilities.
 */

import { describe, it, expect } from 'vitest';

// Validation functions
const isValidEmail = (email: string): boolean => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
};

const isValidPassword = (password: string): { valid: boolean; errors: string[] } => {
  const errors: string[] = [];

  if (password.length < 8) {
    errors.push('Password must be at least 8 characters');
  }
  if (!/[A-Z]/.test(password)) {
    errors.push('Password must contain an uppercase letter');
  }
  if (!/[a-z]/.test(password)) {
    errors.push('Password must contain a lowercase letter');
  }
  if (!/[0-9]/.test(password)) {
    errors.push('Password must contain a number');
  }

  return { valid: errors.length === 0, errors };
};

const isValidUrl = (url: string): boolean => {
  try {
    new URL(url);
    return true;
  } catch {
    return false;
  }
};

const isValidTime = (time: string): boolean => {
  const timeRegex = /^([01]\d|2[0-3]):([0-5]\d)$/;
  return timeRegex.test(time);
};

const isValidTimezone = (timezone: string): boolean => {
  try {
    Intl.DateTimeFormat(undefined, { timeZone: timezone });
    return true;
  } catch {
    return false;
  }
};

const isValidPriority = (priority: number): boolean => {
  return Number.isInteger(priority) && priority >= 1 && priority <= 5;
};

const isValidSkepticism = (level: number): boolean => {
  return Number.isInteger(level) && level >= 1 && level <= 5;
};

const isValidTechnicalDepth = (depth: number): boolean => {
  return Number.isInteger(depth) && depth >= 1 && depth <= 5;
};

const isNonEmptyString = (value: unknown): value is string => {
  return typeof value === 'string' && value.trim().length > 0;
};

const isValidTopicName = (name: string): { valid: boolean; error?: string } => {
  if (!isNonEmptyString(name)) {
    return { valid: false, error: 'Topic name is required' };
  }
  if (name.length > 50) {
    return { valid: false, error: 'Topic name must be 50 characters or less' };
  }
  if (!/^[a-zA-Z0-9\s&-]+$/.test(name)) {
    return { valid: false, error: 'Topic name contains invalid characters' };
  }
  return { valid: true };
};

const isValidKeywordList = (keywords: string[]): { valid: boolean; error?: string } => {
  if (!Array.isArray(keywords)) {
    return { valid: false, error: 'Keywords must be an array' };
  }
  if (keywords.length === 0) {
    return { valid: false, error: 'At least one keyword is required' };
  }
  if (keywords.length > 20) {
    return { valid: false, error: 'Maximum 20 keywords allowed' };
  }
  for (const keyword of keywords) {
    if (!isNonEmptyString(keyword)) {
      return { valid: false, error: 'Keywords cannot be empty' };
    }
    if (keyword.length > 100) {
      return { valid: false, error: 'Keywords must be 100 characters or less' };
    }
  }
  return { valid: true };
};

describe('Email Validation', () => {
  describe('valid emails', () => {
    const validEmails = [
      'test@example.com',
      'user.name@domain.org',
      'user+tag@example.co.uk',
      'firstname.lastname@subdomain.domain.com',
      'email@123.123.123.123',
      'a@b.io',
      'test123@test.com',
    ];

    validEmails.forEach((email) => {
      it(`should accept "${email}"`, () => {
        expect(isValidEmail(email)).toBe(true);
      });
    });
  });

  describe('invalid emails', () => {
    const invalidEmails = [
      'notanemail',
      '@nodomain.com',
      'missing@',
      'spaces in@email.com',
      'double@@at.com',
      '.startswithdot@domain.com',
      'endswithdot.@domain.com',
      'no@tld',
      '',
      '  ',
    ];

    invalidEmails.forEach((email) => {
      it(`should reject "${email || '(empty)'}"`, () => {
        expect(isValidEmail(email)).toBe(false);
      });
    });
  });
});

describe('Password Validation', () => {
  describe('valid passwords', () => {
    const validPasswords = ['Password1', 'SecurePass123', 'MyP@ssw0rd', 'Abcdefg1'];

    validPasswords.forEach((password) => {
      it(`should accept "${password}"`, () => {
        const result = isValidPassword(password);
        expect(result.valid).toBe(true);
        expect(result.errors).toHaveLength(0);
      });
    });
  });

  describe('invalid passwords', () => {
    it('should reject short password', () => {
      const result = isValidPassword('Short1');
      expect(result.valid).toBe(false);
      expect(result.errors).toContain('Password must be at least 8 characters');
    });

    it('should reject password without uppercase', () => {
      const result = isValidPassword('lowercase123');
      expect(result.valid).toBe(false);
      expect(result.errors).toContain('Password must contain an uppercase letter');
    });

    it('should reject password without lowercase', () => {
      const result = isValidPassword('UPPERCASE123');
      expect(result.valid).toBe(false);
      expect(result.errors).toContain('Password must contain a lowercase letter');
    });

    it('should reject password without number', () => {
      const result = isValidPassword('NoNumbers');
      expect(result.valid).toBe(false);
      expect(result.errors).toContain('Password must contain a number');
    });

    it('should accumulate multiple errors', () => {
      const result = isValidPassword('bad');
      expect(result.valid).toBe(false);
      expect(result.errors.length).toBeGreaterThan(1);
    });
  });
});

describe('URL Validation', () => {
  describe('valid URLs', () => {
    const validUrls = [
      'https://example.com',
      'http://example.com',
      'https://www.example.com/path',
      'https://example.com/path?query=value',
      'https://example.com:8080/path',
      'https://subdomain.example.com',
      'ftp://files.example.com',
    ];

    validUrls.forEach((url) => {
      it(`should accept "${url}"`, () => {
        expect(isValidUrl(url)).toBe(true);
      });
    });
  });

  describe('invalid URLs', () => {
    const invalidUrls = [
      'not-a-url',
      'example.com',
      '//missing-protocol.com',
      'http:/missing-slash.com',
      '',
      'javascript:alert(1)',
    ];

    invalidUrls.forEach((url) => {
      it(`should reject "${url || '(empty)'}"`, () => {
        expect(isValidUrl(url)).toBe(false);
      });
    });
  });
});

describe('Time Validation', () => {
  describe('valid times', () => {
    const validTimes = ['00:00', '06:30', '12:00', '18:45', '23:59'];

    validTimes.forEach((time) => {
      it(`should accept "${time}"`, () => {
        expect(isValidTime(time)).toBe(true);
      });
    });
  });

  describe('invalid times', () => {
    const invalidTimes = ['24:00', '12:60', '1:00', '12:0', '12:00:00', '', 'noon', '12 PM'];

    invalidTimes.forEach((time) => {
      it(`should reject "${time || '(empty)'}"`, () => {
        expect(isValidTime(time)).toBe(false);
      });
    });
  });
});

describe('Timezone Validation', () => {
  describe('valid timezones', () => {
    const validTimezones = [
      'UTC',
      'America/New_York',
      'America/Los_Angeles',
      'Europe/London',
      'Europe/Paris',
      'Asia/Tokyo',
      'Australia/Sydney',
      'Pacific/Auckland',
    ];

    validTimezones.forEach((tz) => {
      it(`should accept "${tz}"`, () => {
        expect(isValidTimezone(tz)).toBe(true);
      });
    });
  });

  describe('invalid timezones', () => {
    const invalidTimezones = ['NotATimezone', 'EST', 'PST', 'GMT+5', '', 'America/NotReal'];

    invalidTimezones.forEach((tz) => {
      it(`should reject "${tz || '(empty)'}"`, () => {
        expect(isValidTimezone(tz)).toBe(false);
      });
    });
  });
});

describe('Priority Validation', () => {
  describe('valid priorities', () => {
    [1, 2, 3, 4, 5].forEach((priority) => {
      it(`should accept ${priority}`, () => {
        expect(isValidPriority(priority)).toBe(true);
      });
    });
  });

  describe('invalid priorities', () => {
    [0, 6, -1, 1.5, 3.7, NaN, Infinity].forEach((priority) => {
      it(`should reject ${priority}`, () => {
        expect(isValidPriority(priority)).toBe(false);
      });
    });
  });
});

describe('Skepticism Level Validation', () => {
  describe('valid levels', () => {
    [1, 2, 3, 4, 5].forEach((level) => {
      it(`should accept ${level}`, () => {
        expect(isValidSkepticism(level)).toBe(true);
      });
    });
  });

  describe('invalid levels', () => {
    [0, 6, -1, 2.5, NaN].forEach((level) => {
      it(`should reject ${level}`, () => {
        expect(isValidSkepticism(level)).toBe(false);
      });
    });
  });
});

describe('Technical Depth Validation', () => {
  describe('valid depths', () => {
    [1, 2, 3, 4, 5].forEach((depth) => {
      it(`should accept ${depth}`, () => {
        expect(isValidTechnicalDepth(depth)).toBe(true);
      });
    });
  });

  describe('invalid depths', () => {
    [0, 6, -1, 4.5, NaN].forEach((depth) => {
      it(`should reject ${depth}`, () => {
        expect(isValidTechnicalDepth(depth)).toBe(false);
      });
    });
  });
});

describe('Non-Empty String Validation', () => {
  describe('valid strings', () => {
    const validStrings = ['hello', 'a', '  spaces trimmed  ', '123'];

    validStrings.forEach((str) => {
      it(`should accept "${str}"`, () => {
        expect(isNonEmptyString(str)).toBe(true);
      });
    });
  });

  describe('invalid values', () => {
    const invalidValues = ['', '   ', null, undefined, 123, {}, []];

    invalidValues.forEach((value) => {
      it(`should reject ${JSON.stringify(value)}`, () => {
        expect(isNonEmptyString(value)).toBe(false);
      });
    });
  });
});

describe('Topic Name Validation', () => {
  describe('valid topic names', () => {
    const validNames = ['AI', 'Machine Learning', 'Web Development', 'Science & Technology', 'AI-ML'];

    validNames.forEach((name) => {
      it(`should accept "${name}"`, () => {
        const result = isValidTopicName(name);
        expect(result.valid).toBe(true);
        expect(result.error).toBeUndefined();
      });
    });
  });

  describe('invalid topic names', () => {
    it('should reject empty name', () => {
      const result = isValidTopicName('');
      expect(result.valid).toBe(false);
      expect(result.error).toBe('Topic name is required');
    });

    it('should reject whitespace-only name', () => {
      const result = isValidTopicName('   ');
      expect(result.valid).toBe(false);
      expect(result.error).toBe('Topic name is required');
    });

    it('should reject long name', () => {
      const result = isValidTopicName('A'.repeat(51));
      expect(result.valid).toBe(false);
      expect(result.error).toBe('Topic name must be 50 characters or less');
    });

    it('should reject special characters', () => {
      const result = isValidTopicName('AI@ML!');
      expect(result.valid).toBe(false);
      expect(result.error).toBe('Topic name contains invalid characters');
    });
  });
});

describe('Keyword List Validation', () => {
  describe('valid keyword lists', () => {
    it('should accept single keyword', () => {
      const result = isValidKeywordList(['AI']);
      expect(result.valid).toBe(true);
    });

    it('should accept multiple keywords', () => {
      const result = isValidKeywordList(['AI', 'Machine Learning', 'Deep Learning']);
      expect(result.valid).toBe(true);
    });

    it('should accept up to 20 keywords', () => {
      const keywords = Array.from({ length: 20 }, (_, i) => `keyword${i}`);
      const result = isValidKeywordList(keywords);
      expect(result.valid).toBe(true);
    });
  });

  describe('invalid keyword lists', () => {
    it('should reject empty array', () => {
      const result = isValidKeywordList([]);
      expect(result.valid).toBe(false);
      expect(result.error).toBe('At least one keyword is required');
    });

    it('should reject more than 20 keywords', () => {
      const keywords = Array.from({ length: 21 }, (_, i) => `keyword${i}`);
      const result = isValidKeywordList(keywords);
      expect(result.valid).toBe(false);
      expect(result.error).toBe('Maximum 20 keywords allowed');
    });

    it('should reject empty keyword', () => {
      const result = isValidKeywordList(['AI', '']);
      expect(result.valid).toBe(false);
      expect(result.error).toBe('Keywords cannot be empty');
    });

    it('should reject long keyword', () => {
      const result = isValidKeywordList(['A'.repeat(101)]);
      expect(result.valid).toBe(false);
      expect(result.error).toBe('Keywords must be 100 characters or less');
    });
  });
});

describe('Form Validation', () => {
  interface FormErrors {
    [key: string]: string | undefined;
  }

  const validateLoginForm = (data: { email: string; password: string }): FormErrors => {
    const errors: FormErrors = {};

    if (!isNonEmptyString(data.email)) {
      errors.email = 'Email is required';
    } else if (!isValidEmail(data.email)) {
      errors.email = 'Invalid email format';
    }

    if (!isNonEmptyString(data.password)) {
      errors.password = 'Password is required';
    }

    return errors;
  };

  it('should validate valid login form', () => {
    const errors = validateLoginForm({ email: 'test@example.com', password: 'password123' });
    expect(Object.keys(errors)).toHaveLength(0);
  });

  it('should require email', () => {
    const errors = validateLoginForm({ email: '', password: 'password123' });
    expect(errors.email).toBe('Email is required');
  });

  it('should validate email format', () => {
    const errors = validateLoginForm({ email: 'invalid', password: 'password123' });
    expect(errors.email).toBe('Invalid email format');
  });

  it('should require password', () => {
    const errors = validateLoginForm({ email: 'test@example.com', password: '' });
    expect(errors.password).toBe('Password is required');
  });

  it('should accumulate multiple errors', () => {
    const errors = validateLoginForm({ email: '', password: '' });
    expect(errors.email).toBeDefined();
    expect(errors.password).toBeDefined();
  });
});

describe('Article Quality Score Validation', () => {
  const isValidQualityScore = (score: number): boolean => {
    return typeof score === 'number' && !isNaN(score) && score >= 0 && score <= 1;
  };

  describe('valid scores', () => {
    [0, 0.25, 0.5, 0.75, 1].forEach((score) => {
      it(`should accept ${score}`, () => {
        expect(isValidQualityScore(score)).toBe(true);
      });
    });
  });

  describe('invalid scores', () => {
    [-0.1, 1.1, NaN, Infinity, -Infinity].forEach((score) => {
      it(`should reject ${score}`, () => {
        expect(isValidQualityScore(score)).toBe(false);
      });
    });
  });
});

describe('Bias Direction Validation', () => {
  const validDirections = ['left', 'center-left', 'center', 'center-right', 'right'];

  const isValidBiasDirection = (direction: string): boolean => {
    return validDirections.includes(direction);
  };

  describe('valid directions', () => {
    validDirections.forEach((direction) => {
      it(`should accept "${direction}"`, () => {
        expect(isValidBiasDirection(direction)).toBe(true);
      });
    });
  });

  describe('invalid directions', () => {
    ['LEFT', 'neutral', 'far-left', '', 'unknown'].forEach((direction) => {
      it(`should reject "${direction || '(empty)'}"`, () => {
        expect(isValidBiasDirection(direction)).toBe(false);
      });
    });
  });
});
