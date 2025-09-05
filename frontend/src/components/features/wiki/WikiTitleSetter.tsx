'use client';

import { useEffect } from 'react';
import { useWikiTitle } from '@/components/providers/WikiTitleProvider';

interface WikiTitleSetterProps {
  title: string | null;
}

export default function WikiTitleSetter({ title }: WikiTitleSetterProps) {
  const { setWikiTitle } = useWikiTitle();

  useEffect(() => {
    setWikiTitle(title);
    
    // Clean up on unmount
    return () => setWikiTitle(null);
  }, [title, setWikiTitle]);

  return null; // This component doesn't render anything
}