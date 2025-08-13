import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function Home() {
  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">ConstructionRAG</h1>
      
      <Card className="mb-4">
        <CardHeader>
          <CardTitle>Welcome</CardTitle>
          <CardDescription>AI-powered construction document processing</CardDescription>
        </CardHeader>
        <CardContent>
          <p>This is a basic shadcn/ui setup with no custom styling.</p>
          <div className="mt-4">
            <Button>Get Started</Button>
            <Button variant="outline" className="ml-2">Learn More</Button>
          </div>
        </CardContent>
      </Card>

      <div className="grid md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle>Feature 1</CardTitle>
          </CardHeader>
          <CardContent>
            <p>Basic card with minimal styling.</p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle>Feature 2</CardTitle>
          </CardHeader>
          <CardContent>
            <p>Another basic card.</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}