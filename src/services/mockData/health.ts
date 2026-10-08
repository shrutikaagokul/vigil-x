/**
 * Mock Health fixtures.
 */
import { HealthResponse } from '@/types/api';

export const MOCK_HEALTH: HealthResponse = {
  status: 'healthy',
  version: '0.1.0',
  database: 'connected (synthetic sqlite/parquet)',
  engine: 'Vigil-X Rules Engine v1.0.0 (R06-R10 active)',
  memory_usage_mb: 248.5,
  uptime_seconds: 86400,
  timestamp: new Date().toISOString(),
};
