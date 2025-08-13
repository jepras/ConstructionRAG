# Style and tree structure context for frontend development

1. Run `tree frontend/src` first to see current structure, then compare against desired structure below.
2. Read the style guide in the bottom.
3. When done, respond: "ready to develop frontend stuff"

### Desired Final Route Structure (from architecture doc)

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
│   └── [slug]/                 # Dynamic project routes
│       ├── page.tsx            # Project wiki overview
│       ├── query/page.tsx      # Project query interface
│       ├── experts/page.tsx    # Project-specific experts
│       └── layout.tsx          # Project-specific layout
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

### Styling System Rules

**ALWAYS use CSS variable-based classes from the architecture:**

✅ **Use These Classes:**
- `bg-background` - Main app background
- `bg-card` - Card/modal backgrounds  
- `bg-primary` - Primary orange accent color
- `text-foreground` - Main text color
- `text-muted-foreground` - Secondary/muted text
- `border-border` - Standard borders
- `bg-input` - Form input backgrounds
- `bg-secondary` - Secondary backgrounds
- `text-card-foreground` - Card text color
- `text-primary-foreground` - Primary button text

❌ **Never Use These:**
- Hardcoded colors like `bg-gray-800`, `text-green-400`, `bg-blue-500`
- Custom color classes like `supabase-*`, `custom-*`
- Any color that doesn't map to the CSS variables

### Component Development Rules

1. **Always check existing structure first** with `tree frontend/src`
2. **Follow the desired component organization** from architecture doc
3. **Use semantic naming** matching the architecture patterns
4. **Implement proper TypeScript interfaces** for all components
5. **Use CSS variables exclusively** for colors and theming
6. **Test components work in both light and dark themes**

### Before Any Frontend Work

1. Run `tree frontend/src` to see current structure
2. Compare against desired structure from architecture doc  
3. Note any missing directories or misplaced components
4. Follow the styling system rules strictly
5. Reference the architecture doc for component patterns

### State Management

- **TanStack Query v5** for server state
- **Zustand** for client state  
- **React Hook Form** for form handling


This command should be used whenever working on frontend components, pages, or architecture changes to ensure consistency with the established patterns and guidelines.