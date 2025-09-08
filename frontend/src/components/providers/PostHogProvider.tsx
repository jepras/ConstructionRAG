'use client'

import { useEffect } from 'react'
import posthog from 'posthog-js'

export function PostHogProvider() {
  useEffect(() => {
    if (typeof window !== 'undefined' && process.env.NEXT_PUBLIC_POSTHOG_KEY) {
      posthog.init(process.env.NEXT_PUBLIC_POSTHOG_KEY, {
        api_host: "/ingest",
        ui_host: "https://eu.posthog.com",
        defaults: '2025-05-24',
        capture_exceptions: true,
        debug: process.env.NODE_ENV === "development",
        capture_pageview: false, // We'll handle this manually
        capture_pageleave: true,
        persistence: 'localStorage+cookie',
        // Session replay settings
        session_recording: {
          recordCrossOriginIframes: true,
          recordCanvas: true,
          maskAllText: false,
          maskAllInputs: false,
          // Record only in production
          disable_session_recording: process.env.NODE_ENV === "development",
        },
      })
    }
  }, [])

  return null
}