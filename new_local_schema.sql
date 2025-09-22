

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;


CREATE EXTENSION IF NOT EXISTS "pg_net" WITH SCHEMA "extensions";






COMMENT ON SCHEMA "public" IS 'standard public schema';



CREATE EXTENSION IF NOT EXISTS "pg_graphql" WITH SCHEMA "graphql";






CREATE EXTENSION IF NOT EXISTS "pg_stat_statements" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "pgcrypto" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "supabase_vault" WITH SCHEMA "vault";






CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "vector" WITH SCHEMA "public";






CREATE TYPE "public"."access_level" AS ENUM (
    'public',
    'auth',
    'owner',
    'private'
);


ALTER TYPE "public"."access_level" OWNER TO "postgres";


CREATE TYPE "public"."analysis_status" AS ENUM (
    'pending',
    'running',
    'completed',
    'failed'
);


ALTER TYPE "public"."analysis_status" OWNER TO "postgres";


CREATE TYPE "public"."checklist_status" AS ENUM (
    'found',
    'missing',
    'risk',
    'conditions',
    'pending_clarification'
);


ALTER TYPE "public"."checklist_status" OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."cleanup_expired_email_uploads"() RETURNS integer
    LANGUAGE "plpgsql"
    AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM documents 
    WHERE upload_type = 'email' 
    AND expires_at < NOW();
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RETURN deleted_count;
END;
$$;


ALTER FUNCTION "public"."cleanup_expired_email_uploads"() OWNER TO "postgres";


COMMENT ON FUNCTION "public"."cleanup_expired_email_uploads"() IS 'Removes expired email upload documents (older than 30 days)';



CREATE OR REPLACE FUNCTION "public"."delete_email_upload_folders_production"() RETURNS TABLE("deleted_path" "text", "objects_deleted" integer)
    LANGUAGE "plpgsql"
    AS $$
  DECLARE
      folder_record record;
      deleted_count integer;
      subfolder_name text;
  BEGIN
      -- Loop through each deletable subfolder in email-uploads
      FOR folder_record IN
          SELECT DISTINCT
              CASE
                  WHEN name LIKE 'email-uploads/%/%' THEN
                      split_part(substring(name from 15), '/', 1)
                  WHEN name LIKE 'email-uploads/%' AND name != 'email-uploads/' THEN
                      substring(name from 15)
              END as folder_name
          FROM storage.objects
          WHERE bucket_id = 'pipeline-assets'
          AND name LIKE 'email-uploads/%'
          AND name NOT LIKE 'email-uploads/index-runs/%'
          AND name != 'email-uploads/index-runs'
          AND name != 'email-uploads/'
      LOOP
          IF folder_record.folder_name IS NOT NULL AND folder_record.folder_name != 'index-runs' THEN
              subfolder_name := 'email-uploads/' || folder_record.folder_name;

              -- Delete all objects in this subfolder
              DELETE FROM storage.objects
              WHERE bucket_id = 'pipeline-assets'
              AND (name LIKE subfolder_name || '/%' OR name = subfolder_name);

              GET DIAGNOSTICS deleted_count = ROW_COUNT;

              IF deleted_count > 0 THEN
                  RETURN QUERY SELECT subfolder_name, deleted_count;
              END IF;
          END IF;
      END LOOP;
  END;
  $$;


ALTER FUNCTION "public"."delete_email_upload_folders_production"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."delete_folders_production"() RETURNS TABLE("deleted_path" "text", "objects_deleted" integer)
    LANGUAGE "plpgsql"
    AS $$
  DECLARE
      folder_record record;
      deleted_count integer;
  BEGIN
      -- Loop through each deletable folder
      FOR folder_record IN
          SELECT DISTINCT
              CASE
                  WHEN position('/' in name) > 0 THEN
                      substring(name from 1 for position('/' in name) - 1)
                  ELSE
                      name
              END as folder_name
          FROM storage.objects
          WHERE bucket_id = 'pipeline-assets'
          AND name NOT LIKE 'users/%'
          AND name NOT LIKE 'email-uploads/%'
          AND name != 'users'
          AND name != 'email-uploads'
      LOOP
          -- Delete all objects in this folder
          DELETE FROM storage.objects
          WHERE bucket_id = 'pipeline-assets'
          AND (name LIKE folder_record.folder_name || '/%' OR name = folder_record.folder_name);

          GET DIAGNOSTICS deleted_count = ROW_COUNT;

          RETURN QUERY SELECT folder_record.folder_name::text, deleted_count;
      END LOOP;
  END;
  $$;


ALTER FUNCTION "public"."delete_folders_production"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."delete_folders_test"() RETURNS TABLE("deleted_path" "text", "objects_deleted" integer)
    LANGUAGE "plpgsql"
    AS $$
  DECLARE
      folder_record record;
      deleted_count integer;
  BEGIN
      -- Loop through each deletable folder
      FOR folder_record IN
          SELECT DISTINCT
              CASE
                  WHEN position('/' in name) > 0 THEN
                      substring(name from 1 for position('/' in name) - 1)
                  ELSE
                      name
              END as folder_name
          FROM storage.objects
          WHERE bucket_id = 'pipeline-assets-test'
          AND name NOT LIKE 'users/%'
          AND name NOT LIKE 'email-uploads/%'
          AND name != 'users'
          AND name != 'email-uploads'
      LOOP
          -- Delete all objects in this folder
          DELETE FROM storage.objects
          WHERE bucket_id = 'pipeline-assets-test'
          AND (name LIKE folder_record.folder_name || '/%' OR name = folder_record.folder_name);

          GET DIAGNOSTICS deleted_count = ROW_COUNT;

          RETURN QUERY SELECT folder_record.folder_name::text, deleted_count;
      END LOOP;
  END;
  $$;


ALTER FUNCTION "public"."delete_folders_test"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."delete_users_folders_production"() RETURNS TABLE("deleted_path" "text", "objects_deleted" integer)
    LANGUAGE "plpgsql"
    AS $$
  DECLARE
      folder_record record;
      deleted_count integer;
      user_folder_name text;
  BEGIN
      -- Loop through each deletable user folder
      FOR folder_record IN
          SELECT DISTINCT
              CASE
                  WHEN name LIKE 'users/%/%' THEN
                      split_part(substring(name from 7), '/', 1)
                  WHEN name LIKE 'users/%' AND name != 'users/' THEN
                      substring(name from 7)
              END as folder_name
          FROM storage.objects
          WHERE bucket_id = 'pipeline-assets'
          AND name LIKE 'users/%'
          AND name NOT LIKE 'users/a4be935d-dd17-4db2-aa4e-b4989277bb1a/%'
          AND name != 'users/a4be935d-dd17-4db2-aa4e-b4989277bb1a'
          AND name != 'users/'
      LOOP
          IF folder_record.folder_name IS NOT NULL AND folder_record.folder_name !=
  'a4be935d-dd17-4db2-aa4e-b4989277bb1a' THEN
              user_folder_name := 'users/' || folder_record.folder_name;

              -- Delete all objects in this user folder
              DELETE FROM storage.objects
              WHERE bucket_id = 'pipeline-assets'
              AND (name LIKE user_folder_name || '/%' OR name = user_folder_name);

              GET DIAGNOSTICS deleted_count = ROW_COUNT;

              IF deleted_count > 0 THEN
                  RETURN QUERY SELECT user_folder_name, deleted_count;
              END IF;
          END IF;
      END LOOP;
  END;
  $$;


ALTER FUNCTION "public"."delete_users_folders_production"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."empty_database_except_users_improved"() RETURNS "void"
    LANGUAGE "plpgsql"
    AS $$
  DECLARE
      table_list text;
  BEGIN
      -- Get comma-separated list of all tables except user_profiles
      SELECT string_agg(quote_ident(t.table_name), ', ')
      INTO table_list
      FROM information_schema.tables t
      WHERE t.table_schema = 'public'
        AND t.table_type = 'BASE TABLE'
        AND t.table_name != 'user_profiles';

      -- TRUNCATE all tables at once with CASCADE to handle foreign keys
      IF table_list IS NOT NULL THEN
          EXECUTE 'TRUNCATE ' || table_list || ' RESTART IDENTITY CASCADE';
          RAISE NOTICE 'Successfully truncated tables: %', table_list;
      ELSE
          RAISE NOTICE 'No tables to truncate besides user_profiles';
      END IF;
  END;
  $$;


ALTER FUNCTION "public"."empty_database_except_users_improved"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."extract_indexing_run_id_from_user_path"("file_path" "text") RETURNS "uuid"
    LANGUAGE "plpgsql" STABLE
    AS $$
BEGIN
    -- Extract UUID from the path pattern: users/.../index-runs/{uuid}/wiki/...
    -- Use regex to match UUID pattern after 'index-runs/'
    RETURN (
        SELECT (regexp_match(
            file_path, 
            'users/[^/]+/projects/[^/]+/index-runs/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})', 
            'i'
        ))[1]::uuid
    );
EXCEPTION
    WHEN others THEN
        RETURN NULL;
END;
$$;


