import { Suspense } from 'react';

interface ProjectSettingsPageProps {
  params: Promise<{
    username: string;
    projectSlug: string;
  }>;
}

export async function generateMetadata({ params }: ProjectSettingsPageProps) {
  const { username, projectSlug } = await params;

  return {
    title: `Settings - ${username}/${projectSlug}`,
  };
}

async function ProjectSettingsContent({
  username,
  projectSlug
}: {
  username: string;
  projectSlug: string;
}) {
  return (
    <div className="p-6">
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-foreground mb-2">Project Settings</h1>
          <p className="text-muted-foreground">
            Configure settings for {username}/{projectSlug}
          </p>
        </div>

        <div className="space-y-6">
          <div className="bg-card border border-border rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Project Information</h2>
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium text-muted-foreground">Project Path</label>
                <p className="text-lg font-mono">{username}/{projectSlug}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-muted-foreground">Access Level</label>
                <p className="text-lg">{username === 'anonymous' ? 'Public' : 'Private'}</p>
              </div>
            </div>
          </div>

          <div className="bg-card border border-border rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Coming Soon</h2>
            <p className="text-muted-foreground">
              Project settings functionality is being developed. You'll be able to:
            </p>
            <ul className="mt-4 space-y-2 text-sm text-muted-foreground">
              <li>• Manage project visibility</li>
              <li>• Configure access permissions</li>
              <li>• Update project metadata</li>
              <li>• Manage indexing settings</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}

export default async function ProjectSettingsPage({ params }: ProjectSettingsPageProps) {
  const { username, projectSlug } = await params;

  return (
    <Suspense fallback={
      <div className="p-6">
        <div className="max-w-4xl mx-auto">
          <div className="animate-pulse">
            <div className="h-8 bg-muted rounded w-1/3 mb-2"></div>
            <div className="h-4 bg-muted rounded w-1/2 mb-8"></div>
            <div className="space-y-6">
              <div className="h-48 bg-muted rounded"></div>
              <div className="h-32 bg-muted rounded"></div>
            </div>
          </div>
        </div>
      </div>
    }>
      <ProjectSettingsContent username={username} projectSlug={projectSlug} />
    </Suspense>
  );
}