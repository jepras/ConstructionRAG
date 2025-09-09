import posthog from 'posthog-js'

posthog.init(process.env.NEXT_PUBLIC_POSTHOG_KEY, {
  api_host: "/ingest", // Use the proxy from next.config.ts
  ui_host: "https://eu.posthog.com",
  defaults: '2025-05-24',
  capture_exceptions: true,
  debug: false,
  // Cookie settings for domain handling
  cross_subdomain_cookie: false,
  persistence: 'localStorage+cookie',
  cookie_domain: typeof window !== 'undefined' ? window.location.hostname : undefined,
  // Session replay settings
  session_recording: {
    recordCrossOriginIframes: true,
    recordCanvas: true,
    maskAllText: false,
    maskAllInputs: false,
    // Record only in production
    disable_session_recording: process.env.NODE_ENV === "development",
  },
});