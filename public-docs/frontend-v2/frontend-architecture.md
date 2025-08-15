# ConstructionRAG Frontend Architecture

## Overview

This document outlines the complete frontend architecture for ConstructionRAG's production React frontend using Next.js 15.3 with App Router. The architecture is designed based on comprehensive UI analysis and supports both anonymous and authenticated user flows seamlessly.

## Key Design Principles

- **Single-root architecture** where marketing and authenticated app sections coexist
- **Multi-layout system** supporting marketing, app, and project-specific layouts
- **Performance-first** with route-based code splitting and ISR for dynamic content
- **State management** optimized for complex server-client interactions
- **Component reusability** across different user flows and authentication states

## Technical Stack

### Core Technologies
- **Next.js 15.3** with App Router and TypeScript
- **React 18** with Server Components and Suspense
- **Tailwind CSS** for styling
- **shadcn/ui** for component library
- **TanStack Query v5** for server state management
- **Zustand** for client state management
- **React Hook Form** for form handling
- **Supabase** for authentication and storage

### State Management Strategy

#### TanStack Query (Server State)
```typescript
// API client with authentication
class ApiClient {
  private baseURL = process.env.NEXT_PUBLIC_API_URL;
  
  async getIndexingRuns(params: PaginationParams & FilterParams) {
    return this.request('/api/indexing-runs', { params });
  }
  
  async getProjectWithRun(projectId: string, runId: string) {
    return this.request(`/api/projects/${projectId}/runs/${runId}`);
  }
  
  async getProjectRuns(projectId: string) {
    return this.request(`/api/projects/${projectId}/runs`);
  }
  
  async queryProject(projectId: string, query: string) {
    return this.request('/api/queries', { 
      method: 'POST', 
      body: { query, project_id: projectId }
    });
  }
}
```

#### Zustand (Client State)
```typescript
interface AppState {
  // UI State
  sidebarOpen: boolean;
  currentProject: Project | null;
  activeWikiSection: string | null;
  
  // User State
  user: User | null;
  authState: 'loading' | 'authenticated' | 'anonymous';
  
  // Anonymous User Session
  anonymousSession: {
    uploadedDocuments: string[];
    indexingRunId: string | null;
    queries: Query[];
  } | null;
}
```

## Application Architecture

### Route Structure

```
app/
├── layout.tsx                    # Root layout with providers
├── globals.css                   # Global styles with CSS variables color system
├── (marketing)/                  # Route group for public pages
│   ├── layout.tsx               # Marketing layout with footer
│   ├── page.tsx                 # Landing page (//)
│   ├── about/page.tsx           # About page
│   ├── pricing/page.tsx         # Pricing page
│   └── loading.tsx              # Marketing loading states
├── (app)/                       # Route group for authenticated app
│   ├── layout.tsx               # Clean app layout without marketing footer
│   ├── dashboard/page.tsx       # User project dashboard
│   ├── experts/                 # Expert marketplace
│   │   ├── page.tsx            # Expert marketplace grid
│   │   └── [expertId]/page.tsx # Individual expert details
│   └── settings/page.tsx        # User settings
├── projects/                    # Public project browsing
│   ├── page.tsx                # Public projects grid (/projects)
│   └── [projectSlug]/          # Dynamic project routes (nested structure)
│       └── [runId]/            # Specific indexing run version
│           ├── page.tsx        # Project wiki overview for specific run
│           ├── query/page.tsx  # Project query interface for specific run
│           ├── experts/page.tsx # Project-specific experts for specific run
│           └── layout.tsx      # Project-specific layout
├── auth/                       # Authentication flows
│   ├── signin/page.tsx
│   ├── signup/page.tsx
│   └── callback/page.tsx       # Supabase auth callback
├── api/                        # Next.js API routes
│   ├── auth/
│   │   └── refresh/route.ts    # Token refresh endpoint
│   └── revalidate/route.ts     # ISR revalidation webhook
└── middleware.ts               # Auth and routing middleware
```

