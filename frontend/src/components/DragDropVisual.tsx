import { ArrowUp } from "lucide-react";

export function DragDropVisual() {
  return (
    <div className="relative h-32 mb-6 border-2 border-dashed border-border rounded-lg bg-card/50 overflow-hidden">
      {/* Background document icons */}
      <div className="absolute inset-0 flex items-center justify-center opacity-20">
        <div className="relative w-full h-full flex items-center justify-center">
          {/* Top row documents */}
          {/* Excel file - green */}
          <div className="absolute left-8 top-4 transform -rotate-15">
            <svg width="28" height="32" viewBox="0 0 24 28" fill="none" className="text-green-600">
              <path d="M14 2L20 8V26H4V2H14Z" stroke="currentColor" strokeWidth="2" fill="currentColor" fillOpacity="0.4"/>
              <path d="M14 2V8H20" stroke="currentColor" strokeWidth="2" fill="none"/>
              <rect x="7" y="12" width="10" height="1" fill="currentColor"/>
              <rect x="7" y="14" width="10" height="1" fill="currentColor"/>
              <rect x="7" y="16" width="10" height="1" fill="currentColor"/>
              <rect x="7" y="18" width="10" height="1" fill="currentColor"/>
              <path d="M11 12V19M15 12V19" stroke="currentColor" strokeWidth="0.5"/>
            </svg>
          </div>
          
          {/* Photo/Image - pink */}
          <div className="absolute right-8 top-4 transform rotate-12">
            <svg width="28" height="32" viewBox="0 0 24 28" fill="none" className="text-pink-500">
              <path d="M14 2L20 8V26H4V2H14Z" stroke="currentColor" strokeWidth="2" fill="currentColor" fillOpacity="0.3"/>
              <path d="M14 2V8H20" stroke="currentColor" strokeWidth="2" fill="none"/>
              <rect x="7" y="12" width="10" height="8" stroke="currentColor" strokeWidth="1" fill="none"/>
              <circle cx="9.5" cy="15" r="1" fill="currentColor"/>
              <path d="M7 18L9 16L12 17L17 13V20H7V18Z" fill="currentColor" fillOpacity="0.5"/>
            </svg>
          </div>
          
          {/* Left side documents */}
          {/* PDF document - blue */}
          <div className="absolute left-4 top-12 transform -rotate-8">
            <svg width="32" height="38" viewBox="0 0 24 28" fill="none" className="text-blue-400">
              <path d="M14 2L20 8V26H4V2H14Z" stroke="currentColor" strokeWidth="2" fill="currentColor" fillOpacity="0.3"/>
              <path d="M14 2V8H20" stroke="currentColor" strokeWidth="2" fill="none"/>
              <path d="M8 12H16M8 16H12" stroke="currentColor" strokeWidth="1.5"/>
            </svg>
          </div>
          
          {/* CAD file - purple */}
          <div className="absolute left-6 bottom-8 transform rotate-10">
            <svg width="28" height="32" viewBox="0 0 24 28" fill="none" className="text-purple-500">
              <path d="M14 2L20 8V26H4V2H14Z" stroke="currentColor" strokeWidth="2" fill="currentColor" fillOpacity="0.3"/>
              <path d="M14 2V8H20" stroke="currentColor" strokeWidth="2" fill="none"/>
              <rect x="8" y="12" width="8" height="6" stroke="currentColor" strokeWidth="1" fill="none"/>
              <path d="M10 14L14 16L10 18" stroke="currentColor" strokeWidth="1" fill="none"/>
            </svg>
          </div>
          
          {/* Right side documents */}
          {/* Center-right document - gray */}
          <div className="absolute right-4 top-12 transform -rotate-6">
            <svg width="32" height="38" viewBox="0 0 24 28" fill="none" className="text-gray-400">
              <path d="M14 2L20 8V26H4V2H14Z" stroke="currentColor" strokeWidth="2" fill="currentColor" fillOpacity="0.3"/>
              <path d="M14 2V8H20" stroke="currentColor" strokeWidth="2" fill="none"/>
              <path d="M8 12H16M8 16H14M8 20H12" stroke="currentColor" strokeWidth="1.5"/>
            </svg>
          </div>
          
          {/* CAD drawing - blue */}
          <div className="absolute right-6 bottom-8 transform -rotate-12">
            <svg width="28" height="32" viewBox="0 0 24 28" fill="none" className="text-blue-600">
              <path d="M14 2L20 8V26H4V2H14Z" stroke="currentColor" strokeWidth="2" fill="currentColor" fillOpacity="0.3"/>
              <path d="M14 2V8H20" stroke="currentColor" strokeWidth="2" fill="none"/>
              <circle cx="12" cy="15" r="2" stroke="currentColor" strokeWidth="1" fill="none"/>
              <path d="M8 15H10M14 15H16M12 13V11M12 17V19" stroke="currentColor" strokeWidth="1"/>
            </svg>
          </div>
          
          {/* Bottom row documents */}
          {/* Image file - orange */}
          <div className="absolute left-8 bottom-4 transform -rotate-3">
            <svg width="30" height="34" viewBox="0 0 24 28" fill="none" className="text-orange-500">
              <path d="M14 2L20 8V26H4V2H14Z" stroke="currentColor" strokeWidth="2" fill="currentColor" fillOpacity="0.3"/>
              <path d="M14 2V8H20" stroke="currentColor" strokeWidth="2" fill="none"/>
              <rect x="7" y="12" width="10" height="8" stroke="currentColor" strokeWidth="1" fill="none"/>
              <circle cx="9" cy="15" r="1" fill="currentColor"/>
              <path d="M7 18L10 16L13 17L17 14V20H7V18Z" fill="currentColor" fillOpacity="0.6"/>
            </svg>
          </div>
          
          {/* Document - red */}
          <div className="absolute right-8 bottom-4 transform rotate-14">
            <svg width="32" height="38" viewBox="0 0 24 28" fill="none" className="text-red-400">
              <path d="M14 2L20 8V26H4V2H14Z" stroke="currentColor" strokeWidth="2" fill="currentColor" fillOpacity="0.3"/>
              <path d="M14 2V8H20" stroke="currentColor" strokeWidth="2" fill="none"/>
              <circle cx="12" cy="16" r="3" stroke="currentColor" strokeWidth="1.5" fill="none"/>
            </svg>
          </div>
          
          {/* Center area documents */}
          {/* Center-left document - green */}
          <div className="absolute left-16 top-8 transform rotate-4">
            <svg width="32" height="38" viewBox="0 0 24 28" fill="none" className="text-green-500">
              <path d="M14 2L20 8V26H4V2H14Z" stroke="currentColor" strokeWidth="2" fill="currentColor" fillOpacity="0.4"/>
              <path d="M14 2V8H20" stroke="currentColor" strokeWidth="2" fill="none"/>
              <rect x="8" y="12" width="8" height="1.5" fill="currentColor"/>
              <rect x="8" y="15" width="6" height="1.5" fill="currentColor"/>
              <rect x="8" y="18" width="8" height="1.5" fill="currentColor"/>
            </svg>
          </div>
          
          {/* Spreadsheet - teal */}
          <div className="absolute right-16 bottom-8 transform rotate-8">
            <svg width="30" height="34" viewBox="0 0 24 28" fill="none" className="text-teal-500">
              <path d="M14 2L20 8V26H4V2H14Z" stroke="currentColor" strokeWidth="2" fill="currentColor" fillOpacity="0.4"/>
              <path d="M14 2V8H20" stroke="currentColor" strokeWidth="2" fill="none"/>
              <rect x="7" y="12" width="10" height="8" stroke="currentColor" strokeWidth="1" fill="none"/>
              <path d="M7 14H17M7 16H17M7 18H17" stroke="currentColor" strokeWidth="0.5"/>
              <path d="M9 12V20M11 12V20M13 12V20M15 12V20" stroke="currentColor" strokeWidth="0.5"/>
            </svg>
          </div>
        </div>
      </div>
      
      {/* Central upload icon */}
      <div className="relative z-10 flex flex-col items-center justify-center h-full">
        <div className="bg-background/90 backdrop-blur-sm rounded-full p-3 border border-border/50">
          <ArrowUp className="h-5 w-5 text-foreground" />
        </div>
      </div>
    </div>
  );
}