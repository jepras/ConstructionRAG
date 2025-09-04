# Operations Scripts

This folder contains administrative and operational scripts for managing the ConstructionRAG backend.

## Scripts

### `admin_cleanup_v2.py`

A comprehensive admin script for bulk deletion of indexing runs and all associated data.

#### Purpose
- Bulk delete indexing runs with all related data (documents, chunks, wiki runs, query runs, projects, storage files)
- Clean up storage folders to avoid leaving empty directories
- Maintain database integrity through proper CASCADE deletion order

#### Features
- **Two Operation Modes:**
  - Manual: Specify exact indexing run IDs to delete
  - Automatic: Delete oldest X runs automatically
- **Comprehensive Deletion:** Removes all associated data including:
  - Indexing run documents and chunks
  - Wiki generation runs and pages
  - Query runs that reference the indexing run
  - Associated projects (for user_project uploads)
  - Storage files and folders
- **Safety Features:**
  - Dry-run mode for preview before actual deletion
  - Detailed logging and progress reporting
  - Error handling with failure tracking
  - Confirmation prompts for destructive operations
- **Storage Optimization:**
  - Direct database approach for efficient bulk storage deletion
  - Fallback API recursion for reliability
  - Batch processing to handle Supabase API limits

#### Usage

1. **Configure the script:**
   ```python
   # Edit the configuration section at the top of the file
   INDEXING_RUNS_TO_DELETE = [
       "run-id-1",
       "run-id-2",
       # Add specific indexing run IDs here
   ]
   
   # Or use automatic mode
   USE_AUTOMATIC_MODE = True
   MAX_RUNS_TO_DELETE = 5  # Delete oldest 5 runs
   ```

2. **Run dry-run first (recommended):**
   ```bash
   cd backend
   python operations/admin_cleanup_v2.py --dry-run
   ```

3. **Execute actual deletion:**
   ```bash
   cd backend  
   python operations/admin_cleanup_v2.py
   ```

#### Command Line Options
- `--dry-run`: Preview what would be deleted without making changes
- `--automatic`: Use automatic mode (delete oldest X runs)
- `--max-runs N`: Number of oldest runs to delete in automatic mode

#### Requirements
- Must be run from the `/backend` directory
- Requires Supabase admin credentials (service role key) in `.env`
- Production database access (uses live Supabase instance)

#### What Gets Deleted
For each indexing run, the script will delete:

1. **Database Records:**
   - Indexing run record
   - All associated document records
   - Document chunks (via CASCADE)
   - Wiki generation runs and metadata
   - Query runs that reference this indexing run
   - Associated project (if upload_type = user_project)

2. **Storage Files:**
   - All files in the indexing run's storage folder
   - Project-level folders (for user_project uploads)
   - Empty directory cleanup

#### Technical Details
- **Database Operations:** Uses Supabase admin client to bypass RLS
- **Storage Deletion:** Direct database approach via storage.objects table
- **Batch Processing:** Handles large datasets with configurable batch sizes
- **Error Recovery:** Individual file deletion fallback if batch operations fail
- **Upload Type Handling:** Different logic for `email` vs `user_project` uploads

#### Safety Considerations
- **Always run dry-run first** to verify what will be deleted
- **Irreversible operation** - deleted data cannot be recovered
- **Production database** - affects live data
- **Cascade effects** - related records are automatically deleted

#### Troubleshooting
- Ensure you're running from `/backend` directory
- Check that Supabase environment variables are properly configured
- Verify admin service role key has necessary permissions
- Monitor logs for specific error messages and failed operations