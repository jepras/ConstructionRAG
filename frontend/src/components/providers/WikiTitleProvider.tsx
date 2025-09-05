'use client';

import React, { createContext, useContext, useState, ReactNode } from 'react';

interface WikiTitleContextType {
  wikiTitle: string | null;
  setWikiTitle: (title: string | null) => void;
}

const WikiTitleContext = createContext<WikiTitleContextType | undefined>(undefined);

interface WikiTitleProviderProps {
  children: ReactNode;
}

export function WikiTitleProvider({ children }: WikiTitleProviderProps) {
  const [wikiTitle, setWikiTitle] = useState<string | null>(null);

  return (
    <WikiTitleContext.Provider value={{ wikiTitle, setWikiTitle }}>
      {children}
    </WikiTitleContext.Provider>
  );
}

export function useWikiTitle() {
  const context = useContext(WikiTitleContext);
  if (context === undefined) {
    throw new Error('useWikiTitle must be used within a WikiTitleProvider');
  }
  return context;
}