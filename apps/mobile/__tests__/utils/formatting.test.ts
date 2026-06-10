import {
  formatDate,
  formatTime,
  formatDuration,
  formatBytes,
  formatPercentage,
  formatNumber,
  truncateString,
  capitalizeFirstLetter,
  formatStatus,
} from '@utils/formatting';

describe('Formatting Utilities', () => {
  describe('formatDate', () => {
    it('should format date correctly', () => {
      const date = new Date('2024-06-09');
      const formatted = formatDate(date, 'YYYY-MM-DD');
      expect(formatted).toBe('2024-06-09');
    });
  });

  describe('formatDuration', () => {
    it('should format seconds', () => {
      expect(formatDuration(30)).toBe('30s');
      expect(formatDuration(45)).toBe('45s');
    });

    it('should format minutes and seconds', () => {
      expect(formatDuration(75)).toBe('1m 15s');
      expect(formatDuration(150)).toBe('2m 30s');
    });

    it('should format hours and minutes', () => {
      expect(formatDuration(3661)).toBe('1h 1m');
      expect(formatDuration(7322)).toBe('2h 2m');
    });
  });

  describe('formatBytes', () => {
    it('should format bytes correctly', () => {
      expect(formatBytes(0)).toBe('0 Bytes');
      expect(formatBytes(1024)).toBe('1 KB');
      expect(formatBytes(1024 * 1024)).toBe('1 MB');
    });
  });

  describe('formatPercentage', () => {
    it('should format percentage correctly', () => {
      expect(formatPercentage(0.5)).toBe('50.0%');
      expect(formatPercentage(0.75, 2)).toBe('75.00%');
    });
  });

  describe('formatNumber', () => {
    it('should format numbers with thousands separator', () => {
      expect(formatNumber(1000)).toBe('1,000');
      expect(formatNumber(1000000)).toBe('1,000,000');
    });
  });

  describe('truncateString', () => {
    it('should truncate long strings', () => {
      expect(truncateString('This is a long string', 10)).toBe('This is...');
      expect(truncateString('Short', 10)).toBe('Short');
    });
  });

  describe('capitalizeFirstLetter', () => {
    it('should capitalize first letter', () => {
      expect(capitalizeFirstLetter('hello')).toBe('Hello');
      expect(capitalizeFirstLetter('HELLO')).toBe('HELLO');
    });
  });

  describe('formatStatus', () => {
    it('should format status strings', () => {
      expect(formatStatus('test_case')).toBe('Test Case');
      expect(formatStatus('in_progress')).toBe('In Progress');
    });
  });
});