ALTER FUNCTION "public"."extract_indexing_run_id_from_user_path"("file_path" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_all_auth_users"() RETURNS TABLE("id" "uuid", "email" "text", "email_confirmed_at" timestamp with time zone, "created_at" timestamp with time zone)
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
BEGIN
    RETURN QUERY
    SELECT au.id, au.email, au.email_confirmed_at, au.created_at
    FROM auth.users au
    ORDER BY au.created_at DESC;
END;
$$;


ALTER FUNCTION "public"."get_all_auth_users"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_auth_user_by_email"("user_email" "text") RETURNS TABLE("id" "uuid", "email" "text", "email_confirmed_at" timestamp with time zone, "created_at" timestamp with time zone, "updated_at" timestamp with time zone)
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
BEGIN
    RETURN QUERY
    SELECT au.id, au.email, au.email_confirmed_at, au.created_at, au.updated_at
    FROM auth.users au
    WHERE au.email = user_email;
END;
$$;


ALTER FUNCTION "public"."get_auth_user_by_email"("user_email" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_recent_query_performance"("hours_back" integer DEFAULT 24) RETURNS TABLE("total_queries" bigint, "successful_queries" bigint, "failed_queries" bigint, "avg_response_time_ms" numeric, "success_rate" numeric, "avg_query_processing_time" numeric, "avg_retrieval_time" numeric, "avg_generation_time" numeric)
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*) as total_queries,
        COUNT(CASE WHEN final_response IS NOT NULL THEN 1 END) as successful_queries,
        COUNT(CASE WHEN error_message IS NOT NULL THEN 1 END) as failed_queries,
        AVG(response_time_ms) as avg_response_time_ms,
        CASE 
            WHEN COUNT(*) > 0 THEN 
                (COUNT(CASE WHEN final_response IS NOT NULL THEN 1 END)::NUMERIC / COUNT(*)::NUMERIC) * 100
            ELSE 0 
        END as success_rate,
        AVG((step_timings->>'query_processing')::float) as avg_query_processing_time,
        AVG((step_timings->>'retrieval')::float) as avg_retrieval_time,
        AVG((step_timings->>'generation')::float) as avg_generation_time
    FROM query_runs
    WHERE created_at >= NOW() - INTERVAL '1 hour' * hours_back;
END;
$$;


ALTER FUNCTION "public"."get_recent_query_performance"("hours_back" integer) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_storage_path_for_document"("doc_upload_type" "text", "doc_upload_id" "text", "doc_user_id" "uuid", "doc_project_id" "uuid", "doc_index_run_id" "uuid", "doc_id" "uuid", "file_type" "text", "filename" "text") RETURNS "text"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    IF doc_upload_type = 'email' THEN
        RETURN 'email-uploads/' || doc_upload_id || '/processing/' || doc_id || '/' || file_type || '/' || filename;
    ELSE
        RETURN 'users/' || doc_user_id || '/projects/' || doc_project_id || '/index-runs/' || doc_index_run_id || '/' || doc_id || '/' || file_type || '/' || filename;
    END IF;
END;
$$;


ALTER FUNCTION "public"."get_storage_path_for_document"("doc_upload_type" "text", "doc_upload_id" "text", "doc_user_id" "uuid", "doc_project_id" "uuid", "doc_index_run_id" "uuid", "doc_id" "uuid", "file_type" "text", "filename" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_storage_usage_stats"("user_uuid" "uuid" DEFAULT NULL::"uuid") RETURNS TABLE("upload_type" "text", "total_documents" bigint, "total_size_bytes" bigint, "avg_file_size_bytes" numeric)
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    IF user_uuid IS NOT NULL THEN
        RETURN QUERY
        SELECT 
            d.upload_type,
            COUNT(*) as total_documents,
            COALESCE(SUM(d.file_size), 0) as total_size_bytes,
            COALESCE(AVG(d.file_size), 0) as avg_file_size_bytes
        FROM documents d
        WHERE d.user_id = user_uuid
        GROUP BY d.upload_type;
    ELSE
        RETURN QUERY
        SELECT 
            d.upload_type,
            COUNT(*) as total_documents,
            COALESCE(SUM(d.file_size), 0) as total_size_bytes,
            COALESCE(AVG(d.file_size), 0) as avg_file_size_bytes
        FROM documents d
        GROUP BY d.upload_type;
    END IF;
END;
$$;


ALTER FUNCTION "public"."get_storage_usage_stats"("user_uuid" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."list_deletable_email_upload_folders_production"() RETURNS TABLE("folder_path" "text", "object_count" bigint)
    LANGUAGE "plpgsql"
    AS $$
  BEGIN
      RETURN QUERY
      WITH email_upload_objects AS (
          SELECT
              name,
              -- Extract the subfolder name after email-uploads/
              CASE
                  WHEN name LIKE 'email-uploads/%/%' THEN
                      'email-uploads/' || split_part(substring(name from 15), '/', 1) || '/'
                  WHEN name LIKE 'email-uploads/%' AND name != 'email-uploads/' THEN
                      'email-uploads/' || substring(name from 15) || '/'
              END as subfolder_name
          FROM storage.objects
          WHERE bucket_id = 'pipeline-assets'
          AND name LIKE 'email-uploads/%'
          AND name NOT LIKE 'email-uploads/index-runs/%'
          AND name != 'email-uploads/index-runs'
          AND name != 'email-uploads/'
      )
      SELECT DISTINCT
          subfolder_name as folder_path,
          COUNT(*) as object_count
      FROM email_upload_objects
      WHERE subfolder_name IS NOT NULL
      GROUP BY subfolder_name
      ORDER BY subfolder_name;
  END;
  $$;


ALTER FUNCTION "public"."list_deletable_email_upload_folders_production"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."list_deletable_folders_production"() RETURNS TABLE("folder_path" "text", "object_count" bigint)
    LANGUAGE "plpgsql"
    AS $$
  BEGIN
      RETURN QUERY
      WITH folder_objects AS (
          SELECT
              name,
              CASE
                  WHEN position('/' in name) > 0 THEN
                      substring(name from 1 for position('/' in name))
                  ELSE
                      name || '/'
              END as folder_name
          FROM storage.objects
          WHERE bucket_id = 'pipeline-assets'
          AND name NOT LIKE 'users/%'
          AND name NOT LIKE 'email-uploads/%'
          AND name != 'users'
          AND name != 'email-uploads'
      )
      SELECT DISTINCT
          folder_name as folder_path,
          COUNT(*) as object_count
      FROM folder_objects
      GROUP BY folder_name
      ORDER BY folder_name;
  END;
  $$;


ALTER FUNCTION "public"."list_deletable_folders_production"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."list_deletable_folders_test"() RETURNS TABLE("folder_path" "text", "object_count" bigint)
    LANGUAGE "plpgsql"
    AS $$
  BEGIN
      RETURN QUERY
      WITH folder_objects AS (
          SELECT
              name,
              CASE
                  WHEN position('/' in name) > 0 THEN
                      substring(name from 1 for position('/' in name))
                  ELSE
                      name || '/'
              END as folder_name
          FROM storage.objects
          WHERE bucket_id = 'pipeline-assets'
          AND name NOT LIKE 'users/%'
          AND name NOT LIKE 'email-uploads/%'
          AND name != 'users'
          AND name != 'email-uploads'
      )
      SELECT DISTINCT
          folder_name as folder_path,
          COUNT(*) as object_count
      FROM folder_objects
      GROUP BY folder_name
      ORDER BY folder_name;
  END;
  $$;


ALTER FUNCTION "public"."list_deletable_folders_test"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."list_deletable_users_folders_production"() RETURNS TABLE("folder_path" "text", "object_count" bigint)
    LANGUAGE "plpgsql"
    AS $$
  BEGIN
      RETURN QUERY
      WITH users_objects AS (
          SELECT
              name,
              -- Extract the user folder name after users/
              CASE
                  WHEN name LIKE 'users/%/%' THEN
                      'users/' || split_part(substring(name from 7), '/', 1) || '/'
                  WHEN name LIKE 'users/%' AND name != 'users/' THEN
                      'users/' || substring(name from 7) || '/'
              END as user_folder_name
          FROM storage.objects
          WHERE bucket_id = 'pipeline-assets'
          AND name LIKE 'users/%'
          AND name NOT LIKE 'users/a4be935d-dd17-4db2-aa4e-b4989277bb1a/%'
          AND name != 'users/a4be935d-dd17-4db2-aa4e-b4989277bb1a'
          AND name != 'users/'
      )
      SELECT DISTINCT
          user_folder_name as folder_path,
          COUNT(*) as object_count
      FROM users_objects
      WHERE user_folder_name IS NOT NULL
      GROUP BY user_folder_name
      ORDER BY user_folder_name;
  END;
  $$;


ALTER FUNCTION "public"."list_deletable_users_folders_production"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."match_chunks"("query_embedding" "public"."vector", "match_threshold" double precision, "match_count" integer, "indexing_run_id_filter" "text" DEFAULT NULL::"text") RETURNS TABLE("id" "uuid", "content" "text", "metadata" "jsonb", "embedding_1024" "public"."vector", "document_id" "uuid", "indexing_run_id" "uuid", "similarity" double precision)
    LANGUAGE "plpgsql"
    AS $$
BEGIN
  -- IMPORTANT: We completely IGNORE match_threshold to ensure we get K nearest neighbors
  -- The threshold should be applied in application code if needed
  
  RETURN QUERY
  SELECT 
    dc.id,
    dc.content,
    dc.metadata,
    dc.embedding_1024,
    dc.document_id,
    dc.indexing_run_id,
    1 - (dc.embedding_1024 <=> query_embedding) as similarity
  FROM document_chunks dc
  WHERE 
    dc.embedding_1024 IS NOT NULL
    AND (
      indexing_run_id_filter IS NULL 
      OR dc.indexing_run_id::text = indexing_run_id_filter
    )
  ORDER BY dc.embedding_1024 <=> query_embedding ASC
  LIMIT LEAST(match_count, 200);
END;
$$;


ALTER FUNCTION "public"."match_chunks"("query_embedding" "public"."vector", "match_threshold" double precision, "match_count" integer, "indexing_run_id_filter" "text") OWNER TO "postgres";


COMMENT ON FUNCTION "public"."match_chunks"("query_embedding" "public"."vector", "match_threshold" double precision, "match_count" integer, "indexing_run_id_filter" "text") IS 'REVERTED to working version: Returns K nearest neighbors using HNSW index. Threshold parameter is IGNORED.';



CREATE OR REPLACE FUNCTION "public"."match_chunks_with_threshold"("query_embedding" "public"."vector", "match_threshold" double precision, "match_count" integer, "indexing_run_id_filter" "text" DEFAULT NULL::"text") RETURNS TABLE("id" "uuid", "content" "text", "metadata" "jsonb", "embedding_1024" "public"."vector", "document_id" "uuid", "indexing_run_id" "uuid", "similarity" double precision)
    LANGUAGE "sql"
    AS $$
  SELECT * FROM (
    SELECT 
      id,
      content,
      metadata,
      embedding_1024,
      document_id,
      indexing_run_id,
      1 - (embedding_1024 <=> query_embedding) as similarity
    FROM document_chunks
    WHERE 
      embedding_1024 IS NOT NULL
      AND (indexing_run_id_filter IS NULL OR indexing_run_id::text = indexing_run_id_filter)
    ORDER BY embedding_1024 <=> query_embedding ASC
    LIMIT LEAST(match_count, 200)
  ) AS nearest_neighbors
  WHERE similarity > match_threshold;
$$;


ALTER FUNCTION "public"."match_chunks_with_threshold"("query_embedding" "public"."vector", "match_threshold" double precision, "match_count" integer, "indexing_run_id_filter" "text") OWNER TO "postgres";


COMMENT ON FUNCTION "public"."match_chunks_with_threshold"("query_embedding" "public"."vector", "match_threshold" double precision, "match_count" integer, "indexing_run_id_filter" "text") IS 'Vector similarity search that finds K nearest neighbors first, then filters by threshold. Better performance but may return fewer than K results.';



CREATE OR REPLACE FUNCTION "public"."match_documents"("query_embedding" "public"."vector", "match_threshold" double precision DEFAULT 0.7, "match_count" integer DEFAULT 5, "filter_indexing_run_id" "uuid" DEFAULT NULL::"uuid") RETURNS TABLE("content" "text", "metadata" "jsonb", "similarity" double precision)
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
BEGIN
  RETURN QUERY
  SELECT 
    document_chunks.content,
    document_chunks.metadata,
    (1 - (document_chunks.embedding_1024 <=> query_embedding)) as similarity
  FROM document_chunks
  WHERE 
    (filter_indexing_run_id IS NULL OR document_chunks.indexing_run_id = filter_indexing_run_id)
    AND document_chunks.embedding_1024 IS NOT NULL
    AND (1 - (document_chunks.embedding_1024 <=> query_embedding)) > match_threshold
  ORDER BY document_chunks.embedding_1024 <=> query_embedding
  LIMIT match_count;
END;
$$;


ALTER FUNCTION "public"."match_documents"("query_embedding" "public"."vector", "match_threshold" double precision, "match_count" integer, "filter_indexing_run_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."populate_project_wikis"() RETURNS integer
    LANGUAGE "plpgsql"
    AS $$
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
$$;


ALTER FUNCTION "public"."populate_project_wikis"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."set_updated_at"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."set_updated_at"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."sync_project_wikis"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
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
$$;


ALTER FUNCTION "public"."sync_project_wikis"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."test_migration_function"() RETURNS "text"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    RETURN 'Migration system is working correctly!';
END;
$$;


ALTER FUNCTION "public"."test_migration_function"() OWNER TO "postgres";


COMMENT ON FUNCTION "public"."test_migration_function"() IS 'Test function to verify migration system';



CREATE OR REPLACE FUNCTION "public"."update_updated_at_column"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."update_updated_at_column"() OWNER TO "postgres";

SET default_tablespace = '';

SET default_table_access_method = "heap";


CREATE TABLE IF NOT EXISTS "public"."checklist_analysis_runs" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "indexing_run_id" "uuid" NOT NULL,
    "user_id" "uuid",
    "checklist_name" character varying(255) NOT NULL,
    "checklist_content" "text" NOT NULL,
    "model_name" character varying(100) NOT NULL,
    "status" "public"."analysis_status" DEFAULT 'pending'::"public"."analysis_status" NOT NULL,
    "raw_output" "text",
    "progress_current" integer DEFAULT 0,
    "progress_total" integer DEFAULT 0,
    "error_message" "text",
    "access_level" "public"."access_level" DEFAULT 'private'::"public"."access_level" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."checklist_analysis_runs" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."checklist_results" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "analysis_run_id" "uuid" NOT NULL,
    "item_number" character varying(50) NOT NULL,
    "item_name" character varying(500) NOT NULL,
    "status" "public"."checklist_status" NOT NULL,
    "description" "text" NOT NULL,
    "confidence_score" numeric(3,2),
    "source_document" character varying(255),
    "source_page" integer,
    "source_chunk_id" "uuid",
    "source_excerpt" "text",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "all_sources" "jsonb"
);


ALTER TABLE "public"."checklist_results" OWNER TO "postgres";


COMMENT ON COLUMN "public"."checklist_results"."all_sources" IS 'JSON array of source references: [{"document": "file.pdf", "page": 12, "excerpt": "quote"}]';



CREATE TABLE IF NOT EXISTS "public"."checklist_templates" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" "uuid",
    "name" character varying(255) NOT NULL,
    "content" "text" NOT NULL,
    "category" character varying(100) DEFAULT 'custom'::character varying NOT NULL,
    "is_public" boolean DEFAULT false,
    "access_level" "public"."access_level" DEFAULT 'private'::"public"."access_level" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."checklist_templates" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."document_chunks" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "document_id" "uuid",
    "chunk_index" integer NOT NULL,
    "content" "text" NOT NULL,
    "embedding" "public"."vector"(1536),
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "page_number" integer,
    "section_title" "text",
    "created_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."document_chunks" OWNER TO "postgres";


COMMENT ON TABLE "public"."document_chunks" IS 'Document chunks with embeddings for vector search. Updated for embedding step with voyage-multimodal-3 support.';



COMMENT ON COLUMN "public"."document_chunks"."metadata" IS 'Chunk metadata including page_number, section_title, element_category, etc.';



CREATE TABLE IF NOT EXISTS "public"."documents" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" "uuid",
    "filename" "text" NOT NULL,
    "file_size" integer,
    "file_path" "text",
    "page_count" integer,
    "status" "text" DEFAULT 'pending'::"text",
    "error_message" "text",
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    CONSTRAINT "documents_status_check" CHECK (("status" = ANY (ARRAY['pending'::"text", 'processing'::"text", 'completed'::"text", 'failed'::"text"])))
);


ALTER TABLE "public"."documents" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."indexing_run_documents" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "indexing_run_id" "uuid" NOT NULL,
    "document_id" "uuid" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."indexing_run_documents" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."indexing_runs" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "status" "text" DEFAULT 'pending'::"text" NOT NULL,
    "step_results" "jsonb" DEFAULT '{}'::"jsonb",
    "started_at" timestamp with time zone DEFAULT "now"(),
    "completed_at" timestamp with time zone,
    "error_message" "text",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "upload_type" "text" DEFAULT 'user_project'::"text",
    "project_id" "uuid",
    "pipeline_config" "jsonb" DEFAULT '{}'::"jsonb",
    "user_id" "uuid",
    "access_level" character varying(20) DEFAULT 'private'::character varying,
    "email" "text",
    "email_notifications_enabled" boolean DEFAULT true,
    CONSTRAINT "indexing_runs_status_check" CHECK (("status" = ANY (ARRAY['pending'::"text", 'running'::"text", 'completed'::"text", 'failed'::"text", 'processing'::"text"]))),
    CONSTRAINT "indexing_runs_upload_type_check" CHECK (("upload_type" = ANY (ARRAY['email'::"text", 'user_project'::"text"])))
);


ALTER TABLE "public"."indexing_runs" OWNER TO "postgres";


COMMENT ON COLUMN "public"."indexing_runs"."pipeline_config" IS 'Stores the exact pipeline configuration used for this indexing run, including all step configurations and user overrides';



COMMENT ON COLUMN "public"."indexing_runs"."email" IS 'User email for notification purposes, stored for anonymous uploads, nullable for authenticated users';



COMMENT ON COLUMN "public"."indexing_runs"."email_notifications_enabled" IS 'Whether to send email notifications when processing is complete. Defaults to true.';



CREATE TABLE IF NOT EXISTS "public"."pipeline_runs" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "document_id" "uuid",
    "status" "text" DEFAULT 'pending'::"text",
    "step_results" "jsonb" DEFAULT '{}'::"jsonb",
    "started_at" timestamp with time zone DEFAULT "now"(),
    "completed_at" timestamp with time zone,
    "error_message" "text",
    CONSTRAINT "pipeline_runs_status_check" CHECK (("status" = ANY (ARRAY['pending'::"text", 'running'::"text", 'completed'::"text", 'failed'::"text"])))
);


