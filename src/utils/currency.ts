/**
 * Currency formatting utility for VIGILX USD presentation.
 */

export type CurrencyFormatMode = 'full' | 'compact';

export interface CurrencyFormatOptions {
  readonly mode?: CurrencyFormatMode;
  readonly minimumFractionDigits?: number;
  readonly maximumFractionDigits?: number;
}

export function formatCurrency(
  amount?: number | null,
  modeOrOptions: CurrencyFormatMode | CurrencyFormatOptions = 'full'
): string {
  if (amount == null || isNaN(amount)) {
    return '—';
  }

  const options: CurrencyFormatOptions =
    typeof modeOrOptions === 'string'
      ? { mode: modeOrOptions }
      : modeOrOptions;

  const mode = options.mode || 'full';

  if (mode === 'compact') {
    const abs = Math.abs(amount);
    const sign = amount < 0 ? '-' : '';

    if (abs >= 1e6) {
      const m = (abs / 1e6).toFixed(1).replace(/\.0$/, '');
      return `${sign}$${m}M`;
    }
    if (abs >= 1e3) {
      const k = (abs / 1e3).toFixed(1).replace(/\.0$/, '');
      return `${sign}$${k}K`;
    }
    return `${sign}$${Math.round(abs).toLocaleString('en-US')}`;
  }

  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: options.minimumFractionDigits ?? 0,
    maximumFractionDigits: options.maximumFractionDigits ?? 0,
  }).format(amount);
}

// Canonical USD formatter
export const formatUSD = formatCurrency;

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

