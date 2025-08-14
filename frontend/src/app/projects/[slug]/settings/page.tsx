interface SettingsPageProps {
  params: Promise<{
    slug: string;
  }>;
}

export default async function SettingsPage({ params }: SettingsPageProps) {
  const { slug } = await params;
  
  return (
    <div className="container mx-auto px-4 py-6">
      <h1 className="text-3xl font-bold text-foreground mb-6">
        Settings - {slug}
      </h1>
      <div className="bg-card border border-border rounded-lg p-6">
        <p className="text-muted-foreground">
          Project settings for {slug} will be implemented here.
        </p>
      </div>
    </div>
  );
}