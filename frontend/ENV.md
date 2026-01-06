# Frontend Environment Configuration

This guide explains how to configure environment variables for the FinSight AI frontend.

## Quick Start

1. **Copy the example file:**
   ```bash
   cd frontend
   cp .env.example .env.local
   ```

2. **Update values** in `.env.local` with your actual configuration

3. **Restart dev server:**
   ```bash
   pnpm dev
   ```

## Environment Files

| File | Purpose | Committed to Git? |
|------|---------|-------------------|
| `.env.local` | Local development overrides | ❌ No |
| `.env.example` | Template with all available variables | ✅ Yes |
| `.env.development` | Development defaults (optional) | ✅ Yes |
| `.env.production` | Production defaults (optional) | ✅ Yes |

## Required Variables

```bash
# Backend API URL (required)
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Available Variables

### API Configuration

```bash
# Backend API Base URL
NEXT_PUBLIC_API_URL=http://localhost:8000

# API Version Prefix
NEXT_PUBLIC_API_V1_PREFIX=/api/v1

# WebSocket URL for real-time updates
NEXT_PUBLIC_WS_URL=ws://localhost:8000

# ChromaDB URL (if frontend needs direct access)
NEXT_PUBLIC_CHROMADB_URL=http://localhost:8001
```

### Feature Flags

Control which features are enabled in the UI:

```bash
# Enable/disable batch processing
NEXT_PUBLIC_ENABLE_BATCH_PROCESSING=true

# Enable/disable agent-based analysis
NEXT_PUBLIC_ENABLE_AGENT_ANALYSIS=true

# Enable/disable memory system features
NEXT_PUBLIC_ENABLE_MEMORY_SYSTEM=true

# Enable/disable advanced prompting patterns
NEXT_PUBLIC_ENABLE_ADVANCED_PROMPTING=true

# Enable/disable LLM safety checks UI
NEXT_PUBLIC_ENABLE_SAFETY_CHECKS=true

# Enable/disable model routing features
NEXT_PUBLIC_ENABLE_MODEL_ROUTING=true
```

### Development Settings

```bash
# Enable debug mode
NEXT_PUBLIC_DEBUG_MODE=false

# Log level: error, warn, info, debug
NEXT_PUBLIC_LOG_LEVEL=info

# Use mock API (for testing without backend)
NEXT_PUBLIC_MOCK_API=false

# API request timeout (milliseconds)
NEXT_PUBLIC_API_TIMEOUT=30000
```

### Analytics & Monitoring

```bash
# Google Analytics
NEXT_PUBLIC_ANALYTICS_ID=G-XXXXXXXXXX

# Sentry Error Tracking
NEXT_PUBLIC_SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx

# PostHog Product Analytics
NEXT_PUBLIC_POSTHOG_KEY=phc_xxxxx
NEXT_PUBLIC_POSTHOG_HOST=https://app.posthog.com
```

### Performance Settings

```bash
# Enable service worker
NEXT_PUBLIC_ENABLE_SERVICE_WORKER=false

# Max items per page in tables
NEXT_PUBLIC_MAX_ITEMS_PER_PAGE=50

# Max data points in charts
NEXT_PUBLIC_MAX_CHART_POINTS=100
```

### UI Settings

```bash
# Default theme: light, dark, system
NEXT_PUBLIC_DEFAULT_THEME=system

# Enable theme switching
NEXT_PUBLIC_ENABLE_THEME_TOGGLE=true
```

## Usage in Code

### Using the env helper

The recommended way to access environment variables is through the `lib/env.ts` helper:

```typescript
import { env, getApiUrl, isFeatureEnabled } from '@/lib/env';

// Access configuration
const apiUrl = env.apiUrl;
const debugMode = env.debug;

// Get full API endpoint
const fraudAnalysisUrl = getApiUrl('/fraud/analyze');
// Returns: http://localhost:8000/api/v1/fraud/analyze

