import type { Config } from 'tailwindcss';

export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        masthead: 'var(--color-masthead)',
        paper: {
          DEFAULT: 'var(--color-paper)',
          subtle: 'var(--color-paper-subtle)',
        },
        surface: {
          DEFAULT: 'var(--color-surface)',
          raised: 'var(--color-surface-raised)',
        },
        ink: {
          DEFAULT: 'var(--color-text)',
          muted: 'var(--color-text-muted)',
          subtle: 'var(--color-text-subtle)',
          inverse: 'var(--color-text-inverse)',
        },
        border: {
          DEFAULT: 'var(--color-border)',
          hairline: 'var(--color-border)',
          strong: 'var(--color-border-strong)',
        },
        green: {
          950: 'var(--color-green-950)',
          900: 'var(--color-green-900)',
          800: 'var(--color-green-800)',
          700: 'var(--color-green-700)',
          600: 'var(--color-green-600)',
          300: 'var(--color-green-300)',
          tint: 'var(--color-green-tint)',
          DEFAULT: 'var(--color-green-800)',
        },
        brass: {
          DEFAULT: 'var(--color-brass)',
          soft: 'var(--color-brass-soft)',
        },
        brick: {
          DEFAULT: 'var(--color-brick)',
          soft: 'var(--color-brick-soft)',
        },
        critical: {
          DEFAULT: 'var(--color-critical)',
          soft: 'var(--color-critical-soft)',
        },
        steel: 'var(--color-steel)',
        semantic: {
          success: 'var(--color-success)',
          warning: 'var(--color-warning)',
          danger: 'var(--color-danger)',
          info: 'var(--color-info)',
        },
      },
      fontFamily: {
        sans: ['var(--font-sans)'],
        serif: ['var(--font-serif)'],
        mono: ['var(--font-mono)'],
      },
      boxShadow: {
        none: 'none',
        subtle: 'none',
        card: 'none',
      },
      borderWidth: {
        hairline: '1px',
      },
      borderRadius: {
        none: '0px',
        sm: '2px',
        DEFAULT: '3px',
        md: '3px',
        lg: '3px',
      },
    },
  },
  plugins: [],
} satisfies Config;
