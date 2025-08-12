# Frontend Planning Prompt for ConstructionRAG Application
I need to build a modern React frontend using Next.js 15.3 with App Router for my AI-powered construction document Q&A system called "ConstructionRAG". This will be a production web application that needs to handle both anonymous and authenticated users seamlessly.

## Core Requirements:
### Application Structure:

Single-root architecture where landing pages and authenticated app sections coexist
Marketing pages (landing, about, pricing) should be publicly accessible

I want unauthenticated users to try the main functionality of our app without creating a user. They should be able to upload files and trigger an indexing run, they should be able to see all public indexing runs under specfinder.com/project/ and their own public indexing run under specfinder.com/project/projectname+id. They should also be able to query the indexed run under that page and create a wiki run if it is not already created. 
Authenticated users should be able to see a dashboard of all their projects, create new projects and indexing runs with that project id (backend api endpoints should support most of this already).

Unauthenticated users should be able to upload project files, see public projects under specfinder.com/project/projectname+id, 

Must support both anonymous users (email-based uploads) and registered users (project-based workflows)

### Dynamic Content Generation:

Programmatically generate project showcase pages from markdown content stored in supabase storage
URL structure: /project/[project-name]-[unique-identifier]
These pages should be SEO-optimized and work for both anonymous and authenticated user projects
Need static generation at build time with ISR for new projects

### User Experience Flow:

Anonymous users can upload documents, get processing results, and view generated wikis
Authenticated users get full project management, persistent history, and advanced features
Smooth transition from anonymous to authenticated usage without losing work

### Technical Stack Preferences:

Next.js 15.3 with App Router and TypeScript
shadcn/ui for component library
Tailwind CSS for styling
React Hook Form for form handling
Supabase for authentication (already configured)
Modern state management approach suitable for App Router

### Key Features to Implement:

Document upload interface with drag-and-drop and progress tracking
Query interface with real-time search and results display
Project management dashboard for authenticated users
Wiki page generation and display from markdown
Responsive design for mobile and desktop

### Styling
#### Core Design Philosophy

The application's aesthetic is a dark, modern, and minimalist SaaS UI, heavily inspired by the clean look of platforms like Supabase.

#### Key Principles:
Clarity over Clutter: Prioritize clear information hierarchy and generous whitespace. Every element should have a purpose.
Consistency is Key: Components should be predictable. A button or an input field should look and behave the same way everywhere.
Accent with Purpose: Use the primary accent color (supabase-green) intentionally for main calls-to-action (CTAs), highlights, and to guide the user's attention.
Subtle Interactivity: Animations and transitions should be smooth and subtle, providing feedback to the user without being distracting.

#### Colours
Use these exact color names in your Tailwind classes. Do not use arbitrary hex codes.
Tailwind Class	Hex	Primary Usage
bg-supabase-dark	#181818	Main application background.
bg-supabase-dark-2	#232323	Card backgrounds, sidebars, secondary layout elements.
bg-supabase-dark-3	#2a2a2a	Input fields, selected items, subtle hover backgrounds.
border-supabase-border	#333333	The only color for borders and dividers.
text-supabase-text	#a8a8a8	Standard body text, descriptions, labels, and paragraphs.
text-supabase-text-light	#e0e0e0	Higher-contrast text for titles or important information.
text-white	#ffffff	Main headings (h1, h2) and text on green backgrounds.
bg-supabase-green	#24b47e	Primary action color. For all primary buttons, active states, and important highlights.
bg-supabase-green-hover	#1a9a6a	The hover state for all elements using bg-supabase

#### Font
Hierarchy is established through a combination of font, size, weight, and color.

Fonts:
    Sans-serif: font-sans ('Inter') - Used for all UI text, from headings to labels.
    Handwriting: font-handwriting ('Caveat') - Reserved for special, decorative text (not currently in use in the main UI).

Usage Guidelines:
    Page Titles (<h1>): text-3xl to text-5xl, font-bold or font-extrabold, text-white.
    Section Titles (<h2>, <h3>): text-xl to text-2xl, font-bold, text-supabase-text-light.
    Body Text (<p>): text-sm or text-base, font-normal, text-supabase-text.
    Labels & Metadata: text-xs or text-sm, font-medium, text-supabase-text.

#### Component Styling Reference
    Buttons:
        Primary: bg-supabase-green text-white font-bold rounded-md hover:bg-supabase-green-hover.
        Secondary: bg-supabase-dark-3 border border-supabase-border text-supabase-text-light rounded-md hover:bg-supabase-dark hover:border-supabase-text.

    Input Fields & Selects:
        Base: bg-supabase-dark-3 border border-supabase-border rounded-md text-supabase-text-light.
        Focus State: focus:outline-none focus:ring-2 focus:ring-supabase-green. This is a critical pattern for accessibility and user feedback.

    Cards & Containers:
        Standard Card: bg-supabase-dark-2 border border-supabase-border rounded-lg p-6.
        Interactive Card (e.g., ProjectCard): Apply a group class to the card container. The border should change color on hover using group-hover:border-supabase-green.

#### Interactivity & Animations

Animations should be meaningful and provide feedback. Always include smooth transitions.
    Hover States (hover:): Every clickable element must have a clear hover state.
        Use transition-colors and duration-200 to make these changes smooth.
        Pattern: Slightly lighten/darken the background or border. For example, a card's border changing from supabase-border to supabase-green.

    Press/Active States: For navigation and tabs, the active item should be visually distinct, typically using the supabase-green color for text or a border.

    Keyframe Animations:
        animate-fade-in: Use this for all page-level components to create a smooth loading effect (<div className="animate-fade-in">...</div>).
        animate-float: A subtle up-and-down floating effect. Reserved for decorative icons on the landing page to add dynamism.
        animate-spin: Used exclusively for the Spinner component to indicate a loading process.

## Questions I need you to clarify:

State Management Strategy: Given the mix of server data (documents, queries, projects) and client state (UI preferences, form state), how should I structure state management? Should I use a combination of React Query for server state and Zustand for client state, or do you recommend a different approach?
Route Architecture: How should I structure the routing to cleanly separate marketing pages, authenticated app sections, and dynamic project pages while maintaining good SEO and user experience?
Authentication Flow: What's the best way to handle the transition from anonymous usage to authenticated usage, ensuring users don't lose their work when they decide to sign up?
Dynamic Page Generation: For the programmatic project pages, should I use static generation with ISR, or would server-side rendering be more appropriate given that new projects are created regularly?
Component Organization: How should I structure components to maximize reusability between anonymous and authenticated user flows while keeping the codebase maintainable?
Performance Optimization: What specific Next.js 15.3 features should I prioritize for optimal performance, especially for document upload progress and real-time query results?
SEO Strategy: How should I handle SEO for both the marketing pages and the dynamically generated project showcase pages?
Need static generation at build time with ISR for new projects vs server-side-rendering? 

Please provide specific architectural recommendations and implementation strategies based on these requirements and the latest Next.js 15.3 best practices.