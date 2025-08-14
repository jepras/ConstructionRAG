-- Migration: Add project_wikis junction table
-- Date: 2025-08-14
-- Description: Creates junction table to efficiently combine indexing_runs with wiki_generation_runs for public project browsing

-- 1) Create junction table (idempotent)
CREATE TABLE IF NOT EXISTS public.project_wikis (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  indexing_run_id UUID NOT NULL REFERENCES public.indexing_runs(id) ON DELETE CASCADE,
  wiki_run_id UUID NOT NULL REFERENCES public.wiki_generation_runs(id) ON DELETE CASCADE,
  project_id UUID REFERENCES public.projects(id) ON DELETE CASCADE,
  
  -- Denormalized fields for performance
  project_name TEXT,
  upload_type TEXT NOT NULL CHECK (upload_type IN ('email', 'user_project')),
  access_level TEXT NOT NULL CHECK (access_level IN ('public','auth','owner','private')),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  
  -- Wiki-specific metadata
  pages_count INTEGER DEFAULT 0,
  total_word_count INTEGER DEFAULT 0,
  wiki_status TEXT NOT NULL CHECK (wiki_status IN ('pending', 'running', 'completed', 'failed')),
  
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  
  UNIQUE(indexing_run_id, wiki_run_id)
);

-- 2) Updated_at trigger (reuse existing function)
DROP TRIGGER IF EXISTS trg_project_wikis_updated_at ON public.project_wikis;
CREATE TRIGGER trg_project_wikis_updated_at
BEFORE UPDATE ON public.project_wikis
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- 3) Indexes for performance
CREATE INDEX IF NOT EXISTS idx_project_wikis_access_level ON public.project_wikis(access_level);
CREATE INDEX IF NOT EXISTS idx_project_wikis_upload_type ON public.project_wikis(upload_type);
CREATE INDEX IF NOT EXISTS idx_project_wikis_user_id ON public.project_wikis(user_id);
CREATE INDEX IF NOT EXISTS idx_project_wikis_project_id ON public.project_wikis(project_id);
CREATE INDEX IF NOT EXISTS idx_project_wikis_created_at ON public.project_wikis(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_project_wikis_wiki_status ON public.project_wikis(wiki_status);

-- Composite index for public wikis query
CREATE INDEX IF NOT EXISTS idx_project_wikis_public_completed ON public.project_wikis(access_level, upload_type, wiki_status, created_at DESC) 
WHERE access_level = 'public' AND upload_type = 'email' AND wiki_status = 'completed';

-- 4) RLS Policies
ALTER TABLE public.project_wikis ENABLE ROW LEVEL SECURITY;

-- Drop existing policies first
DROP POLICY IF EXISTS project_wikis_select_public ON public.project_wikis;
DROP POLICY IF EXISTS project_wikis_select_owner ON public.project_wikis;
DROP POLICY IF EXISTS project_wikis_insert_system ON public.project_wikis;
DROP POLICY IF EXISTS project_wikis_update_system ON public.project_wikis;
DROP POLICY IF EXISTS project_wikis_delete_system ON public.project_wikis;

-- SELECT: Public can view public email uploads + users can view their own
CREATE POLICY project_wikis_select_public ON public.project_wikis
FOR SELECT USING (
  (access_level = 'public' AND upload_type = 'email') OR
  (user_id::text = coalesce((current_setting('request.jwt.claims', true)::jsonb ->> 'sub')::text, ''))
);

-- INSERT/UPDATE/DELETE: System only (managed by backend)
CREATE POLICY project_wikis_insert_system ON public.project_wikis
FOR INSERT WITH CHECK (auth.role() = 'service_role');

CREATE POLICY project_wikis_update_system ON public.project_wikis
FOR UPDATE USING (auth.role() = 'service_role');

CREATE POLICY project_wikis_delete_system ON public.project_wikis
FOR DELETE USING (auth.role() = 'service_role');

-- 5) Population function (temporary for migration)
CREATE OR REPLACE FUNCTION public.populate_project_wikis()
RETURNS INTEGER AS $$
DECLARE
  row_count INTEGER := 0;
  wiki_run RECORD;
  indexing_run RECORD;
BEGIN
  -- Process all completed wiki runs
  FOR wiki_run IN 
    SELECT * FROM public.wiki_generation_runs 
    WHERE status = 'completed' AND pages_metadata IS NOT NULL
  LOOP
    -- Get corresponding indexing run
    SELECT * INTO indexing_run 
    FROM public.indexing_runs 
    WHERE id = wiki_run.indexing_run_id;
    
    IF FOUND THEN
      -- Insert into junction table (idempotent)
      INSERT INTO public.project_wikis (
        indexing_run_id,
        wiki_run_id,
        project_id,
        project_name,
        upload_type,
        access_level,
        user_id,
        pages_count,
        total_word_count,
        wiki_status,
        created_at,
        updated_at
      ) VALUES (
        indexing_run.id,
        wiki_run.id,
        wiki_run.project_id,
        COALESCE(wiki_run.project_name, 'Untitled Project'),
        indexing_run.upload_type,
        COALESCE(indexing_run.access_level, 'private'),
        indexing_run.user_id,
        CASE 
          WHEN wiki_run.pages_metadata IS NOT NULL 
          THEN jsonb_array_length(wiki_run.pages_metadata::jsonb)
          ELSE 0 
        END,
        COALESCE(wiki_run.total_word_count, 0),
        wiki_run.status,
        COALESCE(wiki_run.created_at, now()),
        COALESCE(wiki_run.updated_at, now())
      )
      ON CONFLICT (indexing_run_id, wiki_run_id) DO NOTHING;
      
      row_count := row_count + 1;
    END IF;
  END LOOP;
  
  RETURN row_count;
END;
$$ LANGUAGE plpgsql;

-- 6) Auto-populate with existing data (commented out - run manually)
-- SELECT public.populate_project_wikis();

-- 7) Clean up function after migration (commented out - run manually)
-- DROP FUNCTION IF EXISTS public.populate_project_wikis();