'use client';

import React, { useState, KeyboardEvent } from 'react';
import { Mic, ArrowUp } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface QueryInputProps {
  onSubmit: (query: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export default function QueryInput({ onSubmit, disabled, placeholder = "Ask anything..." }: QueryInputProps) {
  const [query, setQuery] = useState('');
  const [isFocused, setIsFocused] = useState(false);

  const handleSubmit = () => {
    if (query.trim() && !disabled) {
      onSubmit(query);
      setQuery('');
    }
  };

  const handleKeyPress = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="relative">
      <Input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyPress={handleKeyPress}
        onFocus={() => setIsFocused(true)}
        onBlur={() => setIsFocused(false)}
        placeholder={placeholder}
        disabled={disabled}
        className={cn(
          "pr-24 transition-all duration-200",
          isFocused && "ring-2 ring-primary ring-offset-2"
        )}
      />
      <div className="absolute right-2 top-1/2 transform -translate-y-1/2 flex space-x-1">
        <Button 
          size="sm" 
          variant="ghost" 
          className="p-2"
          disabled={disabled}
          onClick={() => {
            // TODO: Implement voice input
            console.log('Voice input not yet implemented');
          }}
        >
          <Mic className="w-4 h-4" />
        </Button>
        <Button
          onClick={handleSubmit}
          size="sm"
          variant="ghost"
          disabled={disabled || !query.trim()}
          className={cn(
            "p-2 transition-all duration-300",
            query.trim() && !disabled
              ? "bg-primary hover:bg-primary/90 text-primary-foreground"
              : ""
          )}
        >
          <ArrowUp className="w-4 h-4" />
        </Button>
      </div>
    </div>
  );
}