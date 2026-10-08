/**
 * Indian Rupee (INR) currency formatting utility.
 */

export type CurrencyFormatMode = 'full' | 'compact';

export function formatINR(amount: number, mode: CurrencyFormatMode = 'full'): string {
  if (amount == null || isNaN(amount)) {
    return '₹0';
  }

  if (mode === 'compact') {
    const abs = Math.abs(amount);
    const sign = amount < 0 ? '-' : '';

    if (abs >= 1e7) {
      const cr = (abs / 1e7).toFixed(1).replace(/\.0$/, '');
      return `${sign}₹${cr} Cr`;
    }
    if (abs >= 1e5) {
      const l = (abs / 1e5).toFixed(1).replace(/\.0$/, '');
      return `${sign}₹${l} L`;
    }
    if (abs >= 1e3) {
      const k = (abs / 1e3).toFixed(1).replace(/\.0$/, '');
      return `${sign}₹${k} k`;
    }
    return `${sign}₹${Math.round(abs).toLocaleString('en-IN')}`;
  }

  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatExposureRange(low?: number, high?: number): string {
  if (low == null && high == null) return '₹0';
  if (low != null && high != null && low !== high) {
    return `${formatINR(low, 'compact')} – ${formatINR(high, 'compact')}`;
  }
  return formatINR(high ?? low ?? 0, 'compact');
}
