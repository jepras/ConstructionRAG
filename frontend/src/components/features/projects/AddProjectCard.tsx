'use client';

import Link from 'next/link';
import { Plus } from 'lucide-react';

export default function AddProjectCard() {
  return (
    <Link 
      href="/upload"
      className="group relative flex flex-col items-center justify-center p-6 rounded-lg border border-primary/20 bg-primary/5 hover:bg-primary/10 hover:border-primary/40 transition-all duration-200 min-h-[200px]"
    >
      <div className="flex flex-col items-center text-center space-y-3">
        <div className="w-12 h-12 rounded-full bg-primary/10 group-hover:bg-primary/20 flex items-center justify-center transition-colors">
          <Plus className="w-6 h-6 text-primary" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-foreground mb-1">
            Add Project
          </h3>
          <p className="text-sm text-muted-foreground">
            Create public project or sign up to create private projects.
          </p>
        </div>
      </div>
    </Link>
  );
}