// Check feature flags
if (isFeatureEnabled('batchProcessing')) {
  // Show batch processing UI
}

// Access nested config
const theme = env.ui.defaultTheme;
const maxItems = env.performance.maxItemsPerPage;
```

### Direct access (not recommended)

```typescript
// This works but bypasses type safety and validation
const apiUrl = process.env.NEXT_PUBLIC_API_URL;
```

## Environment-Specific Configuration

### Development

Create `.env.development.local` for local dev overrides:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_DEBUG_MODE=true
NEXT_PUBLIC_LOG_LEVEL=debug
NEXT_PUBLIC_MOCK_API=false
```

### Production

Set environment variables in your deployment platform (Vercel, Netlify, etc.):

```bash
NEXT_PUBLIC_API_URL=https://api.finsight-ai.com
NEXT_PUBLIC_WS_URL=wss://api.finsight-ai.com
NEXT_PUBLIC_DEBUG_MODE=false
NEXT_PUBLIC_LOG_LEVEL=error
```

## Docker Configuration

When running in Docker, pass environment variables:

```bash
docker run -p 3000:3000 \
  -e NEXT_PUBLIC_API_URL=http://backend:8000 \
  -e NEXT_PUBLIC_WS_URL=ws://backend:8000 \
  finsight-frontend
```

Or use `.env` file:

```bash
docker run -p 3000:3000 \
  --env-file .env.production \
  finsight-frontend
```

## Validation

The `lib/env.ts` module automatically validates required variables on startup:

- **Development**: Logs warnings but continues with fallback values
- **Production**: Throws error if required variables are missing

To manually trigger validation:

```typescript
import { validateEnv, logEnvConfig } from '@/lib/env';

// Validate configuration
validateEnv();

// Log current config (debug mode only)
logEnvConfig();
```

## Troubleshooting

### Variables not updating

1. Restart the dev server after changing `.env.local`
2. Clear Next.js cache: `rm -rf .next`
3. Rebuild: `pnpm build`

### Variables undefined in browser

- Ensure variable name starts with `NEXT_PUBLIC_`
- Variables without this prefix are only available server-side

### Type errors with env

```typescript
// ✅ Correct - use the env object
import { env } from '@/lib/env';
const url = env.apiUrl;

// ❌ Wrong - process.env is not typed
const url = process.env.NEXT_PUBLIC_API_URL;
```

## Best Practices

1. **Never commit `.env.local`** - Contains sensitive values
2. **Always commit `.env.example`** - Documents available variables
3. **Use feature flags** - Enable/disable features without code changes
4. **Use the env helper** - Get type safety and validation
5. **Prefix public vars** - Use `NEXT_PUBLIC_` for browser access
6. **Keep secrets server-side** - Never expose API keys in `NEXT_PUBLIC_` vars

## Example Configurations

### Local Development

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_DEBUG_MODE=true
NEXT_PUBLIC_LOG_LEVEL=debug
```

### Staging

```bash
NEXT_PUBLIC_API_URL=https://staging-api.finsight-ai.com
NEXT_PUBLIC_DEBUG_MODE=false
NEXT_PUBLIC_LOG_LEVEL=info
NEXT_PUBLIC_ENABLE_BATCH_PROCESSING=true
```

### Production

```bash
NEXT_PUBLIC_API_URL=https://api.finsight-ai.com
NEXT_PUBLIC_WS_URL=wss://api.finsight-ai.com
NEXT_PUBLIC_DEBUG_MODE=false
NEXT_PUBLIC_LOG_LEVEL=error
NEXT_PUBLIC_ANALYTICS_ID=G-PROD12345
NEXT_PUBLIC_SENTRY_DSN=https://xxx@sentry.io/xxx
```

## Related Files

- `frontend/.env.example` - Template with all variables
- `frontend/lib/env.ts` - Environment configuration helper
- `frontend/.gitignore` - Ignore local env files
- `backend/app/core/config.py` - Backend configuration (reference)
