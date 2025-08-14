interface SettingsPageProps {
  params: Promise<{
    slug: string;
  }>;
}

export default async function SettingsPage({ params }: SettingsPageProps) {
  const { slug } = await params;
  
  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground mb-2">Settings</h1>
        <p className="text-muted-foreground">
          Manage project configuration and access controls.
        </p>
      </div>
      
      <div className="space-y-4">
        <p className="text-muted-foreground">
          Project settings for {slug} will be implemented here.
        </p>
      </div>
    </div>
  );
}