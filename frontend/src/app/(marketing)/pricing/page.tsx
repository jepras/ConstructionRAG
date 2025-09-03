"use client";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Check } from "lucide-react";
import Link from "next/link";

interface PricingTier {
  name: string;
  description: string;
  price: string;
  priceUnit?: string;
  buttonText: string;
  buttonVariant?: "default" | "outline" | "secondary";
  highlighted?: boolean;
  features: string[];
  href?: string;
}

const pricingTiers: PricingTier[] = [
  {
    name: "Free",
    description: "For personal use only with limited features and support.",
    price: "$0",
    priceUnit: "includes 1 user.",
    buttonText: "Get Started",
    buttonVariant: "outline",
    href: "/auth/signup",
    features: [
      "Live Collaboration",
      "1 GB Storage",
      "2 Projects",
      "Basic Support",
      "Limited Customization",
      "Limited Integration",
      "Limited API Access",
    ],
  },
  {
    name: "Pay per project",
    description: "For small businesses with all the features and support.",
    price: "$49",
    priceUnit: "Per project, one-time.",
    buttonText: "Purchase",
    buttonVariant: "outline",
    href: "/auth/signup",
    features: [
      "Everything in Free, and:",
      "Up to 5 collaborators",
      "10 GB storage per project",
      "Priority Support",
      "Full Customization",
      "Full Integration",
      "Full API Access",
      "AI-powered Q&A",
    ],
  },
  {
    name: "Team subscription",
    description: "For teams and organizations with advanced features and support.",
    price: "$99",
    priceUnit: "per user, per month.",
    buttonText: "Purchase",
    buttonVariant: "default",
    highlighted: true,
    href: "/auth/signup",
    features: [
      "Everything in Pay per project, and:",
      "Unlimited projects",
      "50 GB storage per user",
      "Dedicated Support",
      "Advanced Customization",
      "Analytics & Reporting",
      "User Roles & Permissions",
      "Single Sign-On (SSO)",
    ],
  },
  {
    name: "Enterprise",
    description: "For large companies with custom features, support, and security.",
    price: "Custom",
    buttonText: "Contact sales",
    buttonVariant: "outline",
    href: "mailto:hello@specfinder.io?subject=Enterprise%20Pricing",
    features: [
      "Everything in Team, and:",
      "Unlimited Storage",
      "Dedicated Account Manager",
      "Custom Expert Modules",
      "On-premise deployment",
      "Security Audits & Compliance",
      "Custom Integration & APIs",
      "24/7 Priority Support",
    ],
  },
];

export default function PricingPage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="container mx-auto px-6 py-20">
        {/* Header */}
        <div className="text-center mb-16">
          <h1 className="text-5xl font-bold mb-6">Pricing</h1>
          <p className="text-xl text-muted-foreground max-w-3xl mx-auto">
            Check out our affordable pricing plans below and choose the one that suits
            you best. If you need a custom plan, please contact us.
          </p>
        </div>

        {/* Pricing Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8 max-w-7xl mx-auto">
          {pricingTiers.map((tier) => (
            <Card
              key={tier.name}
              className={`relative flex flex-col p-8 ${tier.highlighted
                  ? "border-2 border-primary shadow-lg"
                  : "border border-border"
                }`}
            >
              {/* Tier Header */}
              <div className="mb-6">
                <h3 className="text-xl font-semibold mb-2">{tier.name}</h3>
                <p className="text-sm text-muted-foreground mb-4">
                  {tier.description}
                </p>

                {/* Price */}
                <div className="mb-4">
                  <span className="text-4xl font-bold">{tier.price}</span>
                  {tier.priceUnit && (
                    <p className="text-sm text-muted-foreground mt-1">
                      {tier.priceUnit}
                    </p>
                  )}
                </div>

                {/* CTA Button */}
                <Link href={tier.href || "#"}>
                  <Button
                    className="w-full"
                    variant={tier.buttonVariant || "outline"}
                  >
                    {tier.buttonText}
                  </Button>
                </Link>
              </div>

              {/* Features */}
              <div className="flex-1">
                <h4 className="text-sm font-semibold mb-4">Features</h4>
                <ul className="space-y-3">
                  {tier.features.map((feature, index) => (
                    <li
                      key={index}
                      className={`flex items-start text-sm ${feature.startsWith("Everything")
                          ? "font-semibold mb-2"
                          : ""
                        }`}
                    >
                      <Check className="w-4 h-4 text-primary mr-2 mt-0.5 flex-shrink-0" />
                      <span className="text-muted-foreground">{feature}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}