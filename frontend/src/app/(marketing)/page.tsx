"use client";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useState } from "react";
import { Search, Upload, MessageSquare, Download, Info, Eye, ArrowUp, Mic } from "lucide-react";
import Link from "next/link";

export default function Home() {
  const [query, setQuery] = useState("");
  const [showResponse, setShowResponse] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);

  const handleQuerySubmit = () => {
    if (query.trim()) {
      setShowResponse(true);
      setCurrentPage(currentPage === 1 ? 2 : 1); // Toggle between different mock pages
      setQuery(""); // Clear input after sending
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleQuerySubmit();
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Main Content */}
      <div className="container mx-auto px-6 py-12">
        <div className="text-center mb-12">
          <h1 className="text-5xl font-bold mb-4">
            Any project detail, a <span className="text-primary">quick search</span> away.
          </h1>
          <p className="text-xl text-muted-foreground mb-8">
            Get <span className="font-semibold text-foreground">precise, source-verified</span> answers from deep within your project documents instantly.
          </p>
        </div>

        {/* Demo Interface */}
        <div className="max-w-6xl mx-auto">
          <div className="grid md:grid-cols-2 gap-8 items-start">
            {/* Chat Interface */}
            <div className="bg-card border border-border rounded-lg p-6">
              {/* Existing Message */}
              <div className="mb-6">
                <div className="bg-primary text-primary-foreground p-3 rounded-lg inline-block max-w-sm">
                  Hvad er definitionerne på en 'mindre byfornyelsessag' ifølge dokumentet?
                </div>
              </div>

              {/* Response */}
              <div className="mb-6">
                <div className="flex items-start space-x-3">
                  <div className="w-8 h-8 bg-primary rounded-full flex items-center justify-center flex-shrink-0">
                    <MessageSquare className="w-4 h-4 text-primary-foreground" />
                  </div>
                  <div className="bg-secondary p-4 rounded-lg max-w-md">
                    <p className="text-sm text-secondary-foreground">
                      En 'mindre byfornyelsessag' defineres som en sag på op til 5 mio. kr. i samlede omkostninger.
                    </p>
                  </div>
                </div>
              </div>

              {/* New response if query was submitted */}
              {showResponse && (
                <div className="mb-6">
                  <div className="flex items-start space-x-3">
                    <div className="w-8 h-8 bg-primary rounded-full flex items-center justify-center flex-shrink-0">
                      <MessageSquare className="w-4 h-4 text-primary-foreground" />
                    </div>
                    <div className="bg-secondary p-4 rounded-lg max-w-md">
                      <p className="text-sm text-secondary-foreground">
                        Based on the construction specifications, standard concrete curing time is 28 days for full strength development, though initial setting occurs within 24-48 hours depending on environmental conditions.
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Input */}
              <div className="relative">
                <Input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Ask anything"
                  className="bg-input border-border text-foreground placeholder-muted-foreground pr-24"
                />
                <div className="absolute right-2 top-1/2 transform -translate-y-1/2 flex space-x-1">
                  <Button size="sm" variant="ghost" className="p-2">
                    <Mic className="w-4 h-4" />
                  </Button>
                  <Button
                    onClick={handleQuerySubmit}
                    size="sm"
                    variant="ghost"
                    className="p-2"
                  >
                    <ArrowUp className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </div>

            {/* PDF Viewer */}
            <div className="bg-card border border-border rounded-lg overflow-hidden">
              {/* PDF Header */}
              <div className="bg-secondary p-3 flex items-center justify-between border-b border-border">
                <div className="flex items-center space-x-2">
                  <span className="text-sm font-medium text-secondary-foreground">small-pdf.pdf</span>
                  <span className="text-xs text-muted-foreground">Page {currentPage} of 4</span>
                </div>
                <div className="flex items-center space-x-2">
                  <Button variant="ghost" size="sm">
                    <Info className="w-4 h-4" />
                  </Button>
                  <Button variant="ghost" size="sm">
                    <Search className="w-4 h-4" />
                  </Button>
                  <Button variant="ghost" size="sm">
                    <Eye className="w-4 h-4" />
                  </Button>
                  <Button variant="ghost" size="sm">
                    <Download className="w-4 h-4" />
                  </Button>
                </div>
              </div>

              {/* PDF Content */}
              <div className="p-6 bg-white text-black min-h-96">
                <div className="mb-4">
                  <h2 className="text-lg font-bold text-primary mb-4">BEDRE BYGGETIK</h2>
                  <span className="text-xs text-gray-500 mb-2 block">Minimeret udbudsmateriale</span>
                </div>

                <div className="space-y-4">
                  <div>
                    <h3 className="text-sm font-semibold mb-2 flex items-center">
                      <span className="bg-gray-200 rounded-full w-5 h-5 flex items-center justify-center text-xs mr-2">0</span>
                      Indledning
                    </h3>
                  </div>

                  <div className="text-sm leading-relaxed space-y-3">
                    <p>
                      Dette projekt præsenterer et eksempel på et forenklet udbudsmateriale til
                      mindre omfattende byfornyelsessager.
                      <mark className="bg-orange-200">
                        Mindre byfornyelsessager defineres som sager på op til 5 mio. kr. i samlede omkostninger
                      </mark>
                      (ca. 3 mio. kr. i håndværkerudgifter).
                    </p>

                    <p>
                      Abildhauge A/S har i samarbejde med entreprenørerne CoG A/S og B.
                      Nygaard Sørensen A/S udarbejdet et forenklet udbudsmateriale og giver bud
                      på, hvordan det minimerede udbud berører rådgiver, entreprenør og
                      bygherreomkostninger – herunder overvejelser om, hvordan dette påvirker
                      udbudsformen.
                    </p>

                    <p>
                      Projektet viser, at det er muligt at skære væsentligt i papirmængden ved
                      udbud af mindre sager og samtidig bevare kvaliteten i udbudsmaterialet.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* CTA Buttons */}
          <div className="flex justify-center space-x-4 mt-12">
            <Link href="/upload">
              <Button className="px-8 py-3 text-lg">
                Upload Project
              </Button>
            </Link>
            <Link href="/projects">
              <Button variant="outline" className="px-8 py-3 text-lg">
                Explore public projects
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* Bottom Section */}
      <div className="container mx-auto px-6 py-20">
        <div className="text-center mb-16">
          <h2 className="text-4xl font-bold mb-4">
            From <span className="text-foreground">Piles of PDFs</span><br />
            <span className="text-primary">To Instant Answers</span>
          </h2>
        </div>

        <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
          {/* Step 1 */}
          <div className="text-center">
            <div className="bg-card border border-border rounded-lg p-8 mb-6">
              <div className="w-12 h-12 bg-primary rounded-full flex items-center justify-center mx-auto mb-4 text-xl font-bold text-primary-foreground">
                1
              </div>
              <h3 className="text-xl font-semibold mb-4 text-card-foreground">Upload Your Documents</h3>
              <div className="flex justify-center items-center space-x-4 mb-6">
                <Upload className="w-8 h-8 text-muted-foreground" />
                <ArrowUp className="w-6 h-6 text-muted-foreground" />
              </div>
              <p className="text-lg font-semibold mb-2 text-card-foreground">Drag & Drop Your Project</p>
              <p className="text-muted-foreground text-sm">
                Drag and drop your project folder. We process PDFs, spreadsheets, and CAD files to build a complete picture.
              </p>
            </div>
          </div>

          {/* Step 2 */}
          <div className="text-center">
            <div className="bg-card border border-border rounded-lg p-8 mb-6">
              <div className="w-12 h-12 bg-primary rounded-full flex items-center justify-center mx-auto mb-4 text-xl font-bold text-primary-foreground">
                2
              </div>
              <h3 className="text-xl font-semibold mb-4 text-card-foreground">Get a Personalised Overview</h3>
              <div className="bg-secondary border border-border rounded p-4 mb-6">
                <div className="text-left">
                  <div className="flex items-center space-x-2 mb-2">
                    <div className="w-4 h-4 bg-primary rounded"></div>
                    <span className="text-sm text-secondary-foreground">Overview</span>
                  </div>
                  <div className="bg-muted h-2 rounded mb-2"></div>
                  <div className="bg-muted h-2 rounded mb-2 w-3/4"></div>
                  <div className="bg-muted h-2 rounded w-1/2"></div>
                </div>
              </div>
              <p className="text-muted-foreground text-sm">
                Our AI synthesizes information into an interactive overview, tailored with custom checklists, tables, and charts for your role.
              </p>
            </div>
          </div>

          {/* Step 3 */}
          <div className="text-center">
            <div className="bg-card border border-border rounded-lg p-8 mb-6">
              <div className="w-12 h-12 bg-primary rounded-full flex items-center justify-center mx-auto mb-4 text-xl font-bold text-primary-foreground">
                3
              </div>
              <h3 className="text-xl font-semibold mb-4 text-card-foreground">Ask Critical Questions</h3>
              <div className="bg-secondary border border-border rounded-lg p-4 mb-6 space-y-3">
                {/* Chat-like interface */}
                <div className="flex justify-end">
                  <div className="bg-primary text-primary-foreground p-2 rounded-lg text-xs max-w-xs text-right">
                    What are the longest lead time items?
                  </div>
                </div>
                <div className="flex items-start space-x-2">
                  <div className="w-5 h-5 bg-primary rounded-full flex items-center justify-center flex-shrink-0 mt-1">
                    <MessageSquare className="w-3 h-3 text-primary-foreground" />
                  </div>
                  <div className="bg-muted p-2 rounded-lg text-xs text-muted-foreground">
                    Custom steel trusses (TR-1) require a 16 week lead time. [procurement.xlsx]
                  </div>
                </div>
                <div className="flex justify-end">
                  <div className="bg-primary text-primary-foreground p-2 rounded-lg text-xs max-w-xs text-right">
                    Any conflicts between electrical and HVAC plans?
                  </div>
                </div>
                <div className="flex items-start space-x-2">
                  <div className="w-5 h-5 bg-primary rounded-full flex items-center justify-center flex-shrink-0 mt-1">
                    <MessageSquare className="w-3 h-3 text-primary-foreground" />
                  </div>
                  <div className="bg-muted p-2 rounded-lg text-xs text-muted-foreground">
                    Yes, a duct clashes with a cable tray on Floor 5. [coordination.pdf, p.9]
                  </div>
                </div>
              </div>
              <p className="text-muted-foreground text-sm">
                Query documents in plain English and get immediate, accurate answers with source citations.
              </p>
            </div>
          </div>
        </div>
      </div>

    </div>
  );
}