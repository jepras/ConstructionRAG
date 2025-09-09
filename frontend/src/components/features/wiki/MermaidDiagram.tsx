'use client';

import { useEffect, useRef } from 'react';

interface MermaidDiagramProps {
  children: string;
}

export default function MermaidDiagram({ children }: MermaidDiagramProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const renderDiagram = async () => {
      if (!containerRef.current) return;
      
      // Clear previous content
      containerRef.current.innerHTML = '';
      
      try {
        // Dynamic import for client-side only
        const mermaid = (await import('mermaid')).default;
        
        // Initialize mermaid if not already done
        mermaid.initialize({
          startOnLoad: false,
          theme: 'default',
          suppressErrorRendering: false, // Enable error display for debugging
          logLevel: 'debug', // Show all logs for debugging
          themeVariables: {
            primaryColor: '#f97316', // orange-500
            primaryTextColor: '#000000',
            primaryBorderColor: '#ea580c', // orange-600
            lineColor: '#6b7280', // gray-500
            secondaryColor: '#f3f4f6', // gray-100
            tertiaryColor: '#ffffff',
            background: '#ffffff',
            mainBkg: '#ffffff',
            secondBkg: '#f3f4f6',
            tertiaryBkg: '#ffffff',
          },
        });

        // Generate unique ID for this diagram
        const id = `mermaid-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        
        
        // Render the diagram
        const { svg } = await mermaid.render(id, children.trim());
        
        // Check if container still exists before setting innerHTML
        if (containerRef.current) {
          containerRef.current.innerHTML = svg;
        }
        
      } catch (error) {
        // Detailed error logging for debugging
        console.error('=== MERMAID ERROR ===');
        console.error('Error details:', error);
        console.error('Error message:', error.message);
        console.error('Failed content:', JSON.stringify(children.trim()));
        
        // Fallback to code block if rendering fails
        if (containerRef.current) {
          containerRef.current.innerHTML = `
            <div class="bg-red-50 border border-red-200 rounded-lg p-4 text-sm">
              <div class="font-semibold text-red-800 mb-2">Mermaid Parsing Error:</div>
              <div class="text-red-700 mb-3">${error.message || 'Unknown error'}</div>
              <pre class="bg-card border border-border rounded-lg p-4 overflow-x-auto text-sm">
                <code>${children}</code>
              </pre>
            </div>
          `;
        }
      }
      
      // Hide any mermaid error popups that might still appear
      const hideErrorPopups = () => {
        const errorElements = document.querySelectorAll('[class*="mermaid"], [id*="mermaid"]');
        errorElements.forEach(el => {
          const errorText = el.textContent || '';
          if (errorText.includes('Syntax error') || errorText.includes('mermaid version')) {
            (el as HTMLElement).style.display = 'none';
          }
        });
      };
      
      // Run cleanup with delays
      setTimeout(hideErrorPopups, 100);
      setTimeout(hideErrorPopups, 500);
    };

    renderDiagram();
  }, [children]);

  // Global error cleanup effect
  useEffect(() => {
    const hideGlobalMermaidErrors = () => {
      // Target specific mermaid error elements instead of scanning all elements
      const errorSelectors = [
        '[class*="mermaid"]',
        '[id*="mermaid"]',
        'div[style*="position: fixed"]',
        'div[style*="position: absolute"]'
      ];
      
      errorSelectors.forEach(selector => {
        const elements = document.querySelectorAll(selector);
        elements.forEach(el => {
          const text = el.textContent || '';
          const className = el.className || '';
          
          // Check if element contains mermaid error messages
          if (
            text.includes('Syntax error in text') ||
            text.includes('mermaid version') ||
            (typeof className === 'string' && className.includes('mermaid') && text.includes('Syntax error'))
          ) {
            (el as HTMLElement).style.display = 'none';
            (el as HTMLElement).style.visibility = 'hidden';
            (el as HTMLElement).style.opacity = '0';
            (el as HTMLElement).style.height = '0';
            (el as HTMLElement).style.overflow = 'hidden';
          }
        });
      });
    };

    // Run cleanup with delays to catch dynamically added elements
    const timeouts = [
      setTimeout(hideGlobalMermaidErrors, 100),
      setTimeout(hideGlobalMermaidErrors, 500),
      setTimeout(hideGlobalMermaidErrors, 1000)
    ];
    
    return () => {
      timeouts.forEach(timeout => clearTimeout(timeout));
    };
  }, []);

  return (
    <div className="my-6">
      <div 
        ref={containerRef}
        className="flex justify-center items-center bg-background border border-border rounded-lg p-4 overflow-x-auto"
      >
        {/* Loading state */}
        <div className="text-muted-foreground">Loading diagram...</div>
      </div>
    </div>
  );
}