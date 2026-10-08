/**
 * Central API Client and Mock/Live Mode Abstraction.
 *
 * This is the SINGLE SOURCE OF TRUTH for API mode switching.
 * Application components and pages must NEVER check VITE_API_MODE directly;
 * they consume domain service functions that dispatch transparently.
 */
import { getApiBaseUrl, getApiMode } from './config';

export class ApiError extends Error {
  public readonly statusCode: number;
  public readonly endpoint: string;
  public readonly details?: unknown;

  constructor(message: string, statusCode: number, endpoint: string, details?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.statusCode = statusCode;
    this.endpoint = endpoint;
    this.details = details;
  }
}

/**
 * Returns true if the frontend is running against local mock fixtures.
 */
export function isMockMode(): boolean {
  return getApiMode() === 'mock';
}

/**
 * Executes a typed HTTP request against the live backend API.
 */
async function liveRequest<T>(
  method: 'GET' | 'POST' | 'PUT' | 'DELETE',
  endpoint: string,
  params?: Record<string, string | number | boolean | undefined | null>,
  body?: unknown,
): Promise<T> {
  const baseUrl = getApiBaseUrl().replace(/\/$/, '');
  let url = `${baseUrl}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;

  if (params) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        searchParams.append(key, String(value));
      }
    });
    const queryString = searchParams.toString();
    if (queryString) {
      url += `?${queryString}`;
    }
  }

  const headers: Record<string, string> = {
    Accept: 'application/json',
  };
  if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
  }

  let response: Response;
  try {
    response = await fetch(url, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch (error) {
    throw new ApiError(
      `Network connection failed when requesting ${endpoint}: ${error instanceof Error ? error.message : 'Unknown error'}`,
      0,
      endpoint,
      error,
    );
  }

  if (!response.ok) {
    let errorDetails: unknown;
    let message = `API request failed with status ${response.status} (${response.statusText})`;
    try {
      errorDetails = await response.json();
      if (typeof errorDetails === 'object' && errorDetails !== null && 'message' in errorDetails) {
        message = String((errorDetails as { message: unknown }).message);
      }
    } catch {
      // Body not JSON
    }
    throw new ApiError(message, response.status, endpoint, errorDetails);
  }

  try {
    return (await response.json()) as T;
  } catch (error) {
    throw new ApiError(`Failed to parse JSON response from ${endpoint}`, response.status, endpoint, error);
  }
}

export const liveApi = {
  get: <T>(endpoint: string, params?: Record<string, string | number | boolean | undefined | null>) =>
    liveRequest<T>('GET', endpoint, params),
  post: <T>(endpoint: string, body?: unknown) => liveRequest<T>('POST', endpoint, undefined, body),
};
