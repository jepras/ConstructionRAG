"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/components/providers/AuthProvider";
import { apiClient } from "@/lib/api-client";
import { toast } from "sonner";

type SettingsTab = "profile" | "billing" | "organisation";

const settingsNavItems = [
  {
    id: "profile" as SettingsTab,
    label: "Profile",
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
      </svg>
    ),
  },
  {
    id: "billing" as SettingsTab,
    label: "Billing", 
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
      </svg>
    ),
  },
  {
    id: "organisation" as SettingsTab,
    label: "Organisation",
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
      </svg>
    ),
  },
];

function ProfileSection({ user }: { user: { id: string; email: string; profile?: { full_name?: string } } | null }) {
  const [fullName, setFullName] = useState(user?.profile?.full_name || "");
  const [email, setEmail] = useState(user?.email || "");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSaveChanges = async () => {
    setIsLoading(true);
    try {
      await apiClient.updateUserProfile({
        full_name: fullName,
        email: email,
      });
      
      toast.success('Profile updated successfully!');
    } catch (error) {
      console.error('Failed to update profile:', error);
      toast.error('Failed to update profile. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handlePasswordChange = async () => {
    if (newPassword !== confirmPassword) {
      toast.error("New passwords don't match");
      return;
    }
    setIsLoading(true);
    // TODO: Implement password change API call
    setTimeout(() => {
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      toast.success("Password updated successfully!");
      setIsLoading(false);
    }, 1000);
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-foreground">Profile Settings</CardTitle>
          <p className="text-sm text-muted-foreground">
            Update your personal information.
          </p>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="fullName" className="text-sm font-medium text-foreground">
              Full Name
            </Label>
            <Input 
              id="fullName"
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="bg-input"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="email" className="text-sm font-medium text-foreground">
              Email Address
            </Label>
            <Input 
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="bg-input"
            />
          </div>

          <div className="pt-4">
            <Button 
              variant="default" 
              onClick={handleSaveChanges}
              disabled={isLoading}
            >
              {isLoading ? "Saving..." : "Save Changes"}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-foreground">Change Password</CardTitle>
          <p className="text-sm text-muted-foreground">
            Update your account password.
          </p>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="currentPassword" className="text-sm font-medium text-foreground">
              Current Password
            </Label>
            <Input 
              id="currentPassword"
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              className="bg-input"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="newPassword" className="text-sm font-medium text-foreground">
              New Password
            </Label>
            <Input 
              id="newPassword"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="bg-input"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="confirmPassword" className="text-sm font-medium text-foreground">
              Confirm New Password
            </Label>
            <Input 
              id="confirmPassword"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="bg-input"
            />
          </div>

          <div className="pt-4">
            <Button 
              variant="default" 
              onClick={handlePasswordChange}
              disabled={isLoading || !currentPassword || !newPassword || !confirmPassword}
            >
              {isLoading ? "Updating..." : "Update Password"}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function BillingSection() {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-foreground">Billing</CardTitle>
              <p className="text-sm text-muted-foreground">
                Manage your subscription and payment details.
              </p>
            </div>
            <Badge variant="secondary" className="text-xs">
              Coming Soon
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex items-center justify-between p-4 border border-border rounded-lg">
            <div>
              <p className="font-medium text-foreground">Current Plan: <span className="text-green-600">Pro Tier</span></p>
              <p className="text-sm text-muted-foreground">Next renewal on July 31, 2024.</p>
            </div>
            <Button variant="default" disabled>
              Manage Subscription
            </Button>
          </div>

          <div>
            <h3 className="text-lg font-medium text-foreground mb-4">Payment History</h3>
            <div className="border border-border rounded-lg">
              <div className="grid grid-cols-3 gap-4 p-4 border-b border-border bg-muted/50">
                <div className="font-medium text-foreground">Date</div>
                <div className="font-medium text-foreground">Amount</div>
                <div className="font-medium text-foreground">Status</div>
              </div>
              <div className="grid grid-cols-3 gap-4 p-4 border-b border-border">
                <div className="text-foreground">June 30, 2024</div>
                <div className="text-foreground">$99.00</div>
                <div>
                  <Badge variant="secondary" className="bg-green-100 text-green-800 border-green-200">
                    Paid
                  </Badge>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-4 p-4">
                <div className="text-foreground">May 31, 2024</div>
                <div className="text-foreground">$99.00</div>
                <div>
                  <Badge variant="secondary" className="bg-green-100 text-green-800 border-green-200">
                    Paid
                  </Badge>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function OrganisationSection() {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-foreground">Organisation</CardTitle>
              <p className="text-sm text-muted-foreground">
                Manage your team members and workspace settings.
              </p>
            </div>
            <Badge variant="secondary" className="text-xs">
              Coming Soon
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="orgName" className="text-sm font-medium text-foreground">
              Organisation Name
            </Label>
            <Input 
              id="orgName"
              type="text"
              defaultValue="User's Workspace"
              disabled
              className="bg-input"
            />
          </div>

          <div>
            <h3 className="text-lg font-medium text-foreground mb-4">Team Members</h3>
            <div className="border border-border rounded-lg">
              <div className="flex items-center justify-between p-4 border-b border-border">
                <div>
                  <p className="font-medium text-foreground">You (User)</p>
                  <p className="text-sm text-muted-foreground">user@example.com</p>
                </div>
                <Badge variant="outline" className="text-xs">
                  Owner
                </Badge>
              </div>
              <div className="flex items-center justify-between p-4">
                <div>
                  <p className="font-medium text-foreground">Jane Doe</p>
                  <p className="text-sm text-muted-foreground">jane@example.com</p>
                </div>
                <Badge variant="outline" className="text-xs">
                  Admin
                </Badge>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<SettingsTab>("profile");
  const { user, isLoading } = useAuth();
  
  useEffect(() => {
    document.title = "Settings - specfinder.io";
  }, []);

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-foreground mb-2">
            Settings
          </h1>
          <p className="text-muted-foreground">
            Manage your account and workspace settings.
          </p>
        </div>
        <div className="text-center py-8">
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  const renderTabContent = () => {
    switch (activeTab) {
      case "profile":
        return <ProfileSection user={user} />;
      case "billing":
        return <BillingSection />;
      case "organisation":
        return <OrganisationSection />;
      default:
        return <ProfileSection user={user} />;
    }
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-foreground mb-2">
          Settings
        </h1>
        <p className="text-muted-foreground">
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
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center space-x-3 px-3 py-2 rounded-md text-left transition-colors ${
                  activeTab === item.id
                    ? "bg-accent text-accent-foreground border border-border"
                    : "text-muted-foreground hover:text-foreground hover:bg-accent"
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
          {renderTabContent()}
        </div>
      </div>
    </div>
  );
}