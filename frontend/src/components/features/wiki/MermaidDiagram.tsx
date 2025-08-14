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
        containerRef.current.innerHTML = svg;
        
      } catch (error) {
        console.error('Mermaid rendering error:', error);
        // Fallback to code block if rendering fails
        containerRef.current.innerHTML = `
          <pre class="bg-card border border-border rounded-lg p-4 overflow-x-auto text-sm">
            <code>${children}</code>
          </pre>
        `;
      }
    };

    renderDiagram();
  }, [children]);

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