### Component Architecture

```typescript
components/
├── ui/                         # shadcn/ui base components
│   ├── button.tsx
│   ├── input.tsx
│   ├── card.tsx
│   ├── dialog.tsx
│   └── ...
├── layout/
│   ├── Header.tsx              # Main navigation with auth state
│   ├── Footer.tsx              # Marketing footer with email signup
│   └── ProjectHeader.tsx       # Project-specific navigation with context
├── features/
│   ├── landing/
│   │   ├── HeroSection.tsx     # Split query/document viewer
│   │   ├── FeatureShowcase.tsx # 3-step process cards
│   │   ├── ProcessStep.tsx     # Individual feature card
│   │   └── CTASection.tsx      # Upload/explore call-to-action
│   ├── projects/
│   │   ├── ProjectGrid.tsx     # Responsive grid with infinite scroll
│   │   ├── ProjectCard.tsx     # Individual project preview card
│   │   ├── ProjectStats.tsx    # Document/page/size statistics
│   │   ├── ProjectSearch.tsx   # Search and filter functionality
│   │   └── AddProjectCard.tsx  # Login prompt for authenticated features
│   ├── wiki/
│   │   ├── WikiLayout.tsx      # Three-column layout wrapper
│   │   ├── WikiNavigation.tsx  # Left sidebar with expandable sections
│   │   ├── WikiContent.tsx     # Main markdown content rendering
│   │   ├── WikiTOC.tsx         # Right sidebar table of contents
│   │   ├── WikiDiagram.tsx     # Interactive project flow diagrams
│   │   └── WikiBreadcrumb.tsx  # Hierarchical navigation
│   ├── query/
│   │   ├── QueryInterface.tsx  # Chat-style query input with history
│   │   ├── QueryHistory.tsx    # Previous queries with filtering
│   │   ├── DocumentViewer.tsx  # PDF/document display with navigation
│   │   ├── QueryResults.tsx    # Structured answer display
│   │   └── SourceReferences.tsx # Clickable source citations
│   ├── experts/
│   │   ├── ExpertGrid.tsx      # Marketplace grid with filtering
│   │   ├── ExpertCard.tsx      # Individual expert module cards
│   │   ├── ExpertModal.tsx     # Detailed expert view and configuration
│   │   ├── ExpertStats.tsx     # Usage statistics and metrics
│   │   └── ExpertLanguages.tsx # Multilingual support indicators
│   ├── upload/
│   │   ├── UploadZone.tsx      # Drag & drop file upload
│   │   ├── UploadProgress.tsx  # Multi-file progress tracking
│   │   ├── FilePreview.tsx     # Uploaded file preview cards
│   │   └── UploadSettings.tsx  # Anonymous vs project upload options
│   └── auth/
│       ├── SignInForm.tsx      # Email/password sign in
│       ├── SignUpForm.tsx      # User registration form
│       ├── AuthProvider.tsx    # Supabase auth context
│       └── ProtectedRoute.tsx  # Route protection wrapper
├── shared/
│   ├── StatusIndicator.tsx     # Processing status badges
│   ├── ProgressTracker.tsx     # Step-by-step progress display
│   ├── UserAvatar.tsx          # User profile display
│   ├── LoadingSpinner.tsx      # Consistent loading states
│   ├── ErrorBoundary.tsx       # Error handling wrapper
│   └── SEOHead.tsx             # Dynamic meta tags
└── providers/
    ├── QueryProvider.tsx       # TanStack Query configuration
    ├── AuthProvider.tsx        # Authentication state
    ├── ThemeProvider.tsx       # Theme and styling context
    └── ToastProvider.tsx       # Notification system
```

## Multi-Layout System

### Root Layout
```typescript
// app/layout.tsx
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="bg-background text-foreground font-sans antialiased">
        <QueryProvider>
          <AuthProvider>
            <ToastProvider>
              <div className="min-h-screen flex flex-col">
                {children}
              </div>
            </ToastProvider>
          </AuthProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
```


