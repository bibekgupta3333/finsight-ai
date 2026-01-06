/**
 * Environment Configuration
 *
 * Centralized environment variable access with validation and type safety.
 * All environment variables must be prefixed with NEXT_PUBLIC_ to be accessible in the browser.
 */

// ============================================================================
// Type-safe Environment Configuration
// ============================================================================

interface EnvironmentConfig {
  // API Configuration
  apiUrl: string;
  apiV1Prefix: string;
  wsUrl: string;
  chromadbUrl: string;

  // Feature Flags
  features: {
    batchProcessing: boolean;
    agentAnalysis: boolean;
    memorySystem: boolean;
    advancedPrompting: boolean;
    safetyChecks: boolean;
    modelRouting: boolean;
  };

  // Development Settings
  debug: boolean;
  logLevel: 'error' | 'warn' | 'info' | 'debug';
  mockApi: boolean;
  apiTimeout: number;

  // Analytics
  analytics?: {
    googleAnalyticsId?: string;
    sentryDsn?: string;
    posthogKey?: string;
    posthogHost?: string;
  };

  // Performance
  performance: {
    enableServiceWorker: boolean;
    maxItemsPerPage: number;
    maxChartPoints: number;
  };

  // UI
  ui: {
    defaultTheme: 'light' | 'dark' | 'system';
    enableThemeToggle: boolean;
  };
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Get environment variable with fallback
 */
function getEnv(key: string, fallback: string = ''): string {
  if (typeof window === 'undefined') {
    // Server-side: use process.env
    return process.env[key] || fallback;
  }
  // Client-side: use process.env (injected at build time)
  return process.env[key] || fallback;
}

/**
 * Get boolean environment variable
 */
function getBoolEnv(key: string, fallback: boolean = false): boolean {
  const value = getEnv(key, String(fallback));
  return value === 'true' || value === '1';
}

/**
 * Get number environment variable
 */
function getNumberEnv(key: string, fallback: number): number {
  const value = getEnv(key, String(fallback));
  const parsed = parseInt(value, 10);
  return isNaN(parsed) ? fallback : parsed;
}

// ============================================================================
// Environment Configuration Object
// ============================================================================

export const env: EnvironmentConfig = {
  // API Configuration
  apiUrl: getEnv('NEXT_PUBLIC_API_URL', 'http://localhost:8000'),
  apiV1Prefix: getEnv('NEXT_PUBLIC_API_V1_PREFIX', '/api/v1'),
  wsUrl: getEnv('NEXT_PUBLIC_WS_URL', 'ws://localhost:8000'),
  chromadbUrl: getEnv('NEXT_PUBLIC_CHROMADB_URL', 'http://localhost:8001'),

  // Feature Flags
  features: {
    batchProcessing: getBoolEnv('NEXT_PUBLIC_ENABLE_BATCH_PROCESSING', true),
    agentAnalysis: getBoolEnv('NEXT_PUBLIC_ENABLE_AGENT_ANALYSIS', true),
    memorySystem: getBoolEnv('NEXT_PUBLIC_ENABLE_MEMORY_SYSTEM', true),
    advancedPrompting: getBoolEnv('NEXT_PUBLIC_ENABLE_ADVANCED_PROMPTING', true),
    safetyChecks: getBoolEnv('NEXT_PUBLIC_ENABLE_SAFETY_CHECKS', true),
    modelRouting: getBoolEnv('NEXT_PUBLIC_ENABLE_MODEL_ROUTING', true),
  },

  // Development Settings
  debug: getBoolEnv('NEXT_PUBLIC_DEBUG_MODE', false),
  logLevel: (getEnv('NEXT_PUBLIC_LOG_LEVEL', 'info') as 'error' | 'warn' | 'info' | 'debug'),
  mockApi: getBoolEnv('NEXT_PUBLIC_MOCK_API', false),
  apiTimeout: getNumberEnv('NEXT_PUBLIC_API_TIMEOUT', 30000),

  // Analytics (optional)
  analytics: {
    googleAnalyticsId: getEnv('NEXT_PUBLIC_ANALYTICS_ID'),
    sentryDsn: getEnv('NEXT_PUBLIC_SENTRY_DSN'),
    posthogKey: getEnv('NEXT_PUBLIC_POSTHOG_KEY'),
    posthogHost: getEnv('NEXT_PUBLIC_POSTHOG_HOST'),
  },

  // Performance
  performance: {
    enableServiceWorker: getBoolEnv('NEXT_PUBLIC_ENABLE_SERVICE_WORKER', false),
    maxItemsPerPage: getNumberEnv('NEXT_PUBLIC_MAX_ITEMS_PER_PAGE', 50),
    maxChartPoints: getNumberEnv('NEXT_PUBLIC_MAX_CHART_POINTS', 100),
  },

  // UI
  ui: {
    defaultTheme: (getEnv('NEXT_PUBLIC_DEFAULT_THEME', 'system') as 'light' | 'dark' | 'system'),
    enableThemeToggle: getBoolEnv('NEXT_PUBLIC_ENABLE_THEME_TOGGLE', true),
  },
};

// ============================================================================
// Validation
// ============================================================================

/**
 * Validate required environment variables
 * Call this in app initialization
 */
export function validateEnv(): void {
  const required = [
    'NEXT_PUBLIC_API_URL',
  ];

  const missing = required.filter(key => !getEnv(key));

  if (missing.length > 0) {
    const error = `Missing required environment variables: ${missing.join(', ')}`;

    if (env.debug) {
      console.error(error);
      console.warn('Using fallback values for development. Configure .env.local for production.');
    }

    // Don't throw in development to allow working with defaults
    if (process.env.NODE_ENV === 'production') {
      throw new Error(error);
    }
  }
}

// ============================================================================
// API URL Helpers
// ============================================================================

/**
 * Get full API endpoint URL
 */
export function getApiUrl(path: string): string {
  const base = env.apiUrl;
  const prefix = env.apiV1Prefix;
  const cleanPath = path.startsWith('/') ? path : `/${path}`;

  // If path already includes prefix, don't add it again
  if (cleanPath.startsWith(prefix)) {
    return `${base}${cleanPath}`;
  }

  return `${base}${prefix}${cleanPath}`;
}

/**
 * Get WebSocket URL
 */
export function getWsUrl(path: string = ''): string {
  const base = env.wsUrl;
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${base}${cleanPath}`;
}

/**
 * Get ChromaDB URL
 */
export function getChromaDbUrl(path: string = ''): string {
  const base = env.chromadbUrl;
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${base}${cleanPath}`;
}

// ============================================================================
// Feature Flag Helpers
// ============================================================================

/**
 * Check if a feature is enabled
 */
export function isFeatureEnabled(feature: keyof typeof env.features): boolean {
  return env.features[feature];
}

/**
 * Get all enabled features
 */
export function getEnabledFeatures(): string[] {
  return Object.entries(env.features)
    .filter(([_, enabled]) => enabled)
    .map(([feature]) => feature);
}

// ============================================================================
// Debug Logging
// ============================================================================

/**
 * Log environment configuration (debug mode only)
 */
export function logEnvConfig(): void {
  if (!env.debug) return;

  console.group('🔧 Environment Configuration');
  console.log('API URL:', env.apiUrl);
  console.log('WebSocket URL:', env.wsUrl);
  console.log('ChromaDB URL:', env.chromadbUrl);
  console.log('Features:', env.features);
  console.log('Debug Mode:', env.debug);
  console.log('Log Level:', env.logLevel);
  console.groupEnd();
}

// Auto-validate on import (only in browser)
if (typeof window !== 'undefined') {
  validateEnv();
  logEnvConfig();
}

// ============================================================================
// Type Exports
// ============================================================================

export type { EnvironmentConfig };
