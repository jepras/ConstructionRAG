-- Projects V2: owner-only CRUD, access_level column, RLS, indexes, updated_at trigger
-- Idempotent migration to align with API redesign plan

-- 1) Table create or alter
CREATE TABLE IF NOT EXISTS public.projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  access_level TEXT NOT NULL DEFAULT 'owner' CHECK (access_level IN ('public','auth','owner','private')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Add columns if the table pre-existed without them
DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='projects' AND column_name='access_level'
  ) THEN
    ALTER TABLE public.projects ADD COLUMN access_level TEXT NOT NULL DEFAULT 'owner' CHECK (access_level IN ('public','auth','owner','private'));
  END IF;
END $$;

-- 2) Updated_at trigger
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_projects_updated_at ON public.projects;
CREATE TRIGGER trg_projects_updated_at
BEFORE UPDATE ON public.projects
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- 3) Indexes
CREATE INDEX IF NOT EXISTS idx_projects_user_id ON public.projects(user_id);
CREATE INDEX IF NOT EXISTS idx_projects_access_level ON public.projects(access_level);

-- 4) RLS Policies
ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;

-- SELECT: owner only for MVP
DROP POLICY IF EXISTS projects_select_owner ON public.projects;
CREATE POLICY projects_select_owner ON public.projects
FOR SELECT USING (
  user_id::text = coalesce((current_setting('request.jwt.claims', true)::jsonb ->> 'sub')::text, '')
);

-- INSERT: only as oneself
DROP POLICY IF EXISTS projects_insert_self ON public.projects;
CREATE POLICY projects_insert_self ON public.projects
FOR INSERT WITH CHECK (
  user_id::text = coalesce((current_setting('request.jwt.claims', true)::jsonb ->> 'sub')::text, '')
);

-- UPDATE: owner only
DROP POLICY IF EXISTS projects_update_owner ON public.projects;
CREATE POLICY projects_update_owner ON public.projects
FOR UPDATE USING (
  user_id::text = coalesce((current_setting('request.jwt.claims', true)::jsonb ->> 'sub')::text, '')
)
WITH CHECK (
  user_id::text = coalesce((current_setting('request.jwt.claims', true)::jsonb ->> 'sub')::text, '')
);

-- DELETE: owner only
DROP POLICY IF EXISTS projects_delete_owner ON public.projects;
CREATE POLICY projects_delete_owner ON public.projects
FOR DELETE USING (
  user_id::text = coalesce((current_setting('request.jwt.claims', true)::jsonb ->> 'sub')::text, '')
);

-- 5) Ensure existing referencing FKs are present (idempotent in prior migrations)
-- Documents/indexing_runs/wiki_generation_runs/query_runs already reference projects(id) with ON DELETE CASCADE