### Project Layout
```typescript
// app/projects/[projectSlug]/[runId]/layout.tsx
export default function ProjectLayout({ 
  children, 
  params 
}: { 
  children: React.ReactNode;
  params: { projectSlug: string; runId: string };
}) {
  const { projectSlug, runId } = params;
  const project = useProjectWithRun(extractProjectId(projectSlug), runId);
  
  return (
    <>
      <ProjectHeader projectSlug={projectSlug} runId={runId} project={project} />
      <div className="container mx-auto px-4 py-6">
        {children}
      </div>
    </>
  );
}
```

## Dynamic Content Generation

### Project Page Generation Strategy

**Static Generation with ISR (Incremental Static Regeneration)**

```typescript
// app/projects/[projectSlug]/[runId]/page.tsx
export async function generateStaticParams() {
  const projects = await getPublicProjects();
  
  return projects.map((project) => ({
    projectSlug: `${project.name.toLowerCase().replace(/\s+/g, '-')}-${project.id}`,
    runId: project.indexing_run_id,
  }));
}

export async function generateMetadata({ params }: { params: { projectSlug: string; runId: string } }) {
  const { projectSlug, runId } = params;
  const projectId = extractProjectIdFromSlug(projectSlug);
  const project = await apiClient.getProjectWithRun(projectId, runId);
  
  return {
    title: `${project.name} - ConstructionRAG`,
    description: project.description,
    openGraph: {
      title: project.name,
      description: project.description,
      images: [`/api/og?project=${project.id}`],
    },
  };
}

export default async function ProjectPage({ params }: { params: { projectSlug: string; runId: string } }) {
  const { projectSlug, runId } = params;
  const projectId = extractProjectIdFromSlug(projectSlug);
  const project = await apiClient.getProjectWithRun(projectId, runId);
  const wikiPages = await apiClient.getWikiPages(runId);
  
  return (
    <WikiLayout>
      <WikiNavigation pages={wikiPages} />
      <WikiContent content={wikiPages.overview} />
      <WikiTOC sections={wikiPages.overview.sections} />
    </WikiLayout>
  );
}

export const revalidate = 3600; // Revalidate every hour
```

### Webhook-Triggered Revalidation

```typescript
// app/api/revalidate/route.ts
import { revalidateTag, revalidatePath } from 'next/cache';

export async function POST(request: Request) {
  const { type, projectId, runId } = await request.json();
  
  if (type === 'wiki_generation_complete') {
    // Revalidate specific project page with nested structure
    revalidatePath(`/projects/${projectSlug}/${runId}`);
    revalidateTag(`wiki-${runId}`);
    
    // Revalidate public projects grid
    revalidatePath('/projects');
    
    return Response.json({ revalidated: true });
  }
  
  return Response.json({ revalidated: false });
}
```

## Authentication & User Flow Management

### Core Authentication Principles

**CRITICAL: Follow these patterns to prevent infinite loops and auth conflicts**

#### Single Source of Truth
- **Always use the `AuthProvider`** from `components/providers/AuthProvider.tsx` - never create custom auth state
- **Never call `supabase.auth` directly** in components - use the `useAuth()` hook instead
- **Single auth state manager** - consolidate all auth checks into one useEffect with proper cleanup

#### API Client Authentication
- **Use the centralized `apiClient`** from `lib/api-client.ts` for all authenticated requests
- **Token caching is built-in** - the API client handles token refresh and caching automatically
- **Never manually fetch auth headers** - let the API client handle this internally
- **Clear auth cache on sign out** - call `apiClient.clearAuthCache()` when auth state changes

