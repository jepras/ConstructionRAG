"use client";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useState, useEffect, useRef } from "react";
import { Search, Upload, MessageSquare, Download, Info, ArrowUp, Mic, Play } from "lucide-react";
import Link from "next/link";
import Image from "next/image";
import HowItWorksCard, { ProcessingDiagram } from "@/components/HowItWorksCard";
import { DragDropVisual } from "@/components/DragDropVisual";

export default function Home() {
  const [query, setQuery] = useState("What are the key requirements for concrete curing?");
  const [showResponse, setShowResponse] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [showTyping, setShowTyping] = useState(false);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [hasAsked, setHasAsked] = useState(false);
  const [videoPlaying, setVideoPlaying] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);

  const handleQuerySubmit = () => {
    if (query.trim() && !isLoading && !hasAsked) {
      const submittedQuery = query;
      setIsLoading(true);
      setHasAsked(true);

      // Show user message immediately
      setTimeout(() => {
        setShowTyping(true);

        // Start PDF loading during typing
        setTimeout(() => {
          setPdfLoading(true);
        }, 800); // Start PDF loading 0.8s into typing

        // Show AI response after typing simulation
        setTimeout(() => {
          setShowTyping(false);
          setShowResponse(true);

          // Complete PDF loading shortly after response
          setTimeout(() => {
            setPdfLoading(false);
            setCurrentPage(currentPage === 1 ? 2 : 1); // Toggle between different mock pages
            setIsLoading(false);
          }, 600); // PDF loads 0.6s after response appears
        }, 1500); // 1.5s typing simulation
      }, 100); // Small delay to show message
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
            Any project detail - <span className="text-primary">instantly available</span>
          </h1>
          <p className="text-xl text-muted-foreground mb-8">
            Ask questions about your construction PDFs and get instant answers, instead of digging through messy, hard-to-search documents.
          </p>
        </div>

        {/* Demo Interface */}
        <div className="max-w-6xl mx-auto">
          <div className="grid md:grid-cols-2 gap-8 items-start">
            {/* Chat Interface */}
            <div className="bg-card border border-border rounded-lg p-6 h-[500px] flex flex-col">
              {/* Messages Area */}
              <div className="flex-1 space-y-6">
                {/* Existing Message */}
                <div>
                  <div className="bg-primary text-primary-foreground p-3 rounded-lg inline-block max-w-sm">
                    What are the requirements for smaller construction renovation projects?
                  </div>
                </div>

                {/* Response */}
                <div>
                  <div className="flex items-start space-x-3">
                    <div className="w-8 h-8 bg-primary rounded-full flex items-center justify-center flex-shrink-0">
                      <MessageSquare className="w-4 h-4 text-primary-foreground" />
                    </div>
                    <div className="bg-secondary p-4 rounded-lg max-w-md">
                      <p className="text-sm text-secondary-foreground">
                        Smaller renovation projects are defined as projects up to $5 million in total costs.
                      </p>
                    </div>
                  </div>
                </div>

                {/* New Q&A if query was submitted */}
                {(isLoading || showResponse) && (
                  <>
                    <div>
                      <div className="bg-primary text-primary-foreground p-3 rounded-lg inline-block max-w-sm">
                        What are the key requirements for concrete curing?
                      </div>
                    </div>

                    {/* Typing indicator */}
                    {showTyping && (
                      <div>
                        <div className="flex items-start space-x-3">
                          <div className="w-8 h-8 bg-primary rounded-full flex items-center justify-center flex-shrink-0">
                            <MessageSquare className="w-4 h-4 text-primary-foreground" />
                          </div>
                          <div className="bg-secondary p-4 rounded-lg max-w-md">
                            <div className="flex space-x-1">
                              <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce"></div>
                              <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                              <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                            </div>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* AI Response */}
                    {showResponse && (
                      <div>
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
                  </>
                )}
              </div>

              {/* Input Area */}
              <div className="relative mt-6 opacity-100">
                <Input
                  value={hasAsked ? "" : query}
                  readOnly
                  disabled={hasAsked}
                  onKeyPress={handleKeyPress}
                  placeholder={hasAsked ? "Ask anything about the project..." : "Ask anything"}
                  className={`bg-input border-border text-muted-foreground placeholder-muted-foreground pr-32 ${hasAsked ? 'opacity-60 cursor-not-allowed' : 'cursor-pointer'}`}
                />
                <div className="absolute right-0.5 top-1/2 transform -translate-y-1/2">
                  <Button
                    onClick={handleQuerySubmit}
                    size="sm"
                    variant="ghost"
                    disabled={isLoading || hasAsked}
                    aria-disabled={isLoading || hasAsked}
                    className={`group relative flex items-center justify-center px-3 py-2 rounded-lg transition-all duration-200 ${!showResponse && !isLoading && !hasAsked
                      ? 'border border-primary/20 bg-primary/5 hover:bg-primary/10 hover:border-primary/40 animate-pulse cursor-pointer'
                      : 'border border-transparent'} ${hasAsked ? 'opacity-60 cursor-not-allowed' : ''}`}
                  >
                    <div className="flex items-center justify-between space-x-2 w-full">
                      {!showResponse && !isLoading && !hasAsked && (
                        <span className="text-xs font-bold text-white whitespace-nowrap">Click to ask</span>
                      )}
                      <div className={`w-6 h-6 rounded-full flex items-center justify-center transition-colors ${!showResponse && !isLoading && !hasAsked
                        ? 'bg-primary/10 group-hover:bg-primary/20'
                        : 'bg-transparent'}`}>
                        <ArrowUp className="w-3 h-3 text-white" />
                      </div>
                    </div>
                  </Button>
                </div>
              </div>
            </div>

            {/* PDF Viewer */}
            <div className="bg-card border border-border rounded-lg overflow-hidden h-[500px] flex flex-col">
              {/* PDF Header */}
              <div className="bg-secondary p-2 flex items-center justify-between border-b border-border">
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-medium text-secondary-foreground">
                    {showResponse ? "meridian-heights-concrete.pdf" : "meridian-heights-overall-description.pdf"}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    Page {showResponse ? "89 of 156" : "137 of 241"}
                  </span>
                </div>
                <div className="flex items-center space-x-2">
                  <Button variant="ghost" size="sm">
                    <Info className="w-4 h-4" />
                  </Button>
                  <Button variant="ghost" size="sm">
                    <Search className="w-4 h-4" />
                  </Button>
                  <Button variant="ghost" size="sm">
                    <Download className="w-4 h-4" />
                  </Button>
                </div>
              </div>

              {/* PDF Content */}
              <div className="p-6 bg-card text-muted-foreground flex-1 relative overflow-hidden">
                {pdfLoading && (
                  <div className="absolute inset-0 bg-card/90 flex items-center justify-center z-10">
                    <div className="flex flex-col items-center space-y-3">
                      <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
                      <span className="text-sm text-muted-foreground">Loading document...</span>
                    </div>
                  </div>
                )}
                {!showResponse ? (
                  // Initial PDF Content - Overall Description
                  <>
                    <div className="mb-4">
                      <h2 className="text-lg font-bold text-primary mb-4">MERIDIAN HEIGHTS</h2>
                      <span className="text-xs text-muted-foreground mb-2 block">Mixed-Use Development Project</span>
                    </div>

                    <div className="space-y-4">
                      <div>
                        <h3 className="text-sm font-semibold mb-2 flex items-center">
                          <span className="bg-muted rounded-full w-5 h-5 flex items-center justify-center text-xs mr-2">8</span>
                          Project Classification & Budget Requirements
                        </h3>
                      </div>

                      <div className="text-sm leading-relaxed space-y-3">
                        <p>
                          The Meridian Heights development represents a comprehensive mixed-use project incorporating
                          residential towers, commercial spaces, and underground parking facilities.
                          <mark className="bg-primary/30 text-primary-foreground px-1 py-0.5 rounded">
                            Smaller renovation projects are defined as projects up to $5 million in total costs
                          </mark>
                          , while major developments like Meridian Heights exceed $150 million in total project value.
                        </p>

                        <p>
                          Phase 1 construction includes the 32-story residential tower with 280 units,
                          ground-level retail spaces, and a 4-level underground parking structure.
                          The project requires specialized construction techniques due to the proximity
                          to existing infrastructure and the challenging urban site conditions.
                        </p>

                        <p>
                          All construction activities must comply with municipal building codes,
                          environmental regulations, and the established project timeline spanning
                          36 months from groundbreaking to occupancy permits.
                        </p>
                      </div>
                    </div>
                  </>
                ) : (
                  // New PDF Content - Concrete Specifications
                  <>
                    <div className="mb-4">
                      <h2 className="text-lg font-bold text-primary mb-4">MERIDIAN HEIGHTS</h2>
                      <span className="text-xs text-muted-foreground mb-2 block">Concrete & Materials Specifications</span>
                    </div>

                    <div className="space-y-4">
                      <div>
                        <h3 className="text-sm font-semibold mb-2 flex items-center">
                          <span className="bg-muted rounded-full w-5 h-5 flex items-center justify-center text-xs mr-2">3</span>
                          Concrete Curing & Quality Standards
                        </h3>
                      </div>

                      <div className="text-sm leading-relaxed space-y-3">
                        <p>
                          All structural concrete for the Meridian Heights project must meet or exceed
                          4000 PSI compressive strength requirements.
                          <mark className="bg-primary/30 text-primary-foreground px-1 py-0.5 rounded">
                            Standard concrete curing time is 28 days for full strength development
                          </mark>
                          , with initial setting occurring within 24-48 hours depending on environmental conditions.
                        </p>

                        <p>
                          Temperature control during curing is critical, maintaining concrete between
                          50°F and 90°F throughout the initial 7-day period. Hot weather concreting
                          procedures must be implemented when ambient temperatures exceed 85°F,
                          including pre-cooling aggregates and limiting pour times to early morning hours.
                        </p>

                        <p>
                          Quality control testing includes slump tests every 100 cubic yards,
                          compression testing at 7, 14, and 28 days, and continuous monitoring
                          of aggregate moisture content and cement-to-water ratios throughout
                          the pouring process.
                        </p>
                      </div>
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* CTA Button */}
          <div className="flex justify-center mt-12">
            <Link href="/projects/lindevangskolen-ccs-anlgsprojekt-181d6cd9-b815-4347-bc0b-1df8dca67519/query?q=Hvad%20er%20kravene%20til%20radiatorerne%3F">
              <Button className="px-8 py-3 text-lg bg-primary hover:bg-primary/90 text-primary-foreground shadow-lg hover:shadow-xl transform hover:scale-105 transition-all duration-200 border border-primary/20" style={{ animation: 'scale-pulse 2s ease-in-out infinite' }}>
                Try search on a real project - no user needed!
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* Bottom Section */}
      <div className="container mx-auto px-6 py-20">
        <div className="text-center mb-16">
          <h2 className="text-5xl font-bold mb-4">
            From <span className="text-foreground">Piles of PDFs</span><br />
            <span className="text-primary">To instant answers</span>
          </h2>
        </div>

        <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
          {/* Step 1 */}
          <div className="text-center">
            <div className="bg-card border border-border rounded-lg px-8 py-6 mb-6">
              <div className="w-10 h-8 bg-primary rounded flex items-center justify-center mx-auto mb-4 text-lg font-bold text-primary-foreground">
                1
              </div>
              <h3 className="text-xl font-semibold mb-4 text-card-foreground">Upload or sync your documents</h3>
              
              <DragDropVisual />

              <p className="text-muted-foreground text-sm">
                Upload your pdfs or sync your project folder. We process PDFs and spreadsheets to build a complete picture.
              </p>
            </div>
          </div>

          {/* Step 2 */}
          <HowItWorksCard
            step={2}
            title="Crunch & Enhance"
            description="Our AI extracts key data from your construction project folders, automating what you usually are spending hours to gather"
          >
            <ProcessingDiagram />
          </HowItWorksCard>

          {/* Step 3 */}
          <div className="text-center">
            <div className="bg-card border border-border rounded-lg px-8 py-6 mb-6">
              <div className="w-10 h-8 bg-primary rounded flex items-center justify-center mx-auto mb-4 text-lg font-bold text-primary-foreground">
                3
              </div>
              <h3 className="text-xl font-semibold mb-4 text-card-foreground">Ask critical questions</h3>
              <div className="bg-secondary border border-border rounded-lg p-4 mb-6 space-y-2">
                {/* Chat-like interface */}
                <div className="flex justify-start">
                  <div className="bg-primary text-primary-foreground p-2 rounded-lg text-xs max-w-md inline-block text-left">
                    What are the longest lead time items?
                  </div>
                </div>
                <div className="flex items-start space-x-2">
                  <div className="w-6 h-6 bg-primary rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                    <MessageSquare className="w-3 h-3 text-primary-foreground" />
                  </div>
                  <div className="bg-card border border-border p-2 rounded-lg text-xs text-card-foreground max-w-md text-left">
                    Custom steel trusses (TR-1) require a 16 week lead time. [procurement.xlsx]
                  </div>
                </div>
                <div className="flex justify-start">
                  <div className="bg-primary text-primary-foreground p-2 rounded-lg text-xs max-w-md inline-block text-left">
                    Any conflicts between electrical and HVAC plans?
                  </div>
                </div>
                <div className="flex items-start space-x-2">
                  <div className="w-6 h-6 bg-primary rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                    <MessageSquare className="w-3 h-3 text-primary-foreground" />
                  </div>
                  <div className="bg-card border border-border p-2 rounded-lg text-xs text-card-foreground max-w-md text-left">
                    Yes, a duct clashes with a cable tray on Floor 5. [coordination.pdf, p.9]<br /> <br /> You really don't bother searching through pdfs anymore, do you?
                  </div>
                </div>
              </div>
              <p className="text-muted-foreground text-sm">
                Query document and get immediate, accurate answers with source citations.
              </p>
            </div>
          </div>
        </div>
        
        {/* CTA Button */}
        <div className="flex justify-center mt-12">
          <Link href="/upload">
            <Button className="px-8 py-3 text-lg bg-primary hover:bg-primary/90 text-primary-foreground shadow-lg hover:shadow-xl transform hover:scale-105 transition-all duration-200 border border-primary/20" style={{ animation: 'scale-pulse 2s ease-in-out infinite' }}>
              Upload your own project and try it - no user needed!
            </Button>
          </Link>
        </div>
      </div>

      {/* Video Demo Section */}
      <div className="container mx-auto px-6 py-16">
        <div className="text-center mb-12">
          <h2 className="text-4xl font-bold mb-4">
            How it works in 20 seconds
          </h2>
        </div>
        
        <div className="max-w-4xl mx-auto">
          <div className="relative rounded-lg shadow-xl border border-border overflow-hidden bg-black">
            {/* Custom poster overlay */}
            {!videoPlaying && (
              <div 
                className="absolute inset-0 z-10 cursor-pointer group"
                onClick={() => {
                  setVideoPlaying(true);
                  videoRef.current?.play();
                }}
              >
                <Image
                  src="/video-poster.jpg"
                  alt="Video preview"
                  fill
                  className="object-cover"
                  priority
                />
                <div className="absolute inset-0 bg-black/30 flex items-center justify-center group-hover:bg-black/40 transition-colors">
                  <div className="w-20 h-20 bg-white/90 rounded-full flex items-center justify-center group-hover:scale-110 transition-transform">
                    <Play className="w-10 h-10 text-black ml-1" fill="currentColor" />
                  </div>
                </div>
              </div>
            )}
            
            <video 
              ref={videoRef}
              className="w-full aspect-video"
              controls={videoPlaying}
              poster="/video-poster.jpg"
              preload="metadata"
              muted
              onPlay={() => setVideoPlaying(true)}
              onPause={() => setVideoPlaying(false)}
              onEnded={() => setVideoPlaying(false)}
            >
              <source src="/demo-video.mp4" type="video/mp4" />
              Your browser does not support the video tag.
            </video>
          </div>
        </div>
      </div>

    </div>
  );
}