ALTER TABLE "public"."pipeline_runs" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."project_wikis" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "indexing_run_id" "uuid" NOT NULL,
    "wiki_run_id" "uuid" NOT NULL,
    "project_id" "uuid",
    "project_name" "text",
    "upload_type" "text" NOT NULL,
    "access_level" "text" NOT NULL,
    "user_id" "uuid",
    "pages_count" integer DEFAULT 0,
    "total_word_count" integer DEFAULT 0,
    "wiki_status" "text" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "project_wikis_access_level_check" CHECK (("access_level" = ANY (ARRAY['public'::"text", 'auth'::"text", 'owner'::"text", 'private'::"text"]))),
    CONSTRAINT "project_wikis_upload_type_check" CHECK (("upload_type" = ANY (ARRAY['email'::"text", 'user_project'::"text"]))),
    CONSTRAINT "project_wikis_wiki_status_check" CHECK (("wiki_status" = ANY (ARRAY['pending'::"text", 'running'::"text", 'completed'::"text", 'failed'::"text"])))
);


ALTER TABLE "public"."project_wikis" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."projects" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" "uuid",
    "name" "text" NOT NULL,
    "description" "text",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "access_level" "text" DEFAULT 'owner'::"text" NOT NULL,
    "deleted_at" timestamp with time zone,
    "deleted_by" "uuid",
    CONSTRAINT "projects_access_level_check" CHECK (("access_level" = ANY (ARRAY['public'::"text", 'auth'::"text", 'owner'::"text", 'private'::"text"])))
);


ALTER TABLE "public"."projects" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."queries" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" "uuid",
    "query_text" "text" NOT NULL,
    "response_text" "text",
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."queries" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."query_runs" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" "text",
    "original_query" "text" NOT NULL,
    "query_variations" "jsonb",
    "search_results" "jsonb",
    "final_response" "text",
    "performance_metrics" "jsonb",
    "quality_metrics" "jsonb",
    "response_time_ms" integer,
    "error_message" "text",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "step_timings" "jsonb",
    "access_level" character varying(20) DEFAULT 'private'::character varying,
    "pipeline_config" "jsonb" DEFAULT '{}'::"jsonb",
    "indexing_run_id" "uuid"
);


ALTER TABLE "public"."query_runs" OWNER TO "postgres";


COMMENT ON TABLE "public"."query_runs" IS 'Stores all queries processed through the query pipeline with results and metrics';



COMMENT ON COLUMN "public"."query_runs"."query_variations" IS 'JSON object containing semantic, hyde, and formal query variations';



COMMENT ON COLUMN "public"."query_runs"."search_results" IS 'Array of search results with content, similarity scores, and metadata';



COMMENT ON COLUMN "public"."query_runs"."performance_metrics" IS 'JSON object with model_used, tokens_used, confidence, sources_count';



COMMENT ON COLUMN "public"."query_runs"."quality_metrics" IS 'JSON object with relevance_score, confidence, top_similarity, result_count';



COMMENT ON COLUMN "public"."query_runs"."step_timings" IS 'JSON object containing individual step execution times in seconds (e.g., {"query_processing": 1.23, "retrieval": 2.45, "generation": 9.12})';



COMMENT ON COLUMN "public"."query_runs"."pipeline_config" IS 'Stores the exact pipeline configuration used for this query run, including step configurations and user overrides';



CREATE OR REPLACE VIEW "public"."query_analytics" AS
 SELECT "date_trunc"('day'::"text", "created_at") AS "date",
    "count"(*) AS "total_queries",
    "count"(
        CASE
            WHEN ("final_response" IS NOT NULL) THEN 1
            ELSE NULL::integer
        END) AS "successful_queries",
    "count"(
        CASE
            WHEN ("error_message" IS NOT NULL) THEN 1
            ELSE NULL::integer
        END) AS "failed_queries",
    "avg"("response_time_ms") AS "avg_response_time_ms",
    "avg"((("performance_metrics" ->> 'confidence'::"text"))::double precision) AS "avg_confidence",
    "avg"((("quality_metrics" ->> 'relevance_score'::"text"))::double precision) AS "avg_relevance_score",
    "avg"((("step_timings" ->> 'query_processing'::"text"))::double precision) AS "avg_query_processing_time",
    "avg"((("step_timings" ->> 'retrieval'::"text"))::double precision) AS "avg_retrieval_time",
    "avg"((("step_timings" ->> 'generation'::"text"))::double precision) AS "avg_generation_time"
   FROM "public"."query_runs"
  GROUP BY ("date_trunc"('day'::"text", "created_at"))
  ORDER BY ("date_trunc"('day'::"text", "created_at")) DESC;


