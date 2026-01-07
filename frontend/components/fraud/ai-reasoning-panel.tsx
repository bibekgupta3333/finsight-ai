'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Brain, CheckCircle2, AlertCircle, Info } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ReasoningStep {
  step: number;
  type: 'thought' | 'action' | 'observation' | 'decision';
  content: string;
  confidence?: number;
}

interface AIReasoningPanelProps {
  steps: ReasoningStep[];
  finalDecision?: string;
  showConfidence?: boolean;
  className?: string;
}

export function AIReasoningPanel({
  steps,
  finalDecision,
  showConfidence = true,
  className,
}: AIReasoningPanelProps) {
  const getStepIcon = (type: ReasoningStep['type']) => {
    switch (type) {
      case 'thought':
        return <Brain className="h-4 w-4" />;
      case 'action':
        return <Info className="h-4 w-4" />;
      case 'observation':
        return <AlertCircle className="h-4 w-4" />;
      case 'decision':
        return <CheckCircle2 className="h-4 w-4" />;
    }
  };

  const getStepColor = (type: ReasoningStep['type']) => {
    switch (type) {
      case 'thought':
        return 'border-blue-500 bg-blue-50 dark:bg-blue-950';
      case 'action':
        return 'border-purple-500 bg-purple-50 dark:bg-purple-950';
      case 'observation':
        return 'border-orange-500 bg-orange-50 dark:bg-orange-950';
      case 'decision':
        return 'border-green-500 bg-green-50 dark:bg-green-950';
    }
  };

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Brain className="h-5 w-5" />
          AI Reasoning Chain
        </CardTitle>
        <CardDescription>
          Step-by-step analysis of the fraud detection process
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[400px] pr-4">
          <div className="space-y-3">
            {steps.map((step, index) => (
              <div
                key={index}
                className={cn(
                  'relative rounded-lg border-l-4 p-4',
                  getStepColor(step.type)
                )}
              >
                <div className="flex items-start gap-3">
                  <div className="mt-0.5">{getStepIcon(step.type)}</div>
                  <div className="flex-1 space-y-1">
                    <div className="flex items-center justify-between">
                      <Badge variant="outline" className="text-xs">
                        Step {step.step}: {step.type}
                      </Badge>
                      {showConfidence && step.confidence !== undefined && (
                        <span className="text-xs text-muted-foreground">
                          Confidence: {(step.confidence * 100).toFixed(0)}%
                        </span>
                      )}
                    </div>
                    <p className="text-sm leading-relaxed">{step.content}</p>
                  </div>
                </div>
              </div>
            ))}

            {finalDecision && (
              <div className="mt-6 rounded-lg border-2 border-primary bg-primary/5 p-4">
                <div className="flex items-start gap-3">
                  <CheckCircle2 className="h-5 w-5 text-primary" />
                  <div className="flex-1">
                    <h4 className="font-semibold">Final Decision</h4>
                    <p className="mt-1 text-sm">{finalDecision}</p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
