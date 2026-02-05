'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { CheckCircle2, AlertCircle, Info } from 'lucide-react';

export interface DistillationRecommendation {
  scenario: string;
  data_availability: string;
  task_flexibility: string;
  recommendation: 'distillation' | 'hybrid' | 'skip_distillation';
  reasoning: string[];
  tradeoffs: {
    cost?: string;
    flexibility?: string;
    quality?: string;
    latency?: string;
  };
  implementation_complexity?: string;
  cost_performance?: string;
}

interface DecisionRecommendationProps {
  recommendation: DistillationRecommendation | null;
}

export function DecisionRecommendation({ recommendation }: DecisionRecommendationProps) {
  if (!recommendation) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Info className="h-5 w-5" />
            Recommendation
          </CardTitle>
          <CardDescription>
            Configure a scenario to get a distillation recommendation
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-48 text-muted-foreground">
            Submit a scenario to see recommendation
          </div>
        </CardContent>
      </Card>
    );
  }

  const getRecommendationColor = () => {
    switch (recommendation.recommendation) {
      case 'distillation': return 'bg-green-50 dark:bg-green-950/20 border-green-200 dark:border-green-900';
      case 'hybrid': return 'bg-blue-50 dark:bg-blue-950/20 border-blue-200 dark:border-blue-900';
      case 'skip_distillation': return 'bg-orange-50 dark:bg-orange-950/20 border-orange-200 dark:border-orange-900';
    }
  };

  const getRecommendationIcon = () => {
    switch (recommendation.recommendation) {
      case 'distillation': return <CheckCircle2 className="h-5 w-5 text-green-600" />;
      case 'hybrid': return <Info className="h-5 w-5 text-blue-600" />;
      case 'skip_distillation': return <AlertCircle className="h-5 w-5 text-orange-600" />;
    }
  };

  const getRecommendationLabel = () => {
    switch (recommendation.recommendation) {
      case 'distillation': return 'Full Distillation';
      case 'hybrid': return 'Hybrid Approach';
      case 'skip_distillation': return 'Skip Distillation';
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          {getRecommendationIcon()}
          Distillation Recommendation
        </CardTitle>
        <CardDescription>
          AI-powered decision based on your scenario
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Main Recommendation */}
        <div className={`rounded-lg border p-4 ${getRecommendationColor()}`}>
          <div className="flex items-center justify-between mb-3">
            <Badge variant="outline" className="text-sm">
              {getRecommendationLabel()}
            </Badge>
            <div className="text-right">
              <div className="text-xs text-muted-foreground">Complexity</div>
              <div className="text-sm font-semibold">{recommendation.implementation_complexity || 'N/A'}</div>
            </div>
          </div>
        </div>

        {/* Reasoning */}
        <div className="space-y-2">
          <h4 className="text-sm font-semibold">Reasoning</h4>
          <ul className="space-y-2">
            {recommendation.reasoning.map((reason, idx) => (
              <li key={idx} className="flex gap-2 text-sm">
                <span className="text-muted-foreground">•</span>
                <span>{reason}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Tradeoffs */}
        {recommendation.tradeoffs && Object.keys(recommendation.tradeoffs).length > 0 && (
          <div className="space-y-3">
            <h4 className="text-sm font-semibold">Tradeoffs</h4>
            <div className="grid gap-3 md:grid-cols-2">
              {Object.entries(recommendation.tradeoffs).map(([key, value]) => (
                <div key={key} className="rounded-lg border p-3">
                  <div className="text-xs text-muted-foreground capitalize">{key.replace('_', ' ')}</div>
                  <div className="text-sm font-semibold mt-1">{value}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Cost Performance */}
        {recommendation.cost_performance && (
          <div className="rounded-lg border p-3 bg-muted/50">
            <div className="text-xs text-muted-foreground">Cost vs Performance</div>
            <div className="text-sm font-semibold mt-1">{recommendation.cost_performance}</div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