ALTER VIEW "public"."query_analytics" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."user_config_overrides" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" "uuid" NOT NULL,
    "config_type" "text" NOT NULL,
    "config_key" "text" NOT NULL,
    "config_value" "jsonb" NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "created_at" timestamp with time zone DEFAULT "now"(),
    CONSTRAINT "user_config_overrides_config_type_check" CHECK (("config_type" = ANY (ARRAY['indexing'::"text", 'querying'::"text"])))
);


ALTER TABLE "public"."user_config_overrides" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."user_profiles" (
    "id" "uuid" NOT NULL,
    "email" "text",
    "full_name" "text",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "test_migration_column" "text" DEFAULT 'local_development_test'::"text"
);


ALTER TABLE "public"."user_profiles" OWNER TO "postgres";


COMMENT ON COLUMN "public"."user_profiles"."test_migration_column" IS 'Test column added to verify local migration system works';



CREATE TABLE IF NOT EXISTS "public"."wiki_generation_runs" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "indexing_run_id" "uuid" NOT NULL,
    "upload_type" "text" DEFAULT 'user_project'::"text" NOT NULL,
    "user_id" "uuid",
    "project_id" "uuid",
    "upload_id" "text",
    "status" "text" DEFAULT 'pending'::"text" NOT NULL,
    "language" "text" DEFAULT 'danish'::"text",
    "model" "text" DEFAULT 'google/gemini-2.5-flash'::"text",
    "step_results" "jsonb" DEFAULT '{}'::"jsonb",
    "wiki_structure" "jsonb" DEFAULT '{}'::"jsonb",
    "pages_metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "storage_path" "text",
    "started_at" timestamp with time zone DEFAULT "now"(),
    "completed_at" timestamp with time zone,
    "error_message" "text",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "access_level" character varying(20) DEFAULT 'private'::character varying,
    CONSTRAINT "wiki_generation_runs_language_check" CHECK (("language" = ANY (ARRAY['danish'::"text", 'english'::"text"]))),
    CONSTRAINT "wiki_generation_runs_status_check" CHECK (("status" = ANY (ARRAY['pending'::"text", 'running'::"text", 'completed'::"text", 'failed'::"text"]))),
    CONSTRAINT "wiki_generation_runs_upload_type_check" CHECK (("upload_type" = ANY (ARRAY['email'::"text", 'user_project'::"text"])))
);


ALTER TABLE "public"."wiki_generation_runs" OWNER TO "postgres";


ALTER TABLE ONLY "public"."checklist_analysis_runs"
    ADD CONSTRAINT "checklist_analysis_runs_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."checklist_results"
    ADD CONSTRAINT "checklist_results_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."checklist_templates"
    ADD CONSTRAINT "checklist_templates_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."document_chunks"
    ADD CONSTRAINT "document_chunks_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."documents"
    ADD CONSTRAINT "documents_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."indexing_run_documents"
    ADD CONSTRAINT "indexing_run_documents_indexing_run_id_document_id_key" UNIQUE ("indexing_run_id", "document_id");



ALTER TABLE ONLY "public"."indexing_run_documents"
    ADD CONSTRAINT "indexing_run_documents_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."indexing_runs"
    ADD CONSTRAINT "indexing_runs_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."pipeline_runs"
    ADD CONSTRAINT "pipeline_runs_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."project_wikis"
    ADD CONSTRAINT "project_wikis_indexing_run_id_wiki_run_id_key" UNIQUE ("indexing_run_id", "wiki_run_id");



ALTER TABLE ONLY "public"."project_wikis"
    ADD CONSTRAINT "project_wikis_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."projects"
    ADD CONSTRAINT "projects_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."queries"
    ADD CONSTRAINT "queries_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."query_runs"
    ADD CONSTRAINT "query_runs_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."user_config_overrides"
    ADD CONSTRAINT "user_config_overrides_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."user_config_overrides"
    ADD CONSTRAINT "user_config_overrides_user_id_config_type_config_key_key" UNIQUE ("user_id", "config_type", "config_key");



ALTER TABLE ONLY "public"."user_profiles"
    ADD CONSTRAINT "user_profiles_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."wiki_generation_runs"
    ADD CONSTRAINT "wiki_generation_runs_pkey" PRIMARY KEY ("id");



CREATE INDEX "idx_checklist_analysis_runs_indexing_run_id" ON "public"."checklist_analysis_runs" USING "btree" ("indexing_run_id");



CREATE INDEX "idx_checklist_analysis_runs_status" ON "public"."checklist_analysis_runs" USING "btree" ("status");



CREATE INDEX "idx_checklist_analysis_runs_user_id" ON "public"."checklist_analysis_runs" USING "btree" ("user_id");



CREATE INDEX "idx_checklist_results_all_sources" ON "public"."checklist_results" USING "gin" ("all_sources");



CREATE INDEX "idx_checklist_results_analysis_run_id" ON "public"."checklist_results" USING "btree" ("analysis_run_id");



CREATE INDEX "idx_checklist_results_status" ON "public"."checklist_results" USING "btree" ("status");



CREATE INDEX "idx_checklist_templates_category" ON "public"."checklist_templates" USING "btree" ("category");



CREATE INDEX "idx_checklist_templates_user_id" ON "public"."checklist_templates" USING "btree" ("user_id");



CREATE INDEX "idx_document_chunks_document_id" ON "public"."document_chunks" USING "btree" ("document_id");



CREATE INDEX "idx_document_chunks_embedding" ON "public"."document_chunks" USING "ivfflat" ("embedding" "public"."vector_cosine_ops") WITH ("lists"='100');



CREATE INDEX "idx_document_chunks_metadata_gin" ON "public"."document_chunks" USING "gin" ("metadata");



CREATE INDEX "idx_document_chunks_page_number" ON "public"."document_chunks" USING "btree" ("page_number");



CREATE INDEX "idx_documents_created_at" ON "public"."documents" USING "btree" ("created_at");



CREATE INDEX "idx_documents_status" ON "public"."documents" USING "btree" ("status");



CREATE INDEX "idx_documents_user_id" ON "public"."documents" USING "btree" ("user_id");



CREATE INDEX "idx_indexing_run_documents_document_id" ON "public"."indexing_run_documents" USING "btree" ("document_id");



CREATE INDEX "idx_indexing_run_documents_indexing_run_id" ON "public"."indexing_run_documents" USING "btree" ("indexing_run_id");



CREATE INDEX "idx_indexing_runs_access_level" ON "public"."indexing_runs" USING "btree" ("access_level");



CREATE INDEX "idx_indexing_runs_email" ON "public"."indexing_runs" USING "btree" ("email") WHERE ("email" IS NOT NULL);



CREATE INDEX "idx_indexing_runs_pipeline_config" ON "public"."indexing_runs" USING "gin" ("pipeline_config");



CREATE INDEX "idx_indexing_runs_project_id" ON "public"."indexing_runs" USING "btree" ("project_id");



CREATE INDEX "idx_indexing_runs_started_at" ON "public"."indexing_runs" USING "btree" ("started_at");



CREATE INDEX "idx_indexing_runs_status" ON "public"."indexing_runs" USING "btree" ("status");



CREATE INDEX "idx_indexing_runs_upload_type" ON "public"."indexing_runs" USING "btree" ("upload_type");



CREATE INDEX "idx_indexing_runs_upload_type_access_level" ON "public"."indexing_runs" USING "btree" ("upload_type", "access_level") WHERE (("upload_type" = 'email'::"text") AND (("access_level")::"text" = 'public'::"text"));



CREATE INDEX "idx_indexing_runs_user_access" ON "public"."indexing_runs" USING "btree" ("user_id", "access_level");



CREATE INDEX "idx_pipeline_runs_document_id" ON "public"."pipeline_runs" USING "btree" ("document_id");



CREATE INDEX "idx_pipeline_runs_status" ON "public"."pipeline_runs" USING "btree" ("status");



CREATE INDEX "idx_project_wikis_access_level" ON "public"."project_wikis" USING "btree" ("access_level");



CREATE INDEX "idx_project_wikis_created_at" ON "public"."project_wikis" USING "btree" ("created_at" DESC);



CREATE INDEX "idx_project_wikis_project_id" ON "public"."project_wikis" USING "btree" ("project_id");



CREATE INDEX "idx_project_wikis_public_completed" ON "public"."project_wikis" USING "btree" ("access_level", "upload_type", "wiki_status", "created_at" DESC) WHERE (("access_level" = 'public'::"text") AND ("upload_type" = 'email'::"text") AND ("wiki_status" = 'completed'::"text"));



CREATE INDEX "idx_project_wikis_upload_type" ON "public"."project_wikis" USING "btree" ("upload_type");



CREATE INDEX "idx_project_wikis_user_id" ON "public"."project_wikis" USING "btree" ("user_id");



CREATE INDEX "idx_project_wikis_wiki_status" ON "public"."project_wikis" USING "btree" ("wiki_status");



CREATE INDEX "idx_projects_access_level" ON "public"."projects" USING "btree" ("access_level");



CREATE INDEX "idx_projects_created_at" ON "public"."projects" USING "btree" ("created_at");



CREATE INDEX "idx_projects_deleted_at" ON "public"."projects" USING "btree" ("deleted_at") WHERE ("deleted_at" IS NULL);



CREATE INDEX "idx_projects_user_id" ON "public"."projects" USING "btree" ("user_id");



CREATE INDEX "idx_queries_created_at" ON "public"."queries" USING "btree" ("created_at");



CREATE INDEX "idx_queries_user_id" ON "public"."queries" USING "btree" ("user_id");



CREATE INDEX "idx_query_runs_access_level" ON "public"."query_runs" USING "btree" ("access_level");



CREATE INDEX "idx_query_runs_created_at" ON "public"."query_runs" USING "btree" ("created_at" DESC);



CREATE INDEX "idx_query_runs_indexing_run_id" ON "public"."query_runs" USING "btree" ("indexing_run_id");



CREATE INDEX "idx_query_runs_pipeline_config" ON "public"."query_runs" USING "gin" ("pipeline_config");



CREATE INDEX "idx_query_runs_response_time" ON "public"."query_runs" USING "btree" ("response_time_ms");



CREATE INDEX "idx_query_runs_user_access" ON "public"."query_runs" USING "btree" ("user_id", "access_level");



CREATE INDEX "idx_query_runs_user_id" ON "public"."query_runs" USING "btree" ("user_id");



CREATE INDEX "idx_user_config_overrides_config_type" ON "public"."user_config_overrides" USING "btree" ("config_type");



CREATE INDEX "idx_user_config_overrides_user_id" ON "public"."user_config_overrides" USING "btree" ("user_id");



CREATE INDEX "idx_wiki_generation_runs_access_level" ON "public"."wiki_generation_runs" USING "btree" ("access_level");



CREATE INDEX "idx_wiki_generation_runs_indexing_run_id" ON "public"."wiki_generation_runs" USING "btree" ("indexing_run_id");



CREATE INDEX "idx_wiki_generation_runs_project_id" ON "public"."wiki_generation_runs" USING "btree" ("project_id");



CREATE INDEX "idx_wiki_generation_runs_started_at" ON "public"."wiki_generation_runs" USING "btree" ("started_at");



