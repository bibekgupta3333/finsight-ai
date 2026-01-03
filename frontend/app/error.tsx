'use client';

import { Button } from '@/components/ui/button';
import { AlertCircle } from 'lucide-react';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="text-center max-w-md">
        <AlertCircle className="h-24 w-24 text-red-500 mx-auto mb-6" />
        <h1 className="text-4xl font-bold text-zinc-900 dark:text-zinc-100 mb-4">
          Something went wrong
        </h1>
        <p className="text-zinc-600 dark:text-zinc-400 mb-8">
          {error.message || 'An unexpected error occurred'}
        </p>
        <Button onClick={reset} size="lg">
          Try Again
        </Button>
      </div>
    </div>
  );
}
