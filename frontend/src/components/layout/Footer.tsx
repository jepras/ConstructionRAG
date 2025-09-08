"use client";

import Link from "next/link";
import Image from "next/image";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function Footer() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const handleNewsletterSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!email) {
      setMessage("Please enter your email");
      return;
    }

    setLoading(true);
    setMessage("");

    try {
      const response = await fetch("/api/newsletter/signup", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email }),
      });

      const data = await response.json();

      if (response.ok) {
        setMessage("Success! Check your email to confirm.");
        setEmail("");
      } else {
        setMessage(data.error || "Something went wrong. Please try again.");
      }
    } catch (error) {
      console.error("Newsletter signup error:", error);
      setMessage("Failed to subscribe. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <footer className="border-t border-border bg-card mt-auto">
      <div className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Brand and Contact */}
          <div className="space-y-4">
            <Link href="/" className="flex items-center gap-2.5 group w-fit">
              <Image
                src="/favicon-32x32.png"
                alt="Specfinder"
                width={28}
                height={28}
                className="w-7 h-7"
                priority
              />
              <span className="text-xl font-semibold text-white/90 group-hover:text-white transition-colors">
                specfinder<span className="text-orange-500">.io</span>
              </span>
            </Link>
            <div className="text-sm text-muted-foreground space-y-1">
              <p>Made in Copenhagen</p>
              <p>hello@specfinder.io</p>
            </div>
          </div>

          {/* Product Links */}
          <div>
            <h3 className="font-semibold text-foreground mb-4 text-sm uppercase tracking-wide">
              Product
            </h3>
            <div className="space-y-3 text-sm">
              <div>
                <Link
                  href="/upload"
                  className="text-muted-foreground hover:text-foreground transition-colors"
                >
                  Upload Project
                </Link>
              </div>
              <div>
                <Link
                  href="/projects"
                  className="text-muted-foreground hover:text-foreground transition-colors"
                >
                  Public Projects
                </Link>
              </div>
              <div>
                <Link
                  href="/pricing"
                  className="text-muted-foreground hover:text-foreground transition-colors"
                >
                  Pricing
                </Link>
              </div>
            </div>
          </div>

          {/* Email Signup */}
          <div>
            <h3 className="font-semibold text-foreground mb-4 text-sm uppercase tracking-wide">
              Sign up for Product Updates
            </h3>
            <form onSubmit={handleNewsletterSignup} className="space-y-3">
              <div className="flex space-x-2">
                <Input
                  type="email"
                  placeholder="Enter your email"
                  className="flex-1"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={loading}
                  required
                />
                <Button type="submit" variant="default" size="sm" disabled={loading}>
                  {loading ? (
                    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                  ) : (
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  )}
                </Button>
              </div>
              {message && (
                <p className={`text-xs ${message.includes("Success") ? "text-green-500" : "text-orange-500"}`}>
                  {message}
                </p>
              )}
              <p className="text-xs text-muted-foreground">
                No spam, just updates on new features and improvements.
              </p>
            </form>
          </div>
        </div>

        {/* Copyright */}
        <div className="border-t border-border mt-8 pt-4">
          <p className="text-sm text-muted-foreground text-center">
            © 2025 specfinder<span className="text-orange-500">.io</span>. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
}