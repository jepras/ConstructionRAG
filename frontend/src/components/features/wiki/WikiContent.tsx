'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import { WikiPageContent } from '@/lib/api-client';
import MermaidDiagram from './MermaidDiagram';

interface WikiContentProps {
  content: WikiPageContent;
}

// Custom components for markdown rendering
const components = {
  // Headings with consistent styling
  h1: ({ children, ...props }: any) => (
    <h1 className="text-3xl font-bold text-foreground mt-8 mb-4 first:mt-0" {...props}>
      {children}
    </h1>
  ),
  h2: ({ children, ...props }: any) => (
    <h2 className="text-2xl font-semibold text-foreground mt-6 mb-3 border-b border-border pb-2" {...props}>
      {children}
    </h2>
  ),
  h3: ({ children, ...props }: any) => (
    <h3 className="text-xl font-semibold text-foreground mt-5 mb-2" {...props}>
      {children}
    </h3>
  ),
  h4: ({ children, ...props }: any) => (
    <h4 className="text-lg font-medium text-foreground mt-4 mb-2" {...props}>
      {children}
    </h4>
  ),
  h5: ({ children, ...props }: any) => (
    <h5 className="text-base font-medium text-foreground mt-3 mb-2" {...props}>
      {children}
    </h5>
  ),
  h6: ({ children, ...props }: any) => (
    <h6 className="text-sm font-medium text-foreground mt-3 mb-2" {...props}>
      {children}
    </h6>
  ),

  // Paragraphs
  p: ({ children, ...props }: any) => (
    <p className="text-foreground leading-7 mb-4" {...props}>
      {children}
    </p>
  ),

  // Lists
  ul: ({ children, ...props }: any) => (
    <ul className="list-disc pl-6 mb-4 space-y-1 text-foreground" {...props}>
      {children}
    </ul>
  ),
  ol: ({ children, ...props }: any) => (
    <ol className="list-decimal pl-6 mb-4 space-y-1 text-foreground" {...props}>
      {children}
    </ol>
  ),
  li: ({ children, ...props }: any) => (
    <li className="leading-6" {...props}>
      {children}
    </li>
  ),

  // Code blocks and inline code
  code: ({ className, children, ...props }: any) => {
    const match = /language-(\w+)/.exec(className || '');
    const language = match ? match[1] : '';

    // Handle mermaid diagrams
    if (language === 'mermaid') {
      return <MermaidDiagram>{children as string}</MermaidDiagram>;
    }

    // Regular code blocks
    if (className) {
      return (
        <pre className="bg-card border border-border rounded-lg p-4 overflow-x-auto my-4">
          <code className="text-sm text-foreground font-mono" {...props}>
            {children}
          </code>
        </pre>
      );
    }

    // Inline code
    return (
      <code className="bg-card text-primary px-1.5 py-0.5 rounded text-sm font-mono" {...props}>
        {children}
      </code>
    );
  },

  // Tables
  table: ({ children, ...props }: any) => (
    <div className="my-6 overflow-x-auto">
      <table className="w-full border-collapse border border-border" {...props}>
        {children}
      </table>
    </div>
  ),
  thead: ({ children, ...props }: any) => (
    <thead className="bg-card" {...props}>
      {children}
    </thead>
  ),
  tbody: ({ children, ...props }: any) => (
    <tbody {...props}>
      {children}
    </tbody>
  ),
  tr: ({ children, ...props }: any) => (
    <tr className="border-b border-border" {...props}>
      {children}
    </tr>
  ),
  th: ({ children, ...props }: any) => (
    <th className="border border-border px-4 py-2 text-left font-semibold text-foreground" {...props}>
      {children}
    </th>
  ),
  td: ({ children, ...props }: any) => (
    <td className="border border-border px-4 py-2 text-foreground" {...props}>
      {children}
    </td>
  ),

  // Links
  a: ({ href, children, ...props }: any) => (
    <a 
      href={href} 
      className="text-primary hover:text-primary/80 underline underline-offset-4" 
      target={href?.startsWith('http') ? '_blank' : undefined}
      rel={href?.startsWith('http') ? 'noopener noreferrer' : undefined}
      {...props}
    >
      {children}
    </a>
  ),

  // Blockquotes
  blockquote: ({ children, ...props }: any) => (
    <blockquote className="border-l-4 border-primary pl-4 py-2 my-4 bg-card/50 italic text-muted-foreground" {...props}>
      {children}
    </blockquote>
  ),

  // Horizontal rules
  hr: (props: any) => (
    <hr className="my-8 border-t border-border" {...props} />
  ),

  // Images
  img: ({ src, alt, ...props }: any) => (
    <img 
      src={src} 
      alt={alt} 
      className="max-w-full h-auto rounded-lg border border-border my-4" 
      {...props} 
    />
  ),
};

export default function WikiContent({ content }: WikiContentProps) {
  return (
    <div className="max-w-none">
      {/* Page header */}
      <div className="mb-8 pb-4 border-b border-border">
        <h1 className="text-3xl font-bold text-foreground mb-2">
          {content.title}
        </h1>
        {content.metadata && (
          <div className="text-sm text-muted-foreground">
            {content.metadata.word_count} words
            {content.metadata.last_updated && (
              <> • Updated {new Date(content.metadata.last_updated).toLocaleDateString()}</>
            )}
          </div>
        )}
      </div>

      {/* Markdown content */}
      <div className="prose prose-lg max-w-none">
        <ReactMarkdown
          components={components}
          remarkPlugins={[remarkGfm]}
          rehypePlugins={[rehypeRaw]}
        >
          {content.content}
        </ReactMarkdown>
      </div>
    </div>
  );
}