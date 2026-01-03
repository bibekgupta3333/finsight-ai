'use client';

import { Button } from '@/components/ui/button';
import { BarChart3, Home, Shield, Upload } from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

export function Navigation() {
  const pathname = usePathname();

  const isActive = (path: string) => pathname === path;

  return (
    <nav className="border-b bg-white dark:bg-zinc-950">
      <div className="container mx-auto px-4">
        <div className="flex h-16 items-center justify-between">
          <div className="flex items-center gap-2">
            <Shield className="h-6 w-6 text-blue-600" />
            <Link href="/" className="text-xl font-bold">
              FinSight AI
            </Link>
          </div>

          <div className="flex items-center gap-2">
            <Button
              asChild
              variant={isActive('/') ? 'default' : 'ghost'}
              size="sm"
            >
              <Link href="/">
                <Home className="h-4 w-4 mr-2" />
                Home
              </Link>
            </Button>
            <Button
              asChild
              variant={isActive('/analyze') ? 'default' : 'ghost'}
              size="sm"
            >
              <Link href="/analyze">
                <Upload className="h-4 w-4 mr-2" />
                Analyze
              </Link>
            </Button>
            <Button
              asChild
              variant={isActive('/dashboard') ? 'default' : 'ghost'}
              size="sm"
            >
              <Link href="/dashboard">
                <BarChart3 className="h-4 w-4 mr-2" />
                Dashboard
              </Link>
            </Button>
          </div>
        </div>
      </div>
    </nav>
  );
}
