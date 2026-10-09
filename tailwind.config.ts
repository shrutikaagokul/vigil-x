import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        forest: {
          bg: '#F5F8F4',
          card: '#FFFFFF',
          elevated: '#E8F2E8',
          hover: '#F0F5F0',
          border: '#E0E8DF',
          borderSubtle: '#EDF2EC',
          borderHighlight: '#B8D2B8',
          sage: '#B8D2B8',
          primary: '#477A58',
          dark: '#285239',
          deep: '#183B2A',
          text: '#24352A',
          muted: '#68766B',
          dim: '#8B998E',
        },
        sage: {
          50: '#F5F8F4',
          100: '#E8F2E8',
          200: '#D5E6D5',
          300: '#B8D2B8',
          400: '#8FB88F',
          500: '#6B9E6B',
          600: '#477A58',
          700: '#285239',
          800: '#183B2A',
          900: '#0E2419',
        },
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
          950: '#0E2419',
          900: '#183B2A',
          800: '#285239',
          700: '#356345',
          600: '#477A58',
          500: '#5C966F',
          400: '#7CB58F',
          300: '#B8D2B8',
          200: '#D5E6D5',
          100: '#E8F2E8',
          50: '#F5F8F4',
          DEFAULT: '#477A58',
        },
        brass: {
          DEFAULT: '#B45309',
          soft: '#FEF3C7',
        },
        brick: {
          DEFAULT: '#B91C1C',
          soft: '#FEE2E2',
        },
        critical: {
          DEFAULT: '#DC2626',
          soft: '#FEE2E2',
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
};

export default config;