#### Component Auth Patterns
```typescript
// ✅ CORRECT: Use the auth hook
function MyComponent() {
  const { user, isLoading, isAuthenticated } = useAuth()
  
  if (isLoading) return <LoadingSpinner />
  if (!isAuthenticated) return <SignInPrompt />
  
  return <AuthenticatedContent user={user} />
}

// ❌ WRONG: Never do this
function MyComponent() {
  const [user, setUser] = useState(null)
  const supabase = createClient()
  
  useEffect(() => {
    // This creates auth loops and conflicts!
    supabase.auth.getSession().then(...)
  }, [])
}
```

#### Query Hook Authentication
```typescript
// ✅ CORRECT: Conditional queries based on auth state
function useUserData() {
  const { isAuthenticated } = useAuth()
  
  return useQuery({
    queryKey: ['user-data'],
    queryFn: () => apiClient.getUserData(),
    enabled: isAuthenticated, // Only run when authenticated
  })
}

// ❌ WRONG: Queries that run regardless of auth state
function useUserData() {
  return useQuery({
    queryKey: ['user-data'],
    queryFn: () => apiClient.getUserData(), // This will fail and retry infinitely
  })
}
```

#### Backend RLS (Row Level Security) Integration

**Critical for authenticated API endpoints:** The backend must use the authenticated Supabase client to properly handle RLS policies.

```python
# ✅ CORRECT: Backend endpoint with RLS support
@router.get("/user-projects-with-wikis")
async def list_user_projects_with_wikis(
    current_user: dict[str, Any] = Depends(get_current_user),
    db_client = Depends(get_db_client_for_request),  # ← Authenticated client with JWT
):
    db = db_client  # Includes user's JWT for RLS policies
    result = db.table("project_wikis").select("*").eq("user_id", current_user["id"]).execute()
    return result.data  # ✅ Returns user's data correctly

# ❌ WRONG: Using anon client breaks RLS
@router.get("/user-projects-with-wikis") 
async def list_user_projects_with_wikis(
    current_user: dict[str, Any] = Depends(get_current_user),
):
    db = get_supabase_client()  # ← Anon client - no JWT context!
    result = db.table("project_wikis").select("*").eq("user_id", current_user["id"]).execute() 
    return result.data  # ❌ Returns [] - RLS blocks the query
```

**Why this matters:** 
- Supabase RLS policies need the user's JWT token to determine data access
- The anon client (`get_supabase_client()`) has no user context
- Even with proper `current_user` authentication, RLS policies will block anon client queries
- Always use `get_db_client_for_request()` for user-specific database operations

#### Error Boundaries for Auth
- **Wrap authenticated routes** with `ErrorBoundary` to handle auth failures gracefully
- **Provide fallback UI** for auth errors with sign-in prompts
- **Never let auth errors crash the app** - always provide recovery options

### Anonymous to Authenticated Transition

```typescript
// hooks/useAnonymousSession.ts
export function useAnonymousSession() {
  const [session, setSession] = useLocalStorage<AnonymousSession>('anonymous_session', null);
  const { mutate: migrateSession } = useMutation({
    mutationFn: async (userId: string) => {
      if (!session) return;
      
      // Migrate anonymous data to authenticated account
      await api.post('/api/auth/migrate-anonymous', {
        userId,
        anonymousSession: session,
      });
      
      // Clear anonymous session
      setSession(null);
    },
  });
  
  return { session, setSession, migrateSession };
}
```

### Route Protection Middleware

```typescript
// middleware.ts
import { createMiddlewareClient } from '@supabase/auth-helpers-nextjs';

export async function middleware(req: NextRequest) {
  const res = NextResponse.next();
  const supabase = createMiddlewareClient({ req, res });
  
  const {
    data: { session },
  } = await supabase.auth.getSession();
  
  // Protect authenticated routes
  if (req.nextUrl.pathname.startsWith('/dashboard') && !session) {
    return NextResponse.redirect(new URL('/auth/signin', req.url));
  }
  
  // Redirect authenticated users from auth pages
  if (req.nextUrl.pathname.startsWith('/auth') && session) {
    return NextResponse.redirect(new URL('/dashboard', req.url));
  }
  
  return res;
}

export const config = {
  matcher: ['/dashboard/:path*', '/auth/:path*']
};
```

