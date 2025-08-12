"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

const settingsNavItems = [
  {
    id: "profile",
    label: "Profile",
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
      </svg>
    ),
    active: true,
  },
  {
    id: "billing",
    label: "Billing", 
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
      </svg>
    ),
    active: false,
  },
  {
    id: "organisation",
    label: "Organisation",
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
      </svg>
    ),
    active: false,
  },
];

export default function SettingsPage() {
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-supabase-text-light mb-2">
          Settings
        </h1>
        <p className="text-supabase-text">
          Manage your account and workspace settings.
        </p>
      </div>

      <div className="flex gap-8">
        {/* Sidebar Navigation */}
        <div className="w-64 flex-shrink-0">
          <nav className="space-y-2">
            {settingsNavItems.map((item) => (
              <button
                key={item.id}
                className={`w-full flex items-center space-x-3 px-3 py-2 rounded-md text-left transition-colors ${
                  item.active
                    ? "bg-supabase-dark-3 text-supabase-text-light border border-supabase-border"
                    : "text-supabase-text hover:text-supabase-text-light hover:bg-supabase-dark-3"
                }`}
              >
                {item.icon}
                <span>{item.label}</span>
              </button>
            ))}
          </nav>
        </div>

        {/* Main Content */}
        <div className="flex-1">
          <Card>
            <CardHeader>
              <CardTitle className="text-supabase-text-light">Profile Settings</CardTitle>
              <p className="text-sm text-supabase-text">
                Update your personal information.
              </p>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <label className="text-sm font-medium text-supabase-text-light">
                  Full Name
                </label>
                <Input 
                  type="text"
                  defaultValue="User"
                  className="bg-supabase-dark-3"
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-supabase-text-light">
                  Email Address
                </label>
                <Input 
                  type="email"
                  defaultValue="user@example.com"
                  className="bg-supabase-dark-3"
                />
              </div>

              <div className="pt-4">
                <Button variant="default">
                  Save Changes
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}