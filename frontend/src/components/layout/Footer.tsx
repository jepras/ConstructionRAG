"use client";

import Link from "next/link";
import Image from "next/image";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function Footer() {
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
              <p className="text-xs text-muted-foreground">
                No spam, just updates on new features and improvements.
              </p>
            </div>
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