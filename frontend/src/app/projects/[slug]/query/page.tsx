interface QueryPageProps {
  params: Promise<{
    slug: string;
  }>;
}

export default async function QueryPage({ params }: QueryPageProps) {
  const { slug } = await params;
  
  return (
    <div className="container mx-auto px-4 py-6">
      <h1 className="text-3xl font-bold text-foreground mb-6">
        Q&A - {slug}
      </h1>
      <div className="bg-card border border-border rounded-lg p-6">
        <p className="text-muted-foreground">
          Query interface for project {slug} will be implemented here.
        </p>
      </div>
    </div>
  );
}