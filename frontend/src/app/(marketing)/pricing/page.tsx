"use client";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { HoverCard, HoverCardContent, HoverCardTrigger } from "@/components/ui/hover-card";
import { Check, X } from "lucide-react";
import { useEffect } from "react";
import Link from "next/link";

interface Feature {
  text: string;
  tooltip?: string;
}

interface FeatureSection {
  title: string;
  features: Feature[];
}

interface PricingTier {
  name: string;
  description: string;
  price: string;
  priceUnit?: string;
  buttonText: string;
  buttonVariant?: "default" | "outline" | "secondary";
  highlighted?: boolean;
  featureSections: FeatureSection[];
  href?: string;
}

const pricingTiers: PricingTier[] = [
  {
    name: "Free",
    description: "Try out the core functionality on your own public projects and share them with your colleagues.",
    price: "€0",
    buttonText: "Get Started",
    buttonVariant: "outline",
    href: "/auth/signup",
    featureSections: [
      {
        title: "Basic features",
        features: [
          { text: "Upload pdf's and generate project overviews" },
          { text: "Ask questions to get answers from your pdf" },
        ]
      },
      {
        title: "Limitations",
        features: [
          { text: "Maximum 50 questions per month", tooltip: "that's a lot" },
          { text: "Max 5 projects" },
          { text: "Max 10 pdf's per project" },
          { text: "Max 100 pages per project" },
          { text: "Only public projects" },
          { text: "English & danish" },
          { text: "LLM chosen by specfinder" },
        ]
      }
    ]
  },
  {
    name: "Pay per project",
    description: "Ideal if you work only on one project at a time. One time purchase, no subscription.",
    price: "€49",
    buttonText: "Purchase",
    buttonVariant: "outline",
    href: "/auth/signup",
    featureSections: [
      {
        title: "Basic features",
        features: [
          { text: "Upload pdf's and generate project overviews" },
          { text: "Ask questions to get answers from your pdf" },
        ]
      },
      {
        title: "Advanced features",
        features: [
          { text: "Private projects" },
          { text: "Checklist feature" },
        ]
      },
      {
        title: "Limitations",
        features: [
          { text: "Unlimited questions" },
          { text: "Max 1 private project with advanced features" },
          { text: "Max 30 pdf's per project" },
          { text: "Max 1000 pages per project" },
          { text: "Public & private projects" },
          { text: "English & danish" },
          { text: "LLM chosen by specfinder" },
        ]
      }
    ]
  },
  {
    name: "Pro",
    description: "Makes sense for you if you work with multiple projects per month and want to share private projects.",
    price: "€49",
    priceUnit: "per month",
    buttonText: "Subscribe",
    buttonVariant: "default",
    highlighted: true,
    href: "/auth/signup",
    featureSections: [
      {
        title: "Basic features",
        features: [
          { text: "Upload pdf's and generate project overviews" },
          { text: "Ask questions to get answers from your pdf" },
        ]
      },
      {
        title: "Advanced features",
        features: [
          { text: "Private projects" },
          { text: "Checklist feature" },
          { text: "Share private projects with team members" },
        ]
      },
      {
        title: "Limitations",
        features: [
          { text: "Unlimited questions" },
          { text: "Max 10 private projects per month" },
          { text: "Max 50 pdf's per project" },
          { text: "Max 5000 pages per project" },
          { text: "Public & private projects" },
          { text: "Request languages" },
          { text: "LLM chosen by specfinder" },
        ]
      }
    ]
  },
  {
    name: "Enterprise",
    description: "Necessary for enterprise security & privacy features where GDPR & controlled storage are important.",
    price: "Custom",
    buttonText: "Contact sales",
    buttonVariant: "outline",
    href: "mailto:hello@specfinder.io?subject=Enterprise%20Pricing",
    featureSections: [
      {
        title: "Basic features",
        features: [
          { text: "Upload pdf's and generate project overviews" },
          { text: "Ask questions to get answers from your pdf" },
        ]
      },
      {
        title: "Advanced features",
        features: [
          { text: "Private projects" },
          { text: "Checklist feature" },
          { text: "Share private projects with team members" },
          { text: "Image in-depth analyser" },
          { text: "Sync project files from SharePoint or Google Drive" },
        ]
      },
      {
        title: "Limitations",
        features: [
          { text: "Unlimited questions" },
          { text: "Unlimited projects" },
          { text: "Unlimited pdf's" },
          { text: "Unlimited pages per project" },
          { text: "Public & private projects" },
          { text: "Request languages" },
          { text: "Option for self hosted LLMs" },
        ]
      }
    ]
  },
];

function FeatureItem({ feature, isLimitation = false }: { feature: Feature; isLimitation?: boolean }) {
  const content = (
    <li className="flex items-start text-sm">
      {isLimitation ? (
        <span className="text-muted-foreground">{feature.text}</span>
      ) : (
        <>
          <Check className="w-4 h-4 text-primary mr-2 mt-0.5 flex-shrink-0" />
          <span className="text-muted-foreground">{feature.text}</span>
        </>
      )}
    </li>
  );

  if (feature.tooltip) {
    return (
      <HoverCard>
        <HoverCardTrigger asChild>
          {content}
        </HoverCardTrigger>
        <HoverCardContent className="w-auto">
          <p className="text-sm">{feature.tooltip}</p>
        </HoverCardContent>
      </HoverCard>
    );
  }

  return content;
}

export default function PricingPage() {
  useEffect(() => {
    document.title = "Pricing - specfinder.io";
  }, []);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="container mx-auto px-6 py-20">
        {/* Header */}
        <div className="text-center mb-16">
          <h1 className="text-5xl font-bold mb-6">Pricing to fit your needs</h1>

        </div>

        {/* Pricing Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8 max-w-7xl mx-auto">
          {pricingTiers.map((tier) => (
            <Card
              key={tier.name}
              className={`relative flex flex-col p-6 ${tier.highlighted
                ? "border-2 border-primary shadow-lg"
                : "border border-border"
                }`}
            >
              {/* Tier Header */}
              <div className="mb-6">
                <h3 className="text-xl font-semibold mb-2">{tier.name}</h3>
                <p className="text-sm text-muted-foreground mb-4 min-h-[3rem]">
                  {tier.description}
                </p>

                {/* Price */}
                <div className="mb-4">
                  <span className="text-4xl font-bold">{tier.price}</span>
                  {tier.priceUnit && (
                    <span className="text-sm text-muted-foreground ml-2">
                      {tier.priceUnit}
                    </span>
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

              {/* Feature Sections */}
              <div className="flex-1 space-y-6">
                {tier.featureSections.map((section, sectionIndex) => (
                  <div key={sectionIndex}>
                    <h4 className="text-sm font-semibold mb-3">{section.title}</h4>
                    {section.features.length === 0 ? (
                      <p className="text-sm text-muted-foreground italic">-</p>
                    ) : (
                      <ul className="space-y-2">
                        {section.features.map((feature, index) => (
                          <FeatureItem
                            key={index}
                            feature={feature}
                            isLimitation={section.title === "Limitations"}
                          />
                        ))}
                      </ul>
                    )}
                  </div>
                ))}
              </div>
            </Card>
          ))}
        </div>

        {/* Footer note */}
        <div className="text-center mt-16">

        </div>
      </div>
    </div>
  );
}