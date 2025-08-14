import { revalidateTag, revalidatePath } from 'next/cache';
import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { type, projectId, runId, indexingRunId } = body;

    // Verify the request has required fields
    if (!type) {
      return NextResponse.json(
        { error: 'Missing required field: type' },
        { status: 400 }
      );
    }

    let revalidatedPaths: string[] = [];

    switch (type) {
      case 'wiki_generation_complete':
        if (indexingRunId) {
          // Revalidate specific project page
          const projectSlug = `project-${indexingRunId}`;
          const projectPath = `/projects/${projectSlug}`;
          
          revalidatePath(projectPath);
          revalidatePath(`${projectPath}/query`);
          revalidatePath(`${projectPath}/indexing`);
          revalidatePath(`${projectPath}/settings`);
          
          revalidatedPaths = [
            projectPath,
            `${projectPath}/query`,
            `${projectPath}/indexing`,
            `${projectPath}/settings`
          ];
          
          // Revalidate tag for wiki content
          if (runId) {
            revalidateTag(`wiki-${runId}`);
          }
        }
        
        // Revalidate public projects grid
        revalidatePath('/projects');
        revalidatedPaths.push('/projects');
        break;

      case 'indexing_complete':
        if (indexingRunId) {
          // Revalidate project pages that might now be available
          revalidatePath('/projects');
          revalidatedPaths = ['/projects'];
        }
        break;

      case 'project_updated':
        if (projectId) {
          const projectPath = `/projects/${projectId}`;
          revalidatePath(projectPath);
          revalidatedPaths = [projectPath];
        }
        break;

      default:
        return NextResponse.json(
          { error: `Unknown revalidation type: ${type}` },
          { status: 400 }
        );
    }

    return NextResponse.json({
      revalidated: true,
      paths: revalidatedPaths,
      timestamp: new Date().toISOString(),
    });

  } catch (error) {
    console.error('Revalidation error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}