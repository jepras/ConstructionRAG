"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function Footer() {
  return (
    <footer className="border-t border-supabase-border bg-supabase-dark-2 mt-auto">
      <div className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Brand and Contact */}
          <div className="space-y-4">
            <div className="text-xl font-bold text-supabase-text-light">
              ConstructionRAG
            </div>
            <div className="text-sm text-supabase-text space-y-1">
              <p>Made in Copenhagen</p>
              <p>hello@constructionrag.com</p>
            </div>
          </div>

          {/* Product Links */}
          <div>
            <h3 className="font-semibold text-supabase-text-light mb-4 text-sm uppercase tracking-wide">
              Product
            </h3>
            <div className="space-y-3 text-sm">
              <div>
                <Link 
                  href="/projects" 
                  className="text-supabase-text hover:text-supabase-text-light transition-colors"
                >
                  Public Projects
                </Link>
              </div>
              <div>
                <Link 
                  href="/pricing" 
                  className="text-supabase-text hover:text-supabase-text-light transition-colors"
                >
                  Pricing
                </Link>
              </div>
              <div>
                <Link 
                  href="/upload" 
                  className="text-supabase-text hover:text-supabase-text-light transition-colors"
                >
                  Upload Project
                </Link>
              </div>
            </div>
          </div>

          {/* Email Signup */}
          <div>
            <h3 className="font-semibold text-supabase-text-light mb-4 text-sm uppercase tracking-wide">
              Sign up for Product Updates
            </h3>
            <div className="space-y-3">
              <div className="flex space-x-2">
                <Input 
                  type="email"
                  placeholder="Enter your email"
                  className="flex-1"
                />
                <Button variant="default" size="sm">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </Button>
              </div>
              <p className="text-xs text-supabase-text">
                No spam, just updates on new features and improvements.
              </p>
            </div>
          </div>
        </div>

        {/* Copyright */}
        <div className="border-t border-supabase-border mt-8 pt-4">
          <p className="text-sm text-supabase-text text-center">
            © 2025 ConstructionRAG. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
}