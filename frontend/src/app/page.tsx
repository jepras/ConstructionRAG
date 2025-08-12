import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

export default function Home() {
  return (
    <div className="min-h-screen bg-background text-foreground p-8">
      <div className="container mx-auto max-w-4xl">
        <header className="text-center mb-8">
          <h1 className="text-4xl font-bold mb-4 text-primary">ConstructionRAG</h1>
          <p className="text-xl text-muted-foreground">AI-powered construction document processing and Q&A system</p>
        </header>

        {/* Supabase Color Test Section */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>Supabase Color System Test</CardTitle>
            <CardDescription>Testing our custom Supabase-inspired color palette</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-supabase-dark text-supabase-text-light p-4 rounded border">
                <p className="font-semibold">supabase-dark</p>
                <p className="text-sm">#181818</p>
              </div>
              <div className="bg-supabase-dark-2 text-supabase-text-light p-4 rounded border">
                <p className="font-semibold">supabase-dark-2</p>
                <p className="text-sm">#232323</p>
              </div>
              <div className="bg-supabase-dark-3 text-supabase-text-light p-4 rounded border">
                <p className="font-semibold">supabase-dark-3</p>
                <p className="text-sm">#2a2a2a</p>
              </div>
              <div className="bg-supabase-green text-white p-4 rounded border">
                <p className="font-semibold">supabase-green</p>
                <p className="text-sm">#24b47e</p>
              </div>
            </div>
            <div className="border border-supabase-border p-4 rounded">
              <p className="text-supabase-text">Text in supabase-text color (#a8a8a8)</p>
              <p className="text-supabase-text-light">Text in supabase-text-light color (#e0e0e0)</p>
            </div>
          </CardContent>
        </Card>

        {/* shadcn/ui Components Test Section */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>shadcn/ui Components Test</CardTitle>
            <CardDescription>Testing shadcn/ui components with our color system</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">Buttons</h3>
              <div className="flex flex-wrap gap-4">
                <Button variant="default">Primary Button</Button>
                <Button variant="secondary">Secondary Button</Button>
                <Button variant="outline">Outline Button</Button>
                <Button variant="ghost">Ghost Button</Button>
                <Button variant="destructive">Destructive Button</Button>
              </div>
            </div>

            <div className="space-y-4">
              <h3 className="text-lg font-semibold">Form Elements</h3>
              <div className="space-y-2">
                <Input placeholder="Enter your email..." />
                <Input placeholder="Enter your password..." type="password" />
              </div>
            </div>

            <div className="space-y-4">
              <h3 className="text-lg font-semibold">Nested Cards</h3>
              <div className="grid md:grid-cols-2 gap-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Feature 1</CardTitle>
                    <CardDescription>Upload construction documents</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground">
                      Drag and drop your PDF files to get started with document analysis.
                    </p>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Feature 2</CardTitle>
                    <CardDescription>AI-powered Q&A</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground">
                      Ask questions about your construction projects and get instant answers.
                    </p>
                  </CardContent>
                </Card>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Dark Theme Verification */}
        <Card>
          <CardHeader>
            <CardTitle>Theme Verification</CardTitle>
            <CardDescription>Verifying our dark theme implementation</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <p>This page should display with:</p>
              <ul className="list-disc pl-6 space-y-1 text-muted-foreground">
                <li>Dark background (#181818)</li>
                <li>Light text (#e0e0e0)</li>
                <li>Green primary color (#24b47e)</li>
                <li>Proper contrast and readability</li>
                <li>Inter font family</li>
              </ul>
              <div className="mt-4">
                <Button className="w-full md:w-auto">
                  ✓ Phase 1 Complete - Styling System Ready
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}