"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/components/providers/AuthProvider";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuShortcut,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useUserProjectsWithWikis } from "@/hooks/useApiQueries";
import { Settings, Store, HelpCircle, LogOut } from "lucide-react";

interface HeaderProps {
  variant: "marketing" | "app";
}

export function Header({ variant }: HeaderProps) {
  const { user, isAuthenticated, signOut } = useAuth();
  const router = useRouter();
  const { data: backendProjects = [], isLoading: projectsLoading } = useUserProjectsWithWikis(50);

  function transformUserProject(backendProject: any) {
    const projectName = backendProject.project_name || "Unnamed Project";
    const projectId = backendProject.id;
    const indexingRunId = backendProject.indexing_run_id;

    const projectSlug = `${projectName
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")}-${projectId}`;
    const slug = `${projectSlug}/${indexingRunId}`;

    return {
      id: projectId,
      name: projectName,
      slug,
    };
  }

  const projects = backendProjects.map(transformUserProject);

  const handleSignOut = async () => {
    try {
      await signOut()
      // Redirect to homepage after successful sign out
      router.push('/')
    } catch (error) {
      console.error('Error signing out:', error)
    }
  }

  if (variant === "marketing") {
    return (
      <header className="border-b border-border bg-card">
        <div className="container mx-auto px-4 h-16 flex items-center justify-between">
          {/* Logo */}
          <Link href="/" className="text-xl font-bold text-white">
            specfinder.io
          </Link>

          {/* Navigation */}
          <nav className="hidden md:flex items-center space-x-6">
            <Link
              href="/projects"
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              Public Projects
            </Link>
            <div className="flex items-center space-x-2">
              <Link href="/upload" className="text-muted-foreground hover:text-foreground transition-colors">
                Upload Project
              </Link>
              <span className="bg-primary text-primary-foreground text-xs px-2 py-0.5 rounded">
                free
              </span>
            </div>
          </nav>

          {/* Auth Buttons */}
          <div className="flex items-center space-x-3">
            {isAuthenticated ? (
              <>
                <Link href="/dashboard">
                  <Button variant="ghost" size="sm">
                    Dashboard
                  </Button>
                </Link>
                <Button variant="secondary" size="sm" onClick={handleSignOut}>
                  Sign Out
                </Button>
              </>
            ) : (
              <>
                <Link href="/auth/signin">
                  <Button variant="ghost" size="sm">
                    Sign In
                  </Button>
                </Link>
                <Link href="/auth/signup">
                  <Button variant="default" size="sm">
                    Sign Up
                  </Button>
                </Link>
              </>
            )}
          </div>

          {/* Mobile menu button - TODO: implement mobile menu */}
          <button className="md:hidden text-foreground">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
        </div>
      </header>
    );
  }

  // App variant
  return (
    <header className="border-b border-border bg-card">
      <div className="container mx-auto px-4 h-16 flex items-center justify-between">
        {/* Logo */}
        <Link href="/dashboard" className="text-xl font-bold text-white">
          specfinder.io
        </Link>

        {/* Project Selector */}
        <div className="flex-1 flex justify-center">
          <div className="relative">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="secondary" className="min-w-48">
                  {projectsLoading ? "Loading projects..." : "Select a Project"}
                  <svg className="w-4 h-4 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="center" className="w-64">
                {projectsLoading ? (
                  <DropdownMenuItem disabled>
                    Loading projects...
                  </DropdownMenuItem>
                ) : projects.length === 0 ? (
                  <>
                    <DropdownMenuLabel>No projects found</DropdownMenuLabel>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem asChild>
                      <Link href="/dashboard/new-project" className="cursor-pointer">
                        Create a new project
                      </Link>
                    </DropdownMenuItem>
                  </>
                ) : (
                  <>
                    <DropdownMenuLabel>Your Projects</DropdownMenuLabel>
                    <DropdownMenuSeparator />
                    {projects.map((project) => (
                      <DropdownMenuItem
                        key={project.id}
                        onClick={() => router.push(`/dashboard/projects/${project.slug}`)}
                        className="cursor-pointer"
                      >
                        {project.name}
                      </DropdownMenuItem>
                    ))}
                  </>
                )}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>

        {/* User Dropdown Menu */}
        <div className="flex items-center space-x-3">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="flex items-center gap-2 px-2">
                <div className="w-8 h-8 bg-primary rounded-full flex items-center justify-center text-primary-foreground font-semibold">
                  {user?.email?.[0]?.toUpperCase() || 'U'}
                </div>
                <span className="text-muted-foreground text-sm max-w-32 truncate">
                  {user?.email}
                </span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel>My Account</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem asChild>
                <Link href="/settings" className="cursor-pointer">
                  <Settings className="mr-2 h-4 w-4" />
                  Settings
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem disabled>
                <Store className="mr-2 h-4 w-4" />
                Marketplace
                <DropdownMenuShortcut>Soon</DropdownMenuShortcut>
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <a href="mailto:support@specfinder.io" className="cursor-pointer">
                  <HelpCircle className="mr-2 h-4 w-4" />
                  Support
                </a>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={handleSignOut} className="cursor-pointer">
                <LogOut className="mr-2 h-4 w-4" />
                Sign Out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  );
}