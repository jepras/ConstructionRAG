import { PostHog } from 'posthog-node'

export default function PostHogClient() {
  const posthogClient = new PostHog(process.env.NEXT_PUBLIC_POSTHOG_KEY!, {
    host: process.env.NEXT_PUBLIC_POSTHOG_HOST!,
    flushAt: 1,
    flushInterval: 0
  })
  return posthogClient
}

// Note: Because server-side functions in Next.js can be short-lived, we set:
// - flushAt to 1: flush the queue after each capture call
// - flushInterval to 0: don't wait before flushing
// This ensures events are sent immediately and not batched.
// Remember to call await posthog.shutdown() when done.