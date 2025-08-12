"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";

interface HeaderProps {
  variant: "marketing" | "app";
}

export function Header({ variant }: HeaderProps) {
  if (variant === "marketing") {
    return (
      <header className="border-b border-supabase-border bg-supabase-dark">
        <div className="container mx-auto px-4 h-16 flex items-center justify-between">
          {/* Logo */}
          <Link href="/" className="text-xl font-bold text-supabase-text-light">
            ConstructionRAG
          </Link>

          {/* Navigation */}
          <nav className="hidden md:flex items-center space-x-6">
            <Link 
              href="/projects" 
              className="text-supabase-text hover:text-supabase-text-light transition-colors"
            >
              Public Projects
            </Link>
            <div className="flex items-center space-x-2">
              <Button variant="secondary" size="sm">
                Upload Project
              </Button>
              <span className="bg-supabase-green text-white text-xs px-2 py-1 rounded">
                free
              </span>
            </div>
          </nav>

          {/* Auth Buttons */}
          <div className="flex items-center space-x-3">
            <Link href="/dashboard">
              <Button variant="ghost" size="sm">
                Log In
              </Button>
            </Link>
            <Link href="/dashboard">
              <Button variant="default" size="sm">
                Sign Up
              </Button>
            </Link>
          </div>

          {/* Mobile menu button - TODO: implement mobile menu */}
          <button className="md:hidden text-supabase-text-light">
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
    <header className="border-b border-supabase-border bg-supabase-dark">
      <div className="container mx-auto px-4 h-16 flex items-center justify-between">
        {/* Logo */}
        <Link href="/dashboard" className="text-xl font-bold text-supabase-text-light">
          ConstructionRAG
        </Link>

        {/* Project Selector */}
        <div className="flex-1 flex justify-center">
          <div className="relative">
            <Button variant="secondary" className="min-w-48">
              Select a Project
              <svg className="w-4 h-4 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </Button>
          </div>
        </div>

        {/* User Avatar */}
        <div className="flex items-center space-x-3">
          <Link href="/settings">
            <Button variant="ghost" size="sm">
              Settings
            </Button>
          </Link>
          <Link href="/settings">
            <div className="w-8 h-8 bg-supabase-green rounded-full flex items-center justify-center text-white font-semibold cursor-pointer">
              U
            </div>
          </Link>
        </div>
      </div>
    </header>
  );
}