## Performance Optimization

### Code Splitting Strategy

1. **Route-based splitting** (automatic in Next.js)
2. **Feature-based dynamic imports**
3. **Component-level lazy loading**

```typescript
// Dynamic imports for heavy components
const ExpertMarketplace = dynamic(() => import('../features/experts/ExpertGrid'), {
  loading: () => <ExpertGridSkeleton />,
  ssr: false, // Client-side only for complex interactions
});

const DocumentViewer = dynamic(() => import('../features/query/DocumentViewer'), {
  loading: () => <DocumentViewerSkeleton />,
});
```

### Caching Strategy

```typescript
// TanStack Query configuration
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      cacheTime: 10 * 60 * 1000, // 10 minutes
      retry: (failureCount, error) => {
        // Retry logic based on error type
        if (error.status === 404) return false;
        return failureCount < 3;
      },
    },
  },
});
```

### Image and Asset Optimization

```typescript
// next.config.js
module.exports = {
  images: {
    domains: ['your-supabase-url.supabase.co'],
    formats: ['image/webp', 'image/avif'],
  },
  experimental: {
    optimizeFonts: true,
    optimizeCss: true,
  },
};
```

## Styling System

### CSS Variables Color System


### Component Styling Guidelines

**Use Standard Tailwind Color Classes:**
- `bg-background` - Main app background
- `bg-card` - Card/modal backgrounds  
- `bg-primary` - Primary orange accent color
- `text-foreground` - Main text color
- `text-muted-foreground` - Secondary/muted text
- `border-border` - Standard borders
- `bg-input` - Form input backgrounds

```typescript
// Consistent component styling patterns
const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-ring",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        outline: "border border-border bg-background hover:bg-accent hover:text-accent-foreground",
      },
      size: {
        sm: "h-9 px-3",
        md: "h-10 px-4 py-2", 
        lg: "h-11 px-8",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "md",
    },
  }
);
```

**Styling Best Practices:**
1. **Never use custom color classes** (e.g., `supabase-*`, `custom-*`)
2. **Always use CSS variable-based classes** that map to your `globals.css`
3. **Maintain consistent spacing** with standard Tailwind scale (`p-4`, `m-6`, etc.)
4. **Use semantic color naming** (`primary`, `secondary`, `muted`) over specific colors
5. **Test all components in both light and dark themes** to ensure proper contrast

## SEO & Meta Tag Strategy

### Dynamic Meta Tags

```typescript
// app/projects/[slug]/page.tsx
export async function generateMetadata({ params }: { params: { slug: string } }) {
  const project = await getProjectFromSlug(params.slug);
  
  return {
    title: `${project.name} - Project Documentation | ConstructionRAG`,
    description: `Explore detailed documentation and AI-powered insights for ${project.name}. Get instant answers about project requirements, timelines, and specifications.`,
    keywords: ['construction', 'project management', 'AI', 'documentation', project.name],
    openGraph: {
      title: project.name,
      description: project.description,
      url: `https://specfinder.com/projects/${params.slug}`,
      siteName: 'ConstructionRAG',
      images: [
        {
          url: `/api/og?project=${project.id}`,
          width: 1200,
          height: 630,
          alt: `${project.name} project overview`,
        },
      ],
      locale: 'en_US',
      type: 'website',
    },
    twitter: {
      card: 'summary_large_image',
      title: project.name,
      description: project.description,
      images: [`/api/og?project=${project.id}`],
    },
    robots: {
      index: true,
      follow: true,
      googleBot: {
        index: true,
        follow: true,
        'max-video-preview': -1,
        'max-image-preview': 'large',
        'max-snippet': -1,
      },
    },
  };
}
```

### Structured Data

```typescript
// components/shared/StructuredData.tsx
export function ProjectStructuredData({ project }: { project: Project }) {
  const structuredData = {
    "@context": "https://schema.org",
    "@type": "CreativeWork",
    "name": project.name,
    "description": project.description,
    "url": `https://specfinder.com/projects/${project.slug}`,
    "author": {
      "@type": "Organization",
      "name": "ConstructionRAG"
    },
    "datePublished": project.createdAt,
    "dateModified": project.updatedAt,
    "inLanguage": "en-US"
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(structuredData) }}
    />
  );
}
```


## Backend Integration

### Type-Safe API Client

```typescript
// lib/api-client.ts
export class ApiClient {
  private baseURL: string;
  private getAuthHeaders: () => Promise<Record<string, string>>;

  constructor() {
    this.baseURL = process.env.NEXT_PUBLIC_API_URL!;
    this.getAuthHeaders = async () => {
      const supabase = createClientComponentClient();
      const { data: { session } } = await supabase.auth.getSession();
      
      return session?.access_token 
        ? { Authorization: `Bearer ${session.access_token}` }
        : {};
    };
  }

  async uploadDocuments(files: File[], uploadType: 'email' | 'user_project', metadata?: any) {
    const formData = new FormData();
    files.forEach((file, index) => {
      formData.append(`files`, file);
    });
    formData.append('upload_type', uploadType);
    if (metadata) {
      formData.append('metadata', JSON.stringify(metadata));
    }

    return this.request<UploadResponse>('/api/uploads', {
      method: 'POST',
      body: formData,
      headers: await this.getAuthHeaders(),
    });
  }

  async getIndexingRuns(params: GetIndexingRunsParams) {
    return this.request<PaginatedResponse<IndexingRun>>('/api/indexing-runs', {
      params,
      headers: await this.getAuthHeaders(),
    });
  }

  async createQuery(query: CreateQueryRequest) {
    return this.request<QueryResponse>('/api/queries', {
      method: 'POST',
      body: JSON.stringify(query),
      headers: {
        'Content-Type': 'application/json',
        ...(await this.getAuthHeaders()),
      },
    });
  }

  private async request<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    const url = new URL(endpoint, this.baseURL);
    
    if (options?.params) {
      Object.entries(options.params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          url.searchParams.append(key, String(value));
        }
      });
    }

    const response = await fetch(url.toString(), {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      throw new ApiError(response.status, await response.text());
    }

    return response.json();
  }
}

export const apiClient = new ApiClient();
```

## Testing Strategy

### Component Testing
```typescript
// __tests__/components/ProjectCard.test.tsx
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ProjectCard } from '../components/features/projects/ProjectCard';

const createTestQueryClient = () => new QueryClient({
  defaultOptions: {
    queries: { retry: false },
    mutations: { retry: false },
  },
});

function renderWithProviders(ui: React.ReactElement) {
  const testQueryClient = createTestQueryClient();
  
  return render(
    <QueryClientProvider client={testQueryClient}>
      {ui}
    </QueryClientProvider>
  );
}

describe('ProjectCard', () => {
  const mockProject = {
    id: '123',
    name: 'Test Project',
    description: 'Test description',
    stats: { documents: 5, pages: 25, size: '2.4 MB' },
  };

  it('renders project information correctly', () => {
    renderWithProviders(<ProjectCard project={mockProject} />);
    
    expect(screen.getByText('Test Project')).toBeInTheDocument();
    expect(screen.getByText('Test description')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument(); // documents count
    expect(screen.getByText('25')).toBeInTheDocument(); // pages count
    expect(screen.getByText('2.4 MB')).toBeInTheDocument(); // size
  });
});


## Summary

This architecture provides:

1. **Scalable component organization** matching your UI complexity
2. **Performance-optimized routing** with proper code splitting
3. **Flexible state management** handling both server and client state
4. **Multi-layout system** supporting different user flows
5. **SEO-friendly dynamic content** with ISR and structured data
6. **Type-safe backend integration** with comprehensive error handling
7. **Production-ready deployment** configuration for Railway

The architecture is designed to grow with your application while maintaining performance and developer experience.