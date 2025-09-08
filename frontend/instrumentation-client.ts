import posthog from 'posthog-js'

posthog.init(process.env.NEXT_PUBLIC_POSTHOG_KEY, {
  api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST,
  defaults: '2025-05-24',
  capture_exceptions: true,
  debug: process.env.NODE_ENV === "development",
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