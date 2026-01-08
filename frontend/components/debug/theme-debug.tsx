'use client';

import { useTheme } from 'next-themes';
import { useEffect, useState } from 'react';

export function ThemeDebug() {
  const { theme, systemTheme, resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return null;
  }

  return (
    <div className="fixed bottom-4 right-4 bg-background border border-border rounded-lg p-4 shadow-lg text-xs z-50">
      <div className="font-bold mb-2">Theme Debug Info:</div>
      <div>Current theme: {theme}</div>
      <div>System theme: {systemTheme}</div>
      <div>Resolved theme: {resolvedTheme}</div>
      <div className="mt-2">
        <div>localStorage: {typeof window !== 'undefined' ? localStorage.getItem('finsight-theme') : 'N/A'}</div>
      </div>
      <div className="mt-2">
        <div>HTML class: {typeof document !== 'undefined' ? document.documentElement.className : 'N/A'}</div>
      </div>
    </div>
  );
}
