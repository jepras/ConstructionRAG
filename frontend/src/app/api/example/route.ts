import { NextRequest, NextResponse } from 'next/server'
import PostHogClient from '@/lib/posthog'

export async function GET(request: NextRequest) {
  const posthog = PostHogClient()
  
  try {
    // Example server-side event tracking
    await posthog.capture({
      distinctId: 'anonymous-user', // In real app, use actual user ID
      event: 'api_endpoint_called',
      properties: {
        endpoint: '/api/example',
        userAgent: request.headers.get('user-agent'),
        timestamp: new Date().toISOString(),
      }
    })

    // Example feature flag check
    const flags = await posthog.getAllFlags('anonymous-user')
    
    // Always shutdown when done
    await posthog.shutdown()

    return NextResponse.json({
      message: 'Server-side PostHog example',
      flags: flags,
      tracked: true
    })
  } catch (error) {
    console.error('PostHog server-side error:', error)
    await posthog.shutdown()
    
    return NextResponse.json({
      message: 'Server-side PostHog example',
      error: 'PostHog tracking failed',
      tracked: false
    })
  }
}