CREATE INDEX "idx_wiki_generation_runs_status" ON "public"."wiki_generation_runs" USING "btree" ("status");



CREATE INDEX "idx_wiki_generation_runs_upload_id" ON "public"."wiki_generation_runs" USING "btree" ("upload_id");



CREATE INDEX "idx_wiki_generation_runs_upload_type" ON "public"."wiki_generation_runs" USING "btree" ("upload_type");



CREATE INDEX "idx_wiki_generation_runs_user_access" ON "public"."wiki_generation_runs" USING "btree" ("user_id", "access_level");



CREATE INDEX "idx_wiki_generation_runs_user_id" ON "public"."wiki_generation_runs" USING "btree" ("user_id");



CREATE OR REPLACE TRIGGER "sync_project_wikis_trigger" AFTER INSERT OR UPDATE ON "public"."wiki_generation_runs" FOR EACH ROW EXECUTE FUNCTION "public"."sync_project_wikis"();



CREATE OR REPLACE TRIGGER "trg_project_wikis_updated_at" BEFORE UPDATE ON "public"."project_wikis" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at"();



CREATE OR REPLACE TRIGGER "trg_projects_updated_at" BEFORE UPDATE ON "public"."projects" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at"();



CREATE OR REPLACE TRIGGER "update_documents_updated_at" BEFORE UPDATE ON "public"."documents" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "update_indexing_runs_updated_at" BEFORE UPDATE ON "public"."indexing_runs" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "update_projects_updated_at" BEFORE UPDATE ON "public"."projects" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "update_query_runs_updated_at" BEFORE UPDATE ON "public"."query_runs" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "update_user_config_overrides_updated_at" BEFORE UPDATE ON "public"."user_config_overrides" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "update_user_profiles_updated_at" BEFORE UPDATE ON "public"."user_profiles" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "update_wiki_generation_runs_updated_at" BEFORE UPDATE ON "public"."wiki_generation_runs" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



ALTER TABLE ONLY "public"."checklist_analysis_runs"
    ADD CONSTRAINT "checklist_analysis_runs_indexing_run_id_fkey" FOREIGN KEY ("indexing_run_id") REFERENCES "public"."indexing_runs"("id");



ALTER TABLE ONLY "public"."checklist_analysis_runs"
    ADD CONSTRAINT "checklist_analysis_runs_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id");



ALTER TABLE ONLY "public"."checklist_results"
    ADD CONSTRAINT "checklist_results_analysis_run_id_fkey" FOREIGN KEY ("analysis_run_id") REFERENCES "public"."checklist_analysis_runs"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."checklist_results"
    ADD CONSTRAINT "checklist_results_source_chunk_id_fkey" FOREIGN KEY ("source_chunk_id") REFERENCES "public"."document_chunks"("id");



ALTER TABLE ONLY "public"."checklist_templates"
    ADD CONSTRAINT "checklist_templates_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id");



ALTER TABLE ONLY "public"."document_chunks"
    ADD CONSTRAINT "document_chunks_document_id_fkey" FOREIGN KEY ("document_id") REFERENCES "public"."documents"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."documents"
    ADD CONSTRAINT "documents_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."indexing_run_documents"
    ADD CONSTRAINT "indexing_run_documents_document_id_fkey" FOREIGN KEY ("document_id") REFERENCES "public"."documents"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."indexing_run_documents"
    ADD CONSTRAINT "indexing_run_documents_indexing_run_id_fkey" FOREIGN KEY ("indexing_run_id") REFERENCES "public"."indexing_runs"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."indexing_runs"
    ADD CONSTRAINT "indexing_runs_project_id_fkey" FOREIGN KEY ("project_id") REFERENCES "public"."projects"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."indexing_runs"
    ADD CONSTRAINT "indexing_runs_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."pipeline_runs"
    ADD CONSTRAINT "pipeline_runs_document_id_fkey" FOREIGN KEY ("document_id") REFERENCES "public"."documents"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."project_wikis"
    ADD CONSTRAINT "project_wikis_indexing_run_id_fkey" FOREIGN KEY ("indexing_run_id") REFERENCES "public"."indexing_runs"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."project_wikis"
    ADD CONSTRAINT "project_wikis_project_id_fkey" FOREIGN KEY ("project_id") REFERENCES "public"."projects"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."project_wikis"
    ADD CONSTRAINT "project_wikis_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."project_wikis"
    ADD CONSTRAINT "project_wikis_wiki_run_id_fkey" FOREIGN KEY ("wiki_run_id") REFERENCES "public"."wiki_generation_runs"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."projects"
    ADD CONSTRAINT "projects_deleted_by_fkey" FOREIGN KEY ("deleted_by") REFERENCES "auth"."users"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."projects"
    ADD CONSTRAINT "projects_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."queries"
    ADD CONSTRAINT "queries_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."query_runs"
    ADD CONSTRAINT "query_runs_indexing_run_id_fkey" FOREIGN KEY ("indexing_run_id") REFERENCES "public"."indexing_runs"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."user_config_overrides"
    ADD CONSTRAINT "user_config_overrides_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."user_profiles"
    ADD CONSTRAINT "user_profiles_id_fkey" FOREIGN KEY ("id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."wiki_generation_runs"
    ADD CONSTRAINT "wiki_generation_runs_indexing_run_id_fkey" FOREIGN KEY ("indexing_run_id") REFERENCES "public"."indexing_runs"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."wiki_generation_runs"
    ADD CONSTRAINT "wiki_generation_runs_project_id_fkey" FOREIGN KEY ("project_id") REFERENCES "public"."projects"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."wiki_generation_runs"
    ADD CONSTRAINT "wiki_generation_runs_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



CREATE POLICY "Public can access public indexing runs" ON "public"."indexing_runs" FOR SELECT USING ((("access_level")::"text" = 'public'::"text"));



CREATE POLICY "System can access all document chunks" ON "public"."document_chunks" USING (("auth"."role"() = 'service_role'::"text"));



CREATE POLICY "System can access all documents" ON "public"."documents" USING (("auth"."role"() = 'service_role'::"text"));



CREATE POLICY "System can access all indexing run documents" ON "public"."indexing_run_documents" USING (("auth"."role"() = 'service_role'::"text"));



CREATE POLICY "System can access all indexing runs" ON "public"."indexing_runs" USING (("auth"."role"() = 'service_role'::"text"));



CREATE POLICY "System can access all projects" ON "public"."projects" USING (("auth"."role"() = 'service_role'::"text"));



CREATE POLICY "System can access all query runs" ON "public"."query_runs" USING (("auth"."role"() = 'service_role'::"text"));



CREATE POLICY "System can access all user config overrides" ON "public"."user_config_overrides" USING (("auth"."role"() = 'service_role'::"text"));



CREATE POLICY "System can access all user profiles" ON "public"."user_profiles" USING (("auth"."role"() = 'service_role'::"text"));



CREATE POLICY "Users can access chunks for their documents" ON "public"."document_chunks" USING ((EXISTS ( SELECT 1
   FROM "public"."documents" "d"
  WHERE (("d"."id" = "document_chunks"."document_id") AND ("d"."user_id" = "auth"."uid"())))));



CREATE POLICY "Users can access indexing run documents for their documents" ON "public"."indexing_run_documents" USING ((EXISTS ( SELECT 1
   FROM "public"."documents" "d"
  WHERE (("d"."id" = "indexing_run_documents"."document_id") AND ("d"."user_id" = "auth"."uid"())))));



CREATE POLICY "Users can access indexing runs for their documents" ON "public"."indexing_runs" USING ((EXISTS ( SELECT 1
   FROM ("public"."indexing_run_documents" "ird"
     JOIN "public"."documents" "d" ON (("ird"."document_id" = "d"."id")))
  WHERE (("ird"."indexing_run_id" = "indexing_runs"."id") AND ("d"."user_id" = "auth"."uid"())))));



CREATE POLICY "Users can access results for accessible analysis runs" ON "public"."checklist_results" USING ((EXISTS ( SELECT 1
   FROM "public"."checklist_analysis_runs"
  WHERE (("checklist_analysis_runs"."id" = "checklist_results"."analysis_run_id") AND
        CASE
            WHEN ("checklist_analysis_runs"."access_level" = 'public'::"public"."access_level") THEN true
            WHEN (("checklist_analysis_runs"."access_level" = 'auth'::"public"."access_level") AND ("auth"."uid"() IS NOT NULL)) THEN true
            WHEN (("checklist_analysis_runs"."access_level" = 'private'::"public"."access_level") AND ("checklist_analysis_runs"."user_id" = "auth"."uid"())) THEN true
            ELSE false
        END))));



CREATE POLICY "Users can access their own analysis runs" ON "public"."checklist_analysis_runs" USING (
CASE
    WHEN ("access_level" = 'public'::"public"."access_level") THEN true
    WHEN (("access_level" = 'auth'::"public"."access_level") AND ("auth"."uid"() IS NOT NULL)) THEN true
    WHEN (("access_level" = 'private'::"public"."access_level") AND ("user_id" = "auth"."uid"())) THEN true
    ELSE false
END);



CREATE POLICY "Users can access their own config overrides" ON "public"."user_config_overrides" USING (("user_id" = "auth"."uid"()));



CREATE POLICY "Users can access their own documents" ON "public"."documents" USING (("user_id" = "auth"."uid"()));



CREATE POLICY "Users can access their own profile" ON "public"."user_profiles" USING (("id" = "auth"."uid"()));



CREATE POLICY "Users can access their own projects" ON "public"."projects" USING (("user_id" = "auth"."uid"()));



CREATE POLICY "Users can access their own query runs" ON "public"."query_runs" USING ((("user_id")::"uuid" = "auth"."uid"()));



CREATE POLICY "Users can access their own templates or public templates" ON "public"."checklist_templates" USING (
CASE
    WHEN ("is_public" = true) THEN true
    WHEN ("user_id" = "auth"."uid"()) THEN true
    ELSE false
END);



CREATE POLICY "Users can delete their own documents" ON "public"."documents" FOR DELETE USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can delete their own wiki generation runs" ON "public"."wiki_generation_runs" FOR DELETE USING (((("upload_type" = 'user_project'::"text") AND ("user_id" = "auth"."uid"())) OR (("upload_type" = 'email'::"text") AND ("upload_id" IS NOT NULL))));



CREATE POLICY "Users can insert chunks for their documents" ON "public"."document_chunks" FOR INSERT WITH CHECK ((EXISTS ( SELECT 1
   FROM "public"."documents"
  WHERE (("documents"."id" = "document_chunks"."document_id") AND ("documents"."user_id" = "auth"."uid"())))));



CREATE POLICY "Users can insert pipeline runs for their documents" ON "public"."pipeline_runs" FOR INSERT WITH CHECK ((EXISTS ( SELECT 1
   FROM "public"."documents"
  WHERE (("documents"."id" = "pipeline_runs"."document_id") AND ("documents"."user_id" = "auth"."uid"())))));



CREATE POLICY "Users can insert their own documents" ON "public"."documents" FOR INSERT WITH CHECK (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can insert their own queries" ON "public"."queries" FOR INSERT WITH CHECK (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can insert their own wiki generation runs" ON "public"."wiki_generation_runs" FOR INSERT WITH CHECK (((("upload_type" = 'user_project'::"text") AND ("user_id" = "auth"."uid"())) OR (("upload_type" = 'email'::"text") AND ("upload_id" IS NOT NULL))));



CREATE POLICY "Users can update their own documents" ON "public"."documents" FOR UPDATE USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can update their own profile" ON "public"."user_profiles" FOR UPDATE USING (("auth"."uid"() = "id"));



CREATE POLICY "Users can update their own wiki generation runs" ON "public"."wiki_generation_runs" FOR UPDATE USING (((("upload_type" = 'user_project'::"text") AND ("user_id" = "auth"."uid"())) OR (("upload_type" = 'email'::"text") AND ("upload_id" IS NOT NULL))));



CREATE POLICY "Users can view chunks from their documents" ON "public"."document_chunks" FOR SELECT USING ((EXISTS ( SELECT 1
   FROM "public"."documents"
  WHERE (("documents"."id" = "document_chunks"."document_id") AND ("documents"."user_id" = "auth"."uid"())))));



CREATE POLICY "Users can view own non-deleted projects" ON "public"."projects" FOR SELECT USING ((("auth"."uid"() = "user_id") AND ("deleted_at" IS NULL)));



CREATE POLICY "Users can view their own documents" ON "public"."documents" FOR SELECT USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can view their own pipeline runs" ON "public"."pipeline_runs" FOR SELECT USING ((EXISTS ( SELECT 1
   FROM "public"."documents"
  WHERE (("documents"."id" = "pipeline_runs"."document_id") AND ("documents"."user_id" = "auth"."uid"())))));



CREATE POLICY "Users can view their own profile" ON "public"."user_profiles" FOR SELECT USING (("auth"."uid"() = "id"));



CREATE POLICY "Users can view their own queries" ON "public"."queries" FOR SELECT USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can view their own wiki generation runs" ON "public"."wiki_generation_runs" FOR SELECT USING (((("upload_type" = 'user_project'::"text") AND ("user_id" = "auth"."uid"())) OR (("upload_type" = 'email'::"text") AND ("upload_id" IS NOT NULL))));



ALTER TABLE "public"."checklist_analysis_runs" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."checklist_results" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."checklist_templates" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "doc_modify_owner_policy" ON "public"."documents" USING ((("user_id" IS NOT NULL) AND (("user_id")::"text" = COALESCE((("current_setting"('request.jwt.claims'::"text", true))::"jsonb" ->> 'sub'::"text"), ''::"text")))) WITH CHECK ((("user_id" IS NOT NULL) AND (("user_id")::"text" = COALESCE((("current_setting"('request.jwt.claims'::"text", true))::"jsonb" ->> 'sub'::"text"), ''::"text"))));



ALTER TABLE "public"."document_chunks" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."documents" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "idx_modify_owner_policy" ON "public"."indexing_runs" USING ((("user_id" IS NOT NULL) AND (("user_id")::"text" = COALESCE((("current_setting"('request.jwt.claims'::"text", true))::"jsonb" ->> 'sub'::"text"), ''::"text")))) WITH CHECK (true);



CREATE POLICY "idx_select_policy" ON "public"."indexing_runs" FOR SELECT USING ((((("access_level")::"text" = 'public'::"text") AND ("upload_type" = 'email'::"text")) OR ((("access_level")::"text" = 'auth'::"text") AND (("current_setting"('request.jwt.claims'::"text", true))::"jsonb" ? 'sub'::"text")) OR (("user_id" IS NOT NULL) AND (("user_id")::"text" = COALESCE((("current_setting"('request.jwt.claims'::"text", true))::"jsonb" ->> 'sub'::"text"), ''::"text"))) OR (("project_id" IS NOT NULL) AND (EXISTS ( SELECT 1
   FROM "public"."projects" "p"
  WHERE (("p"."id" = "indexing_runs"."project_id") AND (("p"."user_id")::"text" = COALESCE((("current_setting"('request.jwt.claims'::"text", true))::"jsonb" ->> 'sub'::"text"), ''::"text"))))))));



ALTER TABLE "public"."indexing_run_documents" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."indexing_runs" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."pipeline_runs" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."project_wikis" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "project_wikis_delete_system" ON "public"."project_wikis" FOR DELETE USING (("auth"."role"() = 'service_role'::"text"));



CREATE POLICY "project_wikis_insert_system" ON "public"."project_wikis" FOR INSERT WITH CHECK (("auth"."role"() = 'service_role'::"text"));



CREATE POLICY "project_wikis_select_public" ON "public"."project_wikis" FOR SELECT USING (((("access_level" = 'public'::"text") AND ("upload_type" = 'email'::"text")) OR (("user_id")::"text" = COALESCE((("current_setting"('request.jwt.claims'::"text", true))::"jsonb" ->> 'sub'::"text"), ''::"text"))));



CREATE POLICY "project_wikis_update_system" ON "public"."project_wikis" FOR UPDATE USING (("auth"."role"() = 'service_role'::"text"));



ALTER TABLE "public"."projects" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "projects_delete_owner" ON "public"."projects" FOR DELETE USING ((("user_id")::"text" = COALESCE((("current_setting"('request.jwt.claims'::"text", true))::"jsonb" ->> 'sub'::"text"), ''::"text")));



CREATE POLICY "projects_insert_self" ON "public"."projects" FOR INSERT WITH CHECK ((("user_id")::"text" = COALESCE((("current_setting"('request.jwt.claims'::"text", true))::"jsonb" ->> 'sub'::"text"), ''::"text")));



CREATE POLICY "projects_select_owner" ON "public"."projects" FOR SELECT USING ((("user_id")::"text" = COALESCE((("current_setting"('request.jwt.claims'::"text", true))::"jsonb" ->> 'sub'::"text"), ''::"text")));



CREATE POLICY "projects_update_owner" ON "public"."projects" FOR UPDATE USING ((("user_id")::"text" = COALESCE((("current_setting"('request.jwt.claims'::"text", true))::"jsonb" ->> 'sub'::"text"), ''::"text"))) WITH CHECK ((("user_id")::"text" = COALESCE((("current_setting"('request.jwt.claims'::"text", true))::"jsonb" ->> 'sub'::"text"), ''::"text")));



ALTER TABLE "public"."queries" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "query_modify_owner_policy" ON "public"."query_runs" USING ((("user_id" IS NOT NULL) AND ("user_id" = COALESCE((("current_setting"('request.jwt.claims'::"text", true))::"jsonb" ->> 'sub'::"text"), ''::"text")))) WITH CHECK (true);



ALTER TABLE "public"."query_runs" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "query_select_policy" ON "public"."query_runs" FOR SELECT USING (((("access_level")::"text" = 'public'::"text") OR ((("access_level")::"text" = 'auth'::"text") AND (("current_setting"('request.jwt.claims'::"text", true))::"jsonb" ? 'sub'::"text")) OR (("user_id" IS NOT NULL) AND ("user_id" = COALESCE((("current_setting"('request.jwt.claims'::"text", true))::"jsonb" ->> 'sub'::"text"), ''::"text")))));



ALTER TABLE "public"."user_config_overrides" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."user_profiles" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."wiki_generation_runs" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "wiki_modify_owner_policy" ON "public"."wiki_generation_runs" USING ((("user_id" IS NOT NULL) AND (("user_id")::"text" = COALESCE((("current_setting"('request.jwt.claims'::"text", true))::"jsonb" ->> 'sub'::"text"), ''::"text")))) WITH CHECK (true);



CREATE POLICY "wiki_select_policy" ON "public"."wiki_generation_runs" FOR SELECT USING (((("access_level")::"text" = 'public'::"text") OR ((("access_level")::"text" = 'auth'::"text") AND (("current_setting"('request.jwt.claims'::"text", true))::"jsonb" ? 'sub'::"text")) OR (("user_id" IS NOT NULL) AND (("user_id")::"text" = COALESCE((("current_setting"('request.jwt.claims'::"text", true))::"jsonb" ->> 'sub'::"text"), ''::"text"))) OR (("project_id" IS NOT NULL) AND (EXISTS ( SELECT 1
   FROM "public"."projects" "p"
  WHERE (("p"."id" = "wiki_generation_runs"."project_id") AND (("p"."user_id")::"text" = COALESCE((("current_setting"('request.jwt.claims'::"text", true))::"jsonb" ->> 'sub'::"text"), ''::"text"))))))));





ALTER PUBLICATION "supabase_realtime" OWNER TO "postgres";





