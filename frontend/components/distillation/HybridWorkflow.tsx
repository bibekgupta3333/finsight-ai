'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Workflow, ArrowRight } from 'lucide-react';

export function HybridWorkflow() {
  const steps = [
    {
      id: 1,
      title: 'Classify Task',
      description: 'Route to small or large model',
      icon: '🎯',
    },
    {
      id: 2,
      title: 'Small Model Attempt',
      description: 'Try distilled model first',
      icon: '⚡',
    },
    {
      id: 3,
      title: 'Confidence Check',
      description: 'Evaluate prediction confidence',
      icon: '📊',
    },
    {
      id: 4,
      title: 'Escalate if Needed',
      description: 'Route low-confidence to large model',
      icon: '🚀',
    },
    {
      id: 5,
      title: 'Large Model Processing',
      description: 'Handle complex cases',
      icon: '🧠',
    },
    {
      id: 6,
      title: 'Return Result',
      description: 'Deliver final prediction',
      icon: '✅',
    },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Workflow className="h-5 w-5" />
          Hybrid Workflow
        </CardTitle>
        <CardDescription>
          6-step process for intelligent model routing
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {steps.map((step, idx) => (
            <div key={step.id}>
              <div className="flex items-start gap-3 p-3 rounded-lg border bg-gradient-to-r from-purple-50 to-blue-50 dark:from-purple-950/20 dark:to-blue-950/20">
                <div className="text-2xl">{step.icon}</div>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary" className="text-xs">Step {step.id}</Badge>
                    <h4 className="text-sm font-semibold">{step.title}</h4>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">{step.description}</p>
                </div>
              </div>

              {idx < steps.length - 1 && (
                <div className="flex justify-center py-1">
                  <ArrowRight className="h-4 w-4 text-muted-foreground rotate-90" />
                </div>
              )}
            </div>
          ))}
        </div>

        <div className="mt-6 rounded-lg bg-blue-50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-900 p-4">
          <h4 className="text-sm font-semibold mb-2 text-blue-900 dark:text-blue-100">Hybrid Benefits</h4>
          <p className="text-sm text-blue-800 dark:text-blue-200">
            This workflow optimizes cost and performance by using the small model for 80% of simple cases,
            while escalating complex cases to the large model, achieving 60% cost reduction with minimal
            performance degradation.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
