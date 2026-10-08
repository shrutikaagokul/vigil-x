/**
 * Currency formatting utility preserving backend currency standards (Rupees / INR).
 */

export type CurrencyFormatMode = 'full' | 'compact';

export function formatCurrency(amount?: number | null, mode: CurrencyFormatMode = 'full'): string {
  if (amount == null || isNaN(amount)) {
    return '—';
  }

  if (mode === 'compact') {
    const abs = Math.abs(amount);
    const sign = amount < 0 ? '-' : '';

    if (abs >= 1e6) {
      const m = (abs / 1e6).toFixed(1).replace(/\.0$/, '');
      return `${sign}₹${m}M`;
    }
    if (abs >= 1e3) {
      const k = (abs / 1e3).toFixed(1).replace(/\.0$/, '');
      return `${sign}₹${k}k`;
    }
    return `${sign}₹${Math.round(abs).toLocaleString('en-IN')}`;
  }

  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(amount);
}

// Backward compatibility alias
export const formatINR = formatCurrency;

export function formatExposureRange(low?: number | null, high?: number | null): string {
  if (low == null && high == null) return '—';
  if (low != null && high != null && low !== high) {
    return `${formatCurrency(low, 'compact')} – ${formatCurrency(high, 'compact')}`;
  }
  const val = high ?? low;
  return val != null ? formatCurrency(val, 'compact') : '—';
}
