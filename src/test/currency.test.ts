import { describe, it, expect } from 'vitest';
import {
  formatCurrency,
  formatUSD,
  formatINR,
  formatExposureRange,
} from '@/utils/currency';

describe('VIGILX Currency Formatter (USD / $)', () => {
  describe('formatCurrency full mode', () => {
    it('formats whole dollar amounts with comma grouping and dollar sign', () => {
      expect(formatCurrency(932000)).toBe('$932,000');
      expect(formatCurrency(255096)).toBe('$255,096');
      expect(formatCurrency(150)).toBe('$150');
      expect(formatCurrency(0)).toBe('$0');
    });

    it('formats fractional cents when fraction digits specified', () => {
      expect(
        formatCurrency(150.25, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
      ).toBe('$150.25');
      expect(
        formatCurrency(820, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
      ).toBe('$820.00');
    });

    it('handles negative numbers properly', () => {
      expect(formatCurrency(-5000)).toBe('-$5,000');
    });

    it('returns em-dash for null, undefined, or NaN inputs without throwing', () => {
      expect(formatCurrency(null)).toBe('—');
      expect(formatCurrency(undefined)).toBe('—');
      expect(formatCurrency(NaN)).toBe('—');
    });

    it('preserves numerical magnitude without conversion', () => {
      // 100,000 USD must stay 100,000 USD (never converted by exchange rate)
      const input = 100000;
      expect(formatCurrency(input)).toBe('$100,000');
    });
  });

  describe('formatCurrency US compact notation ($1K, $1M, $20M)', () => {
    it('formats thousand-scale amounts with $...K', () => {
      expect(formatCurrency(1000, 'compact')).toBe('$1K');
      expect(formatCurrency(2500, 'compact')).toBe('$2.5K');
      expect(formatCurrency(50000, 'compact')).toBe('$50K');
      expect(formatCurrency(184200, 'compact')).toBe('$184.2K');
    });

    it('formats million-scale amounts with $...M', () => {
      expect(formatCurrency(1000000, 'compact')).toBe('$1M');
      expect(formatCurrency(20000000, 'compact')).toBe('$20M');
      expect(formatCurrency(1500000, 'compact')).toBe('$1.5M');
    });

    it('formats sub-thousand amounts with exact dollars', () => {
      expect(formatCurrency(500, 'compact')).toBe('$500');
      expect(formatCurrency(75, 'compact')).toBe('$75');
      expect(formatCurrency(0, 'compact')).toBe('$0');
    });

    it('handles negative compact amounts', () => {
      expect(formatCurrency(-1500, 'compact')).toBe('-$1.5K');
      expect(formatCurrency(-2000000, 'compact')).toBe('-$2M');
    });
  });

  describe('formatExposureRange', () => {
    it('formats ranges using compact USD representation', () => {
      expect(formatExposureRange(1000, 5000)).toBe('$1K – $5K');
      expect(formatExposureRange(1000000, 20000000)).toBe('$1M – $20M');
      expect(formatExposureRange(50000, 120000)).toBe('$50K – $120K');
    });

    it('collapses identical low and high values into single amount', () => {
      expect(formatExposureRange(5000, 5000)).toBe('$5K');
    });

    it('handles single-bound or null ranges gracefully', () => {
      expect(formatExposureRange(null, 5000)).toBe('$5K');
      expect(formatExposureRange(10000, null)).toBe('$10K');
      expect(formatExposureRange(null, null)).toBe('—');
    });
  });

  describe('Aliases formatUSD and formatINR', () => {
    it('formatUSD matches formatCurrency exactly', () => {
      expect(formatUSD(12500)).toBe('$12,500');
      expect(formatUSD(1000000, 'compact')).toBe('$1M');
    });

    it('formatINR acts as a safe alias routing to USD presentation without crashing legacy callers', () => {
      expect(formatINR(12500)).toBe('$12,500');
      expect(formatINR(20000000, 'compact')).toBe('$20M');
    });
  });
});
