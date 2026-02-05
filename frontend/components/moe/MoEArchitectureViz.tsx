'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Cpu, Zap } from 'lucide-react';

interface MoEArchitecture {
  model_type: string;
  total_parameters: string;
  active_parameters: string;
  num_experts: number;
  experts_per_token: number;
}

export function MoEArchitectureViz() {
  const [architecture, setArchitecture] = useState<MoEArchitecture | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchArchitecture = async () => {
      setIsLoading(true);
      try {
        const response = await fetch('http://localhost:8000/api/v1/fraud/research/llm-knowledge/moe?model_type=Mixtral-8x7B');
        const data = await response.json();
        setArchitecture(data);
      } catch (error) {
        console.error('Failed to fetch MoE architecture:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchArchitecture();
  }, []);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Cpu className="h-5 w-5" />
            MoE Architecture
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-48">
            <span className="text-muted-foreground">Loading architecture...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!architecture) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Cpu className="h-5 w-5" />
            MoE Architecture
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-48">
            <span className="text-muted-foreground">Failed to load architecture</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Calculate efficiency ratio from the parameters
  const activeParams = parseFloat(architecture.active_parameters.split('B')[0]);
  const totalParams = parseFloat(architecture.total_parameters.split('B')[0]);
  const efficiencyRatio = activeParams / totalParams;
  const efficiencyPercentage = efficiencyRatio * 100;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Cpu className="h-5 w-5" />
          {architecture.model_type} Architecture
        </CardTitle>
        <CardDescription>
          Mixture of Experts parameter efficiency
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Parameter Stats */}
        <div className="grid gap-4 md:grid-cols-2">
          <div className="rounded-lg border p-4 space-y-2">
            <div className="flex items-center gap-2">
              <Cpu className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">Total Parameters</span>
            </div>
            <div className="text-2xl font-bold">{architecture.total_parameters}</div>
          </div>

          <div className="rounded-lg border p-4 space-y-2">
            <div className="flex items-center gap-2">
              <Zap className="h-4 w-4 text-yellow-500" />
              <span className="text-sm text-muted-foreground">Active per Token</span>
            </div>
            <div className="text-2xl font-bold">{architecture.active_parameters}</div>
          </div>
        </div>

        {/* Expert Configuration */}
        <div className="rounded-lg bg-gradient-to-r from-purple-50 to-blue-50 dark:from-purple-950/20 dark:to-blue-950/20 border p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Expert Configuration</span>
            <Badge variant="secondary">
              {architecture.experts_per_token} of {architecture.num_experts} active
            </Badge>
          </div>

          <div className="flex gap-1">
            {Array.from({ length: architecture.num_experts }).map((_, idx) => (
              <div
                key={idx}
                className={`flex-1 h-8 rounded transition-all ${
                  idx < architecture.experts_per_token
                    ? 'bg-gradient-to-t from-purple-500 to-blue-500'
                    : 'bg-gray-200 dark:bg-gray-700'
                }`}
                title={`Expert ${idx + 1}${idx < architecture.experts_per_token ? ' (Active)' : ''}`}
              />
            ))}
          </div>
        </div>

        {/* Efficiency Gauge */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Parameter Efficiency</span>
            <span className="text-2xl font-bold text-green-600">{efficiencyPercentage.toFixed(1)}%</span>
          </div>

          <div className="relative h-4 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
            <div
              className="absolute h-full bg-gradient-to-r from-green-500 to-emerald-500 transition-all duration-500"
              style={{ width: `${efficiencyPercentage}%` }}
            />
          </div>

          <p className="text-xs text-muted-foreground">
            Only {efficiencyPercentage.toFixed(1)}% of parameters are active per token, achieving
            similar performance to dense models with significantly lower computational cost.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
