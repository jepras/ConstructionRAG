interface IndexingPageProps {
  params: Promise<{
    slug: string;
  }>;
}

export default async function IndexingPage({ params }: IndexingPageProps) {
  const { slug } = await params;
  
  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground mb-2">Index</h1>
        <p className="text-muted-foreground">
          Monitor document processing progress and view indexing details.
        </p>
      </div>
      
      <div className="space-y-4">
        <p className="text-muted-foreground">
          Indexing progress and details for project {slug} will be implemented here.
        </p>
      </div>
    </div>
  );
}