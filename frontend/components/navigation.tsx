'use client';

import { Button } from '@/components/ui/button';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu';
import { ThemeToggle } from '@/components/ui/theme-toggle';
import { BarChart3, Brain, Home, Layers, Menu, Shield, Upload, FileText, Info, ChevronDown, Activity, Sliders, Cpu, GitBranch } from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';

export function Navigation() {
  const pathname = usePathname();
  const [isOpen, setIsOpen] = useState(false);

  const isActive = (path: string) => pathname === path;

  const navItems = [
    { href: '/', label: 'Home', icon: Home },
    { href: '/analyze', label: 'Analyze', icon: Upload },
    { href: '/batch', label: 'Batch', icon: Layers },
    { href: '/agents', label: 'Agents', icon: Brain },
    { href: '/about', label: 'About', icon: Info },
    { href: '/whitepaper', label: 'Whitepaper', icon: FileText },
  ];

  const dashboardItems = [
    { href: '/dashboard/fraud-detection', label: 'Fraud Detection', icon: Activity, description: 'Multi-agent fraud analysis' },
    { href: '/dashboard/sampling', label: 'Sampling Optimizer', icon: Sliders, description: 'Parameter tuning & schedules' },
    { href: '/dashboard/moe-explorer', label: 'MoE Cost Explorer', icon: Cpu, description: 'Mixture-of-Experts analysis' },
    { href: '/dashboard/distillation', label: 'Distillation Decision', icon: GitBranch, description: 'Model distillation framework' },
  ];

  const isDashboardActive = dashboardItems.some(item => pathname === item.href);

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

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-2">
            {navItems.map((item) => (
              <Button
                key={item.href}
                asChild
                variant={isActive(item.href) ? 'default' : 'ghost'}
                size="sm"
              >
                <Link href={item.href}>
                  <item.icon className="h-4 w-4 mr-2" />
                  {item.label}
                </Link>
              </Button>
            ))}

            {/* Dashboards Dropdown */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant={isDashboardActive ? 'default' : 'ghost'} size="sm">
                  <BarChart3 className="h-4 w-4 mr-2" />
                  Dashboards
                  <ChevronDown className="h-3 w-3 ml-1" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-64">
                {dashboardItems.map((item, index) => (
                  <div key={item.href}>
                    <DropdownMenuItem asChild>
                      <Link href={item.href} className="cursor-pointer">
                        <item.icon className="h-4 w-4 mr-2" />
                        <div className="flex flex-col">
                          <span className="font-medium">{item.label}</span>
                          <span className="text-xs text-muted-foreground">{item.description}</span>
                        </div>
                      </Link>
                    </DropdownMenuItem>
                    {index < dashboardItems.length - 1 && <DropdownMenuSeparator />}
                  </div>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>

            <div className="ml-4 border-l pl-4">
              <ThemeToggle />
            </div>
          </div>

          {/* Mobile Navigation */}
          <div className="flex md:hidden items-center gap-2">
            <ThemeToggle />
            <Sheet open={isOpen} onOpenChange={setIsOpen}>
              <SheetTrigger asChild>
                <Button variant="ghost" size="sm">
                  <Menu className="h-5 w-5" />
                  <span className="sr-only">Toggle menu</span>
                </Button>
              </SheetTrigger>
              <SheetContent>
                <SheetHeader>
                  <SheetTitle className="flex items-center gap-2">
                    <Shield className="h-5 w-5 text-blue-600" />
                    FinSight AI
                  </SheetTitle>
                </SheetHeader>
                <div className="mt-8 flex flex-col gap-4">
                  {navItems.map((item) => (
                    <Button
                      key={item.href}
                      asChild
                      variant={isActive(item.href) ? 'default' : 'ghost'}
                      className="justify-start"
                      onClick={() => setIsOpen(false)}
                    >
                      <Link href={item.href}>
                        <item.icon className="h-4 w-4 mr-2" />
                        {item.label}
                      </Link>
                    </Button>
                  ))}

                  {/* Dashboards Section */}
                  <div className="border-t pt-4 mt-2">
                    <div className="flex items-center gap-2 px-3 py-2 text-sm font-semibold text-muted-foreground">
                      <BarChart3 className="h-4 w-4" />
                      Dashboards
                    </div>
                    {dashboardItems.map((item) => (
                      <Button
                        key={item.href}
                        asChild
                        variant={pathname === item.href ? 'default' : 'ghost'}
                        className="justify-start w-full"
                        onClick={() => setIsOpen(false)}
                      >
                        <Link href={item.href} className="flex flex-col items-start">
                          <div className="flex items-center">
                            <item.icon className="h-4 w-4 mr-2" />
                            {item.label}
                          </div>
                          <span className="text-xs text-muted-foreground ml-6">{item.description}</span>
                        </Link>
                      </Button>
                    ))}
                  </div>
                </div>
              </SheetContent>
            </Sheet>
          </div>
        </div>
      </div>
    </nav>
  );
}
