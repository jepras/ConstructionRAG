-- Migration: Add auto-sync trigger for project_wikis junction table
-- Date: 2025-08-14
-- Description: Automatically populate project_wikis when wiki generation completes

-- 1) Create trigger function to sync project_wikis
CREATE OR REPLACE FUNCTION public.sync_project_wikis()
RETURNS TRIGGER AS $$
DECLARE
  indexing_run RECORD;
  project_name_value TEXT;
BEGIN
  -- Only sync when status becomes 'completed'
  IF NEW.status = 'completed' AND (OLD.status IS NULL OR OLD.status != 'completed') THEN
    -- Get indexing run data
    SELECT * INTO indexing_run 
    FROM public.indexing_runs 
    WHERE id = NEW.indexing_run_id;
    
    IF FOUND THEN
      -- Get project name if project_id exists
      IF NEW.project_id IS NOT NULL THEN
        SELECT name INTO project_name_value 
        FROM public.projects 
        WHERE id = NEW.project_id;
      ELSE
        project_name_value := 'Untitled Project';
      END IF;
      
      -- Insert or update junction table
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
        NEW.id,
        NEW.project_id,
        COALESCE(project_name_value, 'Untitled Project'),
        COALESCE(NEW.upload_type, 'user_project'),
        COALESCE(NEW.access_level, indexing_run.access_level, 'private'),
        COALESCE(NEW.user_id, indexing_run.user_id),
        CASE 
          WHEN NEW.pages_metadata IS NOT NULL AND NEW.pages_metadata != '{}'::jsonb
          THEN jsonb_array_length(NEW.pages_metadata::jsonb)
          ELSE 0 
        END,
        0, -- total_word_count - not available in wiki_generation_runs
        NEW.status,
        COALESCE(NEW.created_at, now()),
        COALESCE(NEW.updated_at, now())
      )
      ON CONFLICT (indexing_run_id, wiki_run_id) 
      DO UPDATE SET
        wiki_status = NEW.status,
        pages_count = CASE 
          WHEN NEW.pages_metadata IS NOT NULL AND NEW.pages_metadata != '{}'::jsonb
          THEN jsonb_array_length(NEW.pages_metadata::jsonb)
          ELSE 0 
        END,
        access_level = COALESCE(NEW.access_level, EXCLUDED.access_level),
        updated_at = now();
    END IF;
  END IF;
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 2) Create trigger
DROP TRIGGER IF EXISTS sync_project_wikis_trigger ON public.wiki_generation_runs;
CREATE TRIGGER sync_project_wikis_trigger
  AFTER INSERT OR UPDATE ON public.wiki_generation_runs
  FOR EACH ROW EXECUTE FUNCTION public.sync_project_wikis();

-- 3) Update backfill function to handle missing columns gracefully
CREATE OR REPLACE FUNCTION public.populate_project_wikis()
RETURNS INTEGER AS $$
DECLARE
  row_count INTEGER := 0;
  wiki_run RECORD;
  indexing_run RECORD;
  project_name_value TEXT;
BEGIN
  -- Process all completed wiki runs
  FOR wiki_run IN 
    SELECT * FROM public.wiki_generation_runs 
    WHERE status = 'completed' 
  LOOP
    -- Get corresponding indexing run
    SELECT * INTO indexing_run 
    FROM public.indexing_runs 
    WHERE id = wiki_run.indexing_run_id;
    
    IF FOUND THEN
      -- Get project name if project_id exists
      IF wiki_run.project_id IS NOT NULL THEN
        SELECT name INTO project_name_value 
        FROM public.projects 
        WHERE id = wiki_run.project_id;
      ELSE
        project_name_value := 'Untitled Project';
      END IF;
      
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
        COALESCE(project_name_value, 'Untitled Project'),
        COALESCE(wiki_run.upload_type, 'user_project'),
        COALESCE(wiki_run.access_level, indexing_run.access_level, 'private'),
        COALESCE(wiki_run.user_id, indexing_run.user_id),
        CASE 
          WHEN wiki_run.pages_metadata IS NOT NULL AND wiki_run.pages_metadata != '{}'::jsonb
          THEN jsonb_array_length(wiki_run.pages_metadata::jsonb)
          ELSE 0 
        END,
        0, -- total_word_count - not available in current schema
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

-- 4) Run backfill automatically (commented out - run manually if needed)
-- SELECT public.populate_project_wikis();