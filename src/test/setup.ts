import '@testing-library/jest-dom';

// Mock ResizeObserver for Radix UI primitives
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};
