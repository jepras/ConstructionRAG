'use client';

import React, { useState, KeyboardEvent } from 'react';
import { ArrowUp } from 'lucide-react';
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
          "pr-12 transition-all duration-200",
          isFocused && "ring-2 ring-primary ring-offset-2"
        )}
        style={{ paddingRight: '2.75rem' }}
      />
      <div className="absolute inset-y-0 right-0.5 flex items-center">
        <Button
          onClick={handleSubmit}
          size="sm"
          variant="ghost"
          disabled={disabled || !query.trim()}
          className={cn(
            "p-2 transition-all duration-300 rounded-md",
            query.trim() && !disabled
              ? "bg-orange-500 hover:bg-orange-600 text-white shadow-sm"
              : "bg-gray-100 hover:bg-gray-200 text-gray-400"
          )}
        >
          <ArrowUp className="w-4 h-4" />
        </Button>
      </div>
    </div>
  );
}