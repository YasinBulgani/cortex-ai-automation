import {
  validateEmail,
  validatePassword,
  validateURL,
  validatePhoneNumber,
  validateTestCaseName,
  validateDescription,
} from '@utils/validation';

describe('Validation Utilities', () => {
  describe('validateEmail', () => {
    it('should validate correct email', () => {
      expect(validateEmail('test@example.com')).toBe(true);
      expect(validateEmail('user.name+tag@example.co.uk')).toBe(true);
    });

    it('should reject invalid emails', () => {
      expect(validateEmail('invalid')).toBe(false);
      expect(validateEmail('invalid@')).toBe(false);
      expect(validateEmail('@example.com')).toBe(false);
    });
  });

  describe('validatePassword', () => {
    it('should validate strong password', () => {
      const result = validatePassword('SecurePass123');
      expect(result.valid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('should reject weak password', () => {
      const result = validatePassword('weak');
      expect(result.valid).toBe(false);
      expect(result.errors.length).toBeGreaterThan(0);
    });

    it('should require uppercase letter', () => {
      const result = validatePassword('securepass123');
      expect(result.errors).toContain('Password must contain an uppercase letter');
    });

    it('should require number', () => {
      const result = validatePassword('SecurePass');
      expect(result.errors).toContain('Password must contain a number');
    });
  });

  describe('validateURL', () => {
    it('should validate correct URLs', () => {
      expect(validateURL('https://example.com')).toBe(true);
      expect(validateURL('http://localhost:3000')).toBe(true);
      expect(validateURL('ftp://files.example.com')).toBe(true);
    });

    it('should reject invalid URLs', () => {
      expect(validateURL('not a url')).toBe(false);
      expect(validateURL('ht!tp://invalid')).toBe(false);
    });
  });

  describe('validatePhoneNumber', () => {
    it('should validate phone numbers', () => {
      expect(validatePhoneNumber('1234567890')).toBe(true);
      expect(validatePhoneNumber('123-456-7890')).toBe(true);
      expect(validatePhoneNumber('+1 (123) 456-7890')).toBe(true);
    });

    it('should reject invalid phone numbers', () => {
      expect(validatePhoneNumber('123')).toBe(false);
      expect(validatePhoneNumber('abc')).toBe(false);
    });
  });

  describe('validateTestCaseName', () => {
    it('should validate non-empty names up to 255 characters', () => {
      expect(validateTestCaseName('Valid Test Case')).toBe(true);
      expect(validateTestCaseName('a'.repeat(255))).toBe(true);
    });

    it('should reject empty names', () => {
      expect(validateTestCaseName('')).toBe(false);
      expect(validateTestCaseName('   ')).toBe(false);
    });

    it('should reject names longer than 255 characters', () => {
      expect(validateTestCaseName('a'.repeat(256))).toBe(false);
    });
  });

  describe('validateDescription', () => {
    it('should validate descriptions up to 1000 characters', () => {
      expect(validateDescription('Valid description')).toBe(true);
      expect(validateDescription('a'.repeat(1000))).toBe(true);
    });

    it('should reject descriptions longer than 1000 characters', () => {
      expect(validateDescription('a'.repeat(1001))).toBe(false);
    });
  });
});