GRANT USAGE ON SCHEMA "public" TO "postgres";
GRANT USAGE ON SCHEMA "public" TO "anon";
GRANT USAGE ON SCHEMA "public" TO "authenticated";
GRANT USAGE ON SCHEMA "public" TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_in"("cstring", "oid", integer) TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_in"("cstring", "oid", integer) TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_in"("cstring", "oid", integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_in"("cstring", "oid", integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_out"("public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_out"("public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_out"("public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_out"("public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_recv"("internal", "oid", integer) TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_recv"("internal", "oid", integer) TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_recv"("internal", "oid", integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_recv"("internal", "oid", integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_send"("public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_send"("public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_send"("public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_send"("public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_typmod_in"("cstring"[]) TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_typmod_in"("cstring"[]) TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_typmod_in"("cstring"[]) TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_typmod_in"("cstring"[]) TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_in"("cstring", "oid", integer) TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_in"("cstring", "oid", integer) TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_in"("cstring", "oid", integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_in"("cstring", "oid", integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_out"("public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_out"("public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_out"("public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_out"("public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_recv"("internal", "oid", integer) TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_recv"("internal", "oid", integer) TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_recv"("internal", "oid", integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_recv"("internal", "oid", integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_send"("public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_send"("public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_send"("public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_send"("public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_typmod_in"("cstring"[]) TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_typmod_in"("cstring"[]) TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_typmod_in"("cstring"[]) TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_typmod_in"("cstring"[]) TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_in"("cstring", "oid", integer) TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_in"("cstring", "oid", integer) TO "anon";
GRANT ALL ON FUNCTION "public"."vector_in"("cstring", "oid", integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_in"("cstring", "oid", integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_out"("public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_out"("public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_out"("public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_out"("public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_recv"("internal", "oid", integer) TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_recv"("internal", "oid", integer) TO "anon";
GRANT ALL ON FUNCTION "public"."vector_recv"("internal", "oid", integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_recv"("internal", "oid", integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_send"("public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_send"("public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_send"("public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_send"("public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_typmod_in"("cstring"[]) TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_typmod_in"("cstring"[]) TO "anon";
GRANT ALL ON FUNCTION "public"."vector_typmod_in"("cstring"[]) TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_typmod_in"("cstring"[]) TO "service_role";



GRANT ALL ON FUNCTION "public"."array_to_halfvec"(real[], integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."array_to_halfvec"(real[], integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."array_to_halfvec"(real[], integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."array_to_halfvec"(real[], integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(real[], integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(real[], integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(real[], integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(real[], integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."array_to_vector"(real[], integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."array_to_vector"(real[], integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."array_to_vector"(real[], integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."array_to_vector"(real[], integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."array_to_halfvec"(double precision[], integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."array_to_halfvec"(double precision[], integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."array_to_halfvec"(double precision[], integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."array_to_halfvec"(double precision[], integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(double precision[], integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(double precision[], integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(double precision[], integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(double precision[], integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."array_to_vector"(double precision[], integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."array_to_vector"(double precision[], integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."array_to_vector"(double precision[], integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."array_to_vector"(double precision[], integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."array_to_halfvec"(integer[], integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."array_to_halfvec"(integer[], integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."array_to_halfvec"(integer[], integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."array_to_halfvec"(integer[], integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(integer[], integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(integer[], integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(integer[], integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(integer[], integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."array_to_vector"(integer[], integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."array_to_vector"(integer[], integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."array_to_vector"(integer[], integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."array_to_vector"(integer[], integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."array_to_halfvec"(numeric[], integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."array_to_halfvec"(numeric[], integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."array_to_halfvec"(numeric[], integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."array_to_halfvec"(numeric[], integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(numeric[], integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(numeric[], integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(numeric[], integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(numeric[], integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."array_to_vector"(numeric[], integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."array_to_vector"(numeric[], integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."array_to_vector"(numeric[], integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."array_to_vector"(numeric[], integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_to_float4"("public"."halfvec", integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_to_float4"("public"."halfvec", integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_to_float4"("public"."halfvec", integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_to_float4"("public"."halfvec", integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec"("public"."halfvec", integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec"("public"."halfvec", integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec"("public"."halfvec", integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec"("public"."halfvec", integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_to_sparsevec"("public"."halfvec", integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_to_sparsevec"("public"."halfvec", integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_to_sparsevec"("public"."halfvec", integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_to_sparsevec"("public"."halfvec", integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_to_vector"("public"."halfvec", integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_to_vector"("public"."halfvec", integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_to_vector"("public"."halfvec", integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_to_vector"("public"."halfvec", integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_to_halfvec"("public"."sparsevec", integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_to_halfvec"("public"."sparsevec", integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_to_halfvec"("public"."sparsevec", integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_to_halfvec"("public"."sparsevec", integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec"("public"."sparsevec", integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec"("public"."sparsevec", integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec"("public"."sparsevec", integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec"("public"."sparsevec", integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_to_vector"("public"."sparsevec", integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_to_vector"("public"."sparsevec", integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_to_vector"("public"."sparsevec", integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_to_vector"("public"."sparsevec", integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_to_float4"("public"."vector", integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_to_float4"("public"."vector", integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."vector_to_float4"("public"."vector", integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_to_float4"("public"."vector", integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_to_halfvec"("public"."vector", integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_to_halfvec"("public"."vector", integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."vector_to_halfvec"("public"."vector", integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_to_halfvec"("public"."vector", integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_to_sparsevec"("public"."vector", integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_to_sparsevec"("public"."vector", integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."vector_to_sparsevec"("public"."vector", integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_to_sparsevec"("public"."vector", integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."vector"("public"."vector", integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."vector"("public"."vector", integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."vector"("public"."vector", integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector"("public"."vector", integer, boolean) TO "service_role";































































































































































GRANT ALL ON FUNCTION "public"."binary_quantize"("public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."binary_quantize"("public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."binary_quantize"("public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."binary_quantize"("public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."binary_quantize"("public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."binary_quantize"("public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."binary_quantize"("public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."binary_quantize"("public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."cleanup_expired_email_uploads"() TO "anon";
GRANT ALL ON FUNCTION "public"."cleanup_expired_email_uploads"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."cleanup_expired_email_uploads"() TO "service_role";



GRANT ALL ON FUNCTION "public"."cosine_distance"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."cosine_distance"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."cosine_distance"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."cosine_distance"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."cosine_distance"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."cosine_distance"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."cosine_distance"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."cosine_distance"("public"."sparsevec", "public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."cosine_distance"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."cosine_distance"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."cosine_distance"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."cosine_distance"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."delete_email_upload_folders_production"() TO "anon";
GRANT ALL ON FUNCTION "public"."delete_email_upload_folders_production"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."delete_email_upload_folders_production"() TO "service_role";



GRANT ALL ON FUNCTION "public"."delete_folders_production"() TO "anon";
GRANT ALL ON FUNCTION "public"."delete_folders_production"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."delete_folders_production"() TO "service_role";



GRANT ALL ON FUNCTION "public"."delete_folders_test"() TO "anon";
GRANT ALL ON FUNCTION "public"."delete_folders_test"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."delete_folders_test"() TO "service_role";



GRANT ALL ON FUNCTION "public"."delete_users_folders_production"() TO "anon";
GRANT ALL ON FUNCTION "public"."delete_users_folders_production"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."delete_users_folders_production"() TO "service_role";



GRANT ALL ON FUNCTION "public"."empty_database_except_users_improved"() TO "anon";
GRANT ALL ON FUNCTION "public"."empty_database_except_users_improved"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."empty_database_except_users_improved"() TO "service_role";



GRANT ALL ON FUNCTION "public"."extract_indexing_run_id_from_user_path"("file_path" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."extract_indexing_run_id_from_user_path"("file_path" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."extract_indexing_run_id_from_user_path"("file_path" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."get_all_auth_users"() TO "anon";
GRANT ALL ON FUNCTION "public"."get_all_auth_users"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_all_auth_users"() TO "service_role";



GRANT ALL ON FUNCTION "public"."get_auth_user_by_email"("user_email" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."get_auth_user_by_email"("user_email" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_auth_user_by_email"("user_email" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."get_recent_query_performance"("hours_back" integer) TO "anon";
GRANT ALL ON FUNCTION "public"."get_recent_query_performance"("hours_back" integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_recent_query_performance"("hours_back" integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."get_storage_path_for_document"("doc_upload_type" "text", "doc_upload_id" "text", "doc_user_id" "uuid", "doc_project_id" "uuid", "doc_index_run_id" "uuid", "doc_id" "uuid", "file_type" "text", "filename" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."get_storage_path_for_document"("doc_upload_type" "text", "doc_upload_id" "text", "doc_user_id" "uuid", "doc_project_id" "uuid", "doc_index_run_id" "uuid", "doc_id" "uuid", "file_type" "text", "filename" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_storage_path_for_document"("doc_upload_type" "text", "doc_upload_id" "text", "doc_user_id" "uuid", "doc_project_id" "uuid", "doc_index_run_id" "uuid", "doc_id" "uuid", "file_type" "text", "filename" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."get_storage_usage_stats"("user_uuid" "uuid") TO "anon";
GRANT ALL ON FUNCTION "public"."get_storage_usage_stats"("user_uuid" "uuid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_storage_usage_stats"("user_uuid" "uuid") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_accum"(double precision[], "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_accum"(double precision[], "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_accum"(double precision[], "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_accum"(double precision[], "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_add"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_add"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_add"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_add"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_avg"(double precision[]) TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_avg"(double precision[]) TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_avg"(double precision[]) TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_avg"(double precision[]) TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_cmp"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_cmp"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_cmp"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_cmp"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_combine"(double precision[], double precision[]) TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_combine"(double precision[], double precision[]) TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_combine"(double precision[], double precision[]) TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_combine"(double precision[], double precision[]) TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_concat"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_concat"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_concat"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_concat"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_eq"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_eq"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_eq"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_eq"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_ge"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_ge"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_ge"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_ge"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_gt"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_gt"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_gt"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_gt"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_l2_squared_distance"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_l2_squared_distance"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_l2_squared_distance"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_l2_squared_distance"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_le"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_le"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_le"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_le"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_lt"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_lt"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_lt"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_lt"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_mul"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_mul"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_mul"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_mul"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_ne"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_ne"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_ne"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_ne"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_negative_inner_product"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_negative_inner_product"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_negative_inner_product"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_negative_inner_product"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_spherical_distance"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_spherical_distance"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_spherical_distance"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_spherical_distance"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_sub"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_sub"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_sub"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_sub"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."hamming_distance"(bit, bit) TO "postgres";
GRANT ALL ON FUNCTION "public"."hamming_distance"(bit, bit) TO "anon";
GRANT ALL ON FUNCTION "public"."hamming_distance"(bit, bit) TO "authenticated";
GRANT ALL ON FUNCTION "public"."hamming_distance"(bit, bit) TO "service_role";



GRANT ALL ON FUNCTION "public"."hnsw_bit_support"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."hnsw_bit_support"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."hnsw_bit_support"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."hnsw_bit_support"("internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."hnsw_halfvec_support"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."hnsw_halfvec_support"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."hnsw_halfvec_support"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."hnsw_halfvec_support"("internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."hnsw_sparsevec_support"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."hnsw_sparsevec_support"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."hnsw_sparsevec_support"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."hnsw_sparsevec_support"("internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."hnswhandler"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."hnswhandler"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."hnswhandler"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."hnswhandler"("internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."inner_product"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."inner_product"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."inner_product"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."inner_product"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."inner_product"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."inner_product"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."inner_product"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."inner_product"("public"."sparsevec", "public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."inner_product"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."inner_product"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."inner_product"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."inner_product"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."ivfflat_bit_support"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."ivfflat_bit_support"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."ivfflat_bit_support"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."ivfflat_bit_support"("internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."ivfflat_halfvec_support"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."ivfflat_halfvec_support"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."ivfflat_halfvec_support"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."ivfflat_halfvec_support"("internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."ivfflathandler"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."ivfflathandler"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."ivfflathandler"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."ivfflathandler"("internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."jaccard_distance"(bit, bit) TO "postgres";
GRANT ALL ON FUNCTION "public"."jaccard_distance"(bit, bit) TO "anon";
GRANT ALL ON FUNCTION "public"."jaccard_distance"(bit, bit) TO "authenticated";
GRANT ALL ON FUNCTION "public"."jaccard_distance"(bit, bit) TO "service_role";



GRANT ALL ON FUNCTION "public"."l1_distance"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."l1_distance"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."l1_distance"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."l1_distance"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."l1_distance"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."l1_distance"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."l1_distance"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."l1_distance"("public"."sparsevec", "public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."l1_distance"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."l1_distance"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."l1_distance"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."l1_distance"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."l2_distance"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."l2_distance"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."l2_distance"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."l2_distance"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."l2_distance"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."l2_distance"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."l2_distance"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."l2_distance"("public"."sparsevec", "public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."l2_distance"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."l2_distance"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."l2_distance"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."l2_distance"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."l2_norm"("public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."l2_norm"("public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."l2_norm"("public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."l2_norm"("public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."l2_norm"("public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."l2_norm"("public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."l2_norm"("public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."l2_norm"("public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."l2_normalize"("public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."l2_normalize"("public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."l2_normalize"("public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."l2_normalize"("public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."l2_normalize"("public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."l2_normalize"("public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."l2_normalize"("public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."l2_normalize"("public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."l2_normalize"("public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."l2_normalize"("public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."l2_normalize"("public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."l2_normalize"("public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."list_deletable_email_upload_folders_production"() TO "anon";
GRANT ALL ON FUNCTION "public"."list_deletable_email_upload_folders_production"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."list_deletable_email_upload_folders_production"() TO "service_role";



GRANT ALL ON FUNCTION "public"."list_deletable_folders_production"() TO "anon";
GRANT ALL ON FUNCTION "public"."list_deletable_folders_production"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."list_deletable_folders_production"() TO "service_role";



GRANT ALL ON FUNCTION "public"."list_deletable_folders_test"() TO "anon";
GRANT ALL ON FUNCTION "public"."list_deletable_folders_test"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."list_deletable_folders_test"() TO "service_role";



GRANT ALL ON FUNCTION "public"."list_deletable_users_folders_production"() TO "anon";
GRANT ALL ON FUNCTION "public"."list_deletable_users_folders_production"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."list_deletable_users_folders_production"() TO "service_role";



GRANT ALL ON FUNCTION "public"."match_chunks"("query_embedding" "public"."vector", "match_threshold" double precision, "match_count" integer, "indexing_run_id_filter" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."match_chunks"("query_embedding" "public"."vector", "match_threshold" double precision, "match_count" integer, "indexing_run_id_filter" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."match_chunks"("query_embedding" "public"."vector", "match_threshold" double precision, "match_count" integer, "indexing_run_id_filter" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."match_chunks_with_threshold"("query_embedding" "public"."vector", "match_threshold" double precision, "match_count" integer, "indexing_run_id_filter" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."match_chunks_with_threshold"("query_embedding" "public"."vector", "match_threshold" double precision, "match_count" integer, "indexing_run_id_filter" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."match_chunks_with_threshold"("query_embedding" "public"."vector", "match_threshold" double precision, "match_count" integer, "indexing_run_id_filter" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."match_documents"("query_embedding" "public"."vector", "match_threshold" double precision, "match_count" integer, "filter_indexing_run_id" "uuid") TO "anon";
GRANT ALL ON FUNCTION "public"."match_documents"("query_embedding" "public"."vector", "match_threshold" double precision, "match_count" integer, "filter_indexing_run_id" "uuid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."match_documents"("query_embedding" "public"."vector", "match_threshold" double precision, "match_count" integer, "filter_indexing_run_id" "uuid") TO "service_role";



GRANT ALL ON FUNCTION "public"."populate_project_wikis"() TO "anon";
GRANT ALL ON FUNCTION "public"."populate_project_wikis"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."populate_project_wikis"() TO "service_role";



GRANT ALL ON FUNCTION "public"."set_updated_at"() TO "anon";
GRANT ALL ON FUNCTION "public"."set_updated_at"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."set_updated_at"() TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_cmp"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_cmp"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_cmp"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_cmp"("public"."sparsevec", "public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_eq"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_eq"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_eq"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_eq"("public"."sparsevec", "public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_ge"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_ge"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_ge"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_ge"("public"."sparsevec", "public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_gt"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_gt"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_gt"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_gt"("public"."sparsevec", "public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_l2_squared_distance"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_l2_squared_distance"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_l2_squared_distance"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_l2_squared_distance"("public"."sparsevec", "public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_le"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_le"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_le"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_le"("public"."sparsevec", "public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_lt"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_lt"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_lt"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_lt"("public"."sparsevec", "public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_ne"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_ne"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_ne"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_ne"("public"."sparsevec", "public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_negative_inner_product"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_negative_inner_product"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_negative_inner_product"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_negative_inner_product"("public"."sparsevec", "public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."subvector"("public"."halfvec", integer, integer) TO "postgres";
GRANT ALL ON FUNCTION "public"."subvector"("public"."halfvec", integer, integer) TO "anon";
GRANT ALL ON FUNCTION "public"."subvector"("public"."halfvec", integer, integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."subvector"("public"."halfvec", integer, integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."subvector"("public"."vector", integer, integer) TO "postgres";
GRANT ALL ON FUNCTION "public"."subvector"("public"."vector", integer, integer) TO "anon";
GRANT ALL ON FUNCTION "public"."subvector"("public"."vector", integer, integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."subvector"("public"."vector", integer, integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."sync_project_wikis"() TO "anon";
GRANT ALL ON FUNCTION "public"."sync_project_wikis"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."sync_project_wikis"() TO "service_role";



GRANT ALL ON FUNCTION "public"."test_migration_function"() TO "anon";
GRANT ALL ON FUNCTION "public"."test_migration_function"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."test_migration_function"() TO "service_role";



GRANT ALL ON FUNCTION "public"."update_updated_at_column"() TO "anon";
GRANT ALL ON FUNCTION "public"."update_updated_at_column"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."update_updated_at_column"() TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_accum"(double precision[], "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_accum"(double precision[], "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_accum"(double precision[], "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_accum"(double precision[], "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_add"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_add"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_add"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_add"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_avg"(double precision[]) TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_avg"(double precision[]) TO "anon";
GRANT ALL ON FUNCTION "public"."vector_avg"(double precision[]) TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_avg"(double precision[]) TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_cmp"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_cmp"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_cmp"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_cmp"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_combine"(double precision[], double precision[]) TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_combine"(double precision[], double precision[]) TO "anon";
GRANT ALL ON FUNCTION "public"."vector_combine"(double precision[], double precision[]) TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_combine"(double precision[], double precision[]) TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_concat"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_concat"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_concat"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_concat"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_dims"("public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_dims"("public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_dims"("public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_dims"("public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_dims"("public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_dims"("public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_dims"("public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_dims"("public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_eq"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_eq"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_eq"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_eq"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_ge"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_ge"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_ge"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_ge"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_gt"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_gt"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_gt"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_gt"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_l2_squared_distance"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_l2_squared_distance"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_l2_squared_distance"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_l2_squared_distance"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_le"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_le"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_le"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_le"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_lt"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_lt"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_lt"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_lt"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_mul"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_mul"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_mul"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_mul"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_ne"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_ne"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_ne"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_ne"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_negative_inner_product"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_negative_inner_product"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_negative_inner_product"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_negative_inner_product"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_norm"("public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_norm"("public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_norm"("public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_norm"("public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_spherical_distance"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_spherical_distance"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_spherical_distance"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_spherical_distance"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_sub"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_sub"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_sub"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_sub"("public"."vector", "public"."vector") TO "service_role";












GRANT ALL ON FUNCTION "public"."avg"("public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."avg"("public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."avg"("public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."avg"("public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."avg"("public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."avg"("public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."avg"("public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."avg"("public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."sum"("public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."sum"("public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."sum"("public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sum"("public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."sum"("public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."sum"("public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."sum"("public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sum"("public"."vector") TO "service_role";









GRANT ALL ON TABLE "public"."checklist_analysis_runs" TO "anon";
GRANT ALL ON TABLE "public"."checklist_analysis_runs" TO "authenticated";
GRANT ALL ON TABLE "public"."checklist_analysis_runs" TO "service_role";



GRANT ALL ON TABLE "public"."checklist_results" TO "anon";
GRANT ALL ON TABLE "public"."checklist_results" TO "authenticated";
GRANT ALL ON TABLE "public"."checklist_results" TO "service_role";



GRANT ALL ON TABLE "public"."checklist_templates" TO "anon";
GRANT ALL ON TABLE "public"."checklist_templates" TO "authenticated";
GRANT ALL ON TABLE "public"."checklist_templates" TO "service_role";



GRANT ALL ON TABLE "public"."document_chunks" TO "anon";
GRANT ALL ON TABLE "public"."document_chunks" TO "authenticated";
GRANT ALL ON TABLE "public"."document_chunks" TO "service_role";



GRANT ALL ON TABLE "public"."documents" TO "anon";
GRANT ALL ON TABLE "public"."documents" TO "authenticated";
GRANT ALL ON TABLE "public"."documents" TO "service_role";



GRANT ALL ON TABLE "public"."indexing_run_documents" TO "anon";
GRANT ALL ON TABLE "public"."indexing_run_documents" TO "authenticated";
GRANT ALL ON TABLE "public"."indexing_run_documents" TO "service_role";



GRANT ALL ON TABLE "public"."indexing_runs" TO "anon";
GRANT ALL ON TABLE "public"."indexing_runs" TO "authenticated";
GRANT ALL ON TABLE "public"."indexing_runs" TO "service_role";



GRANT ALL ON TABLE "public"."pipeline_runs" TO "anon";
GRANT ALL ON TABLE "public"."pipeline_runs" TO "authenticated";
GRANT ALL ON TABLE "public"."pipeline_runs" TO "service_role";



GRANT ALL ON TABLE "public"."project_wikis" TO "anon";
GRANT ALL ON TABLE "public"."project_wikis" TO "authenticated";
GRANT ALL ON TABLE "public"."project_wikis" TO "service_role";



GRANT ALL ON TABLE "public"."projects" TO "anon";
GRANT ALL ON TABLE "public"."projects" TO "authenticated";
GRANT ALL ON TABLE "public"."projects" TO "service_role";



GRANT ALL ON TABLE "public"."queries" TO "anon";
GRANT ALL ON TABLE "public"."queries" TO "authenticated";
GRANT ALL ON TABLE "public"."queries" TO "service_role";



GRANT ALL ON TABLE "public"."query_runs" TO "anon";
GRANT ALL ON TABLE "public"."query_runs" TO "authenticated";
GRANT ALL ON TABLE "public"."query_runs" TO "service_role";



GRANT ALL ON TABLE "public"."query_analytics" TO "anon";
GRANT ALL ON TABLE "public"."query_analytics" TO "authenticated";
GRANT ALL ON TABLE "public"."query_analytics" TO "service_role";



GRANT ALL ON TABLE "public"."user_config_overrides" TO "anon";
GRANT ALL ON TABLE "public"."user_config_overrides" TO "authenticated";
GRANT ALL ON TABLE "public"."user_config_overrides" TO "service_role";



GRANT ALL ON TABLE "public"."user_profiles" TO "anon";
GRANT ALL ON TABLE "public"."user_profiles" TO "authenticated";
GRANT ALL ON TABLE "public"."user_profiles" TO "service_role";



GRANT ALL ON TABLE "public"."wiki_generation_runs" TO "anon";
GRANT ALL ON TABLE "public"."wiki_generation_runs" TO "authenticated";
GRANT ALL ON TABLE "public"."wiki_generation_runs" TO "service_role";









ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "service_role";






























RESET ALL;
