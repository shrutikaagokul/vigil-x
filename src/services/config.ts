/**
 * Central configuration helper.
 * Provides typed runtime environment configuration to the UI and services
 * without scattering import.meta.env references across components.
 */

export type ApiMode = 'mock' | 'live';

export interface AppConfig {
  readonly apiMode: ApiMode;
  readonly apiBaseUrl: string;
  readonly isMock: boolean;
}

export function getApiMode(): ApiMode {
  const mode = import.meta.env.VITE_API_MODE;
  return mode === 'live' ? 'live' : 'mock';
}

export function getApiBaseUrl(): string {
  return import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
}

export function getAppConfig(): AppConfig {
  const apiMode = getApiMode();
  return {
    apiMode,
    apiBaseUrl: getApiBaseUrl(),
    isMock: apiMode === 'mock',
  };
}
