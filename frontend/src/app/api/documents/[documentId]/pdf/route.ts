import { NextRequest, NextResponse } from 'next/server';
import { createServerClient } from '@supabase/ssr';
import { cookies } from 'next/headers';

// Backend API base URL
const BACKEND_API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ documentId: string }> }
) {
  try {
    // Await params as required in Next.js 15
    const { documentId } = await params;
    const searchParams = request.nextUrl.searchParams;
    
    // Build the backend URL with query parameters
    const backendUrl = new URL(`/api/documents/${documentId}/pdf`, BACKEND_API_URL);
    
    // Forward query parameters (like index_run_id)
    searchParams.forEach((value, key) => {
      backendUrl.searchParams.set(key, value);
    });
    
    // Get auth token from Supabase session (consistent with other endpoints)
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };
    
    try {
      const cookieStore = await cookies();
      
      // Create Supabase server client for API routes
      const supabase = createServerClient(
        process.env.NEXT_PUBLIC_SUPABASE_URL!,
        process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
        {
          cookies: {
            getAll() {
              return cookieStore.getAll()
            },
            setAll(cookiesToSet) {
              try {
                cookiesToSet.forEach(({ name, value, options }) => {
                  cookieStore.set(name, value, options)
                })
              } catch {
                // The `setAll` method was called from a Server Component.
                // This can be ignored if you have middleware refreshing
                // user sessions.
              }
            },
          },
        }
      );
      
      const { data: { session }, error } = await supabase.auth.getSession();
      
      if (!error && session?.access_token) {
        headers['Authorization'] = `Bearer ${session.access_token}`;
      }
    } catch (authError) {
      console.log('No auth session, proceeding without auth header');
    }
    
    // Make request to backend
    const response = await fetch(backendUrl.toString(), {
      method: 'GET',
      headers,
    });
    
    if (!response.ok) {
      const errorData = await response.text();
      console.error('Backend PDF endpoint error:', errorData);
      
      return NextResponse.json(
        { error: 'Failed to fetch PDF URL from backend' },
        { status: response.status }
      );
    }
    
    const data = await response.json();
    
    // Return the PDF URL data
    return NextResponse.json(data);
    
  } catch (error) {
    console.error('PDF proxy error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}