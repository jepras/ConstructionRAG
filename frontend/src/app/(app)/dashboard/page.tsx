import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

// Mock project data - will be replaced with real data later
const mockProjects = [
  {
    id: "1",
    name: "Downtown Tower",
    documentCount: 3,
    status: "Wiki Generated",
  },
  {
    id: "2", 
    name: "Suburban Mall Extension",
    documentCount: 1,
    status: "Wiki Generated",
  },
  {
    id: "3",
    name: "New Bridge Construction", 
    documentCount: 0,
    status: "No Documents",
  },
  {
    id: "4",
    name: "Meridian Heights Development",
    documentCount: 3, 
    status: "Wiki Generated",
  },
  {
    id: "5",
    name: "Heerup Skole",
    documentCount: 3,
    status: "Wiki Generated", 
  },
];

export default function DashboardPage() {
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-start mb-8">
        <div>
          <h1 className="text-3xl font-bold text-supabase-text-light mb-2">
            Projects
          </h1>
          <p className="text-supabase-text">
            Select a project to view its DeepWiki or create a new one.
          </p>
        </div>
        <Button variant="default">
          <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          New Project
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {mockProjects.map((project) => (
          <Card key={project.id} className="hover:border-supabase-green/50 transition-colors cursor-pointer">
            <CardHeader>
              <div className="flex items-start space-x-3">
                <div className="p-2 bg-supabase-dark-3 rounded">
                  <svg className="w-5 h-5 text-supabase-text" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <div className="flex-1 min-w-0">
                  <CardTitle className="text-lg text-supabase-text-light truncate">
                    {project.name}
                  </CardTitle>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center space-x-1 text-supabase-text">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <span>{project.documentCount} Documents</span>
                </div>
              </div>
              <div className="mt-4 flex justify-between items-center">
                <span className="text-xs text-supabase-text">Status</span>
                <div className="flex items-center space-x-1">
                  {project.status === "Wiki Generated" && (
                    <svg className="w-3 h-3 text-supabase-green" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                  )}
                  <span className={`text-xs ${project.status === "Wiki Generated" ? "text-supabase-green" : "text-supabase-text"}`}>
                    {project.status}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}