import { Loader2 } from 'lucide-react';

export default function AnalyzeLoading() {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <Loader2 className="h-16 w-16 text-blue-500 animate-spin mx-auto mb-4" />
        <p className="text-zinc-600 dark:text-zinc-400 text-lg">Loading analysis tools...</p>
      </div>
    </div>
  );
}
