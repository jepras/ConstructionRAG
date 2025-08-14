interface QueryPageProps {
  params: Promise<{
    slug: string;
  }>;
}

export default async function QueryPage({ params }: QueryPageProps) {
  const { slug } = await params;
  
  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground mb-2">Q&A</h1>
        <p className="text-muted-foreground">
          Ask questions about this project's documentation and get AI-powered answers.
        </p>
      </div>
      
      <div className="space-y-4">
        <p className="text-muted-foreground">
          Query interface for project {slug} will be implemented here.
        </p>
      </div>
    </div>
  );
}