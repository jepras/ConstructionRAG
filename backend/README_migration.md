# Project Wikis Junction Table Migration

## Overview
This migration creates a `project_wikis` junction table to efficiently combine data from `indexing_runs` and `wiki_generation_runs` tables. This replaces the complex cross-table queries with a single, optimized table.

## Migration File
- **Location**: `/supabase/migrations/20250814092500_add_project_wikis_junction_table.sql`
- **Name**: Follows project naming convention `YYYYMMDDHHMMSS_descriptive_name.sql`

## Migration Steps

### 1. Apply the Migration
The migration follows the project's standard patterns:

```bash
# Migration will be applied automatically by Supabase
# Or apply manually via Supabase Dashboard → SQL Editor
```

### 2. Populate with Existing Data
After creating the table, populate it with existing data:

```sql
SELECT public.populate_project_wikis();
```

### 3. Verify Migration
Check that data was populated correctly:

```sql
SELECT COUNT(*) FROM public.project_wikis;
SELECT * FROM public.project_wikis LIMIT 5;
```

### 4. Clean Up (Optional)
Drop the population function after use:

```sql
DROP FUNCTION IF EXISTS public.populate_project_wikis();
```

## Migration Features

### Following Project Conventions
- ✅ **Idempotent**: Uses `CREATE TABLE IF NOT EXISTS`
- ✅ **RLS Policies**: Proper access control with policy drops/creates
- ✅ **Indexes**: Performance-optimized with `CREATE INDEX IF NOT EXISTS`
- ✅ **Triggers**: Reuses existing `set_updated_at()` function
- ✅ **Constraints**: Proper CHECK constraints and foreign keys
- ✅ **Schema**: Uses `public.` schema prefix consistently

### Performance Optimizations
- **Composite Index**: Optimized for public wikis query
- **Denormalized Fields**: Frequently accessed data stored locally
- **Proper Constraints**: Ensures data integrity

### Access Control
- **Public Access**: Email uploads with public access level
- **User Access**: Users can see their own project wikis
- **System Control**: Backend manages all write operations

## API Changes

The migration enables a new, more efficient endpoint:
- `/api/indexing-runs-with-wikis` → Uses simple `SELECT` from `project_wikis`
- Eliminates complex cross-table queries
- Provides `indexing_run_id` directly (no regex parsing needed)
- Graceful fallback when junction table doesn't exist yet

## Backward Compatibility

The migration maintains full backward compatibility:
- Existing endpoints continue to work
- No breaking changes to existing API contracts
- New junction table supplements existing tables
- Backend endpoint auto-detects table availability