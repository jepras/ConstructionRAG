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