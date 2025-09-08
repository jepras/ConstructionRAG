import posthog from "posthog-js"

posthog.init(process.env.NEXT_PUBLIC_POSTHOG_KEY!, {
  api_host: "/ingest",
  ui_host: "https://eu.posthog.com",
  defaults: '2025-05-24',
  capture_exceptions: true, // This enables capturing exceptions using Error Tracking, set to false if you don't want this
  debug: process.env.NODE_ENV === "development",
  // Session replay settings
  session_recording: {
    recordCrossOriginIframes: true,
    recordCanvas: true,
    maskAllText: false,
    maskAllInputs: false,
    // Record only on production to avoid noise from dev
    disable_session_recording: process.env.NODE_ENV === "development",
  },
});