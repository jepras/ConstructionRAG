'use client'

import { useEffect } from 'react'
import posthog from 'posthog-js'

export function PostHogProvider() {
  useEffect(() => {
    // Debug logging
    console.log('PostHog Environment Check:')
    console.log('- NEXT_PUBLIC_POSTHOG_KEY:', process.env.NEXT_PUBLIC_POSTHOG_KEY)
    console.log('- NEXT_PUBLIC_POSTHOG_HOST:', process.env.NEXT_PUBLIC_POSTHOG_HOST)
    console.log('- NODE_ENV:', process.env.NODE_ENV)
    console.log('- window undefined?:', typeof window === 'undefined')
    
    if (typeof window !== 'undefined' && process.env.NEXT_PUBLIC_POSTHOG_KEY) {
      console.log('✅ Initializing PostHog...')
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
      console.log('✅ PostHog initialized successfully')
    } else {
      console.log('❌ PostHog NOT initialized - missing key or running server-side')
    }
  }, [])

  return null
}