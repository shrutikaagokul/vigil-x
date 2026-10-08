import '@testing-library/jest-dom';

// Mock ResizeObserver for Radix UI primitives
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

// Mock HTMLCanvasElement getContext for Cytoscape.js in jsdom
if (typeof HTMLCanvasElement !== 'undefined') {
  (HTMLCanvasElement.prototype as any).getContext = () => {
    const dummyContext: Record<string, unknown> = {
      measureText: () => ({ width: 0 }),
      getImageData: () => ({ data: [] }),
      createImageData: () => [],
      getLineDash: () => [],
      setLineDash: () => {},
    };

    return new Proxy(dummyContext, {
      get(target, prop) {
        if (prop in target) {
          return target[prop as string];
        }
        return () => {};
      },
      set(target, prop, value) {
        target[prop as string] = value;
        return true;
      },
    });
  };
}
