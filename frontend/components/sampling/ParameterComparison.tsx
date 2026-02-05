'use client';

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { GitCompare, ArrowRight } from 'lucide-react';

interface SamplingConfig {
  temperature: number;
  top_p: number;
  top_k: number;
  repetition_penalty: number;
  length_penalty: number;
  max_tokens: number;
  stop_sequences: string[];
}

interface ComparisonResult {
  config_a: SamplingConfig;
  config_b: SamplingConfig;
  differences: {
    [key: string]: {
      config_a: number;
      config_b: number;
      delta: number | null;
    };
  };
  recommendation: string;
  use_case_fit: {
    [key: string]: {
      config_a_score: number;
      config_b_score: number;
      better_fit: string;
    };
  };
}

const PRESET_CONFIGS: Record<string, SamplingConfig> = {
  conservative: { temperature: 0.1, top_p: 0.85, top_k: 20, repetition_penalty: 1.3, length_penalty: 1.0, max_tokens: 128, stop_sequences: [] },
  balanced: { temperature: 0.7, top_p: 0.9, top_k: 50, repetition_penalty: 1.1, length_penalty: 1.0, max_tokens: 256, stop_sequences: [] },
  creative: { temperature: 1.2, top_p: 0.95, top_k: 100, repetition_penalty: 1.0, length_penalty: 1.0, max_tokens: 512, stop_sequences: [] },
};

export function ParameterComparison() {
  const [configA, setConfigA] = useState<SamplingConfig>(PRESET_CONFIGS.conservative);
  const [configB, setConfigB] = useState<SamplingConfig>(PRESET_CONFIGS.creative);
  const [comparison, setComparison] = useState<ComparisonResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleCompare = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('http://localhost:8000/api/v1/fraud/research/sampling/compare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          config_a: configA,
          config_b: configB,
          use_cases: ['fraud_detection', 'fraud_explanation', 'creative_fraud_scenarios'],
        }),
      });
      const data = await response.json();
      setComparison(data);
    } catch (error) {
      console.error('Failed to compare configs:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const loadPreset = (preset: string, target: 'A' | 'B') => {
    const config = PRESET_CONFIGS[preset as keyof typeof PRESET_CONFIGS];
    if (target === 'A') {
      setConfigA(config);
    } else {
      setConfigB(config);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <GitCompare className="h-5 w-5" />
          Parameter Comparison
        </CardTitle>
        <CardDescription>
          Compare two sampling configurations side-by-side
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Config Selection */}
        <div className="grid gap-4 md:grid-cols-2">
          {/* Config A */}
          <div className="rounded-lg border p-4 space-y-3">
            <div className="flex items-center justify-between">
              <Badge variant="outline">Configuration A</Badge>
              <select
                className="text-xs border rounded px-2 py-1"
                onChange={(e) => loadPreset(e.target.value, 'A')}
              >
                <option value="">Load Preset...</option>
                <option value="conservative">Conservative</option>
                <option value="balanced">Balanced</option>
                <option value="creative">Creative</option>
              </select>
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Temperature:</span>
                <span className="font-medium">{configA.temperature}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Top-P:</span>
                <span className="font-medium">{configA.top_p}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Top-K:</span>
                <span className="font-medium">{configA.top_k}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Max Tokens:</span>
                <span className="font-medium">{configA.max_tokens}</span>
              </div>
            </div>
          </div>

          {/* Config B */}
          <div className="rounded-lg border p-4 space-y-3">
            <div className="flex items-center justify-between">
              <Badge variant="outline">Configuration B</Badge>
              <select
                className="text-xs border rounded px-2 py-1"
                onChange={(e) => loadPreset(e.target.value, 'B')}
              >
                <option value="">Load Preset...</option>
                <option value="conservative">Conservative</option>
                <option value="balanced">Balanced</option>
                <option value="creative">Creative</option>
              </select>
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Temperature:</span>
                <span className="font-medium">{configB.temperature}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Top-P:</span>
                <span className="font-medium">{configB.top_p}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Top-K:</span>
                <span className="font-medium">{configB.top_k}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Max Tokens:</span>
                <span className="font-medium">{configB.max_tokens}</span>
              </div>
            </div>
          </div>
        </div>

        <Button onClick={handleCompare} disabled={isLoading} className="w-full">
          {isLoading ? 'Comparing...' : 'Compare Configurations'}
        </Button>

        {/* Comparison Results */}
        {comparison && (
          <div className="space-y-4 mt-6">
            {/* Differences */}
            <div className="rounded-lg border p-4">
              <h4 className="text-sm font-semibold mb-3">Parameter Differences</h4>
              <div className="space-y-2">
                {Object.entries(comparison.differences).map(([param, diff]) => (
                  <div key={param} className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground capitalize">{param.replace(/_/g, ' ')}:</span>
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{diff.config_a}</span>
                      <ArrowRight className="h-3 w-3 text-muted-foreground" />
                      <span className="font-medium">{diff.config_b}</span>
                      {diff.delta !== null && (
                        <Badge variant={diff.delta > 0 ? "default" : "secondary"} className="text-xs">
                          {diff.delta > 0 ? '+' : ''}{diff.delta.toFixed(2)}
                        </Badge>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Recommendation */}
            <div className="rounded-lg bg-blue-50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-900 p-4">
              <h4 className="text-sm font-semibold mb-2 text-blue-900 dark:text-blue-100">Recommendation</h4>
              <p className="text-sm text-blue-800 dark:text-blue-200">{comparison.recommendation}</p>
            </div>

            {/* Use Case Suitability */}
            {comparison.use_case_fit && Object.keys(comparison.use_case_fit).length > 0 && (
              <div className="rounded-lg border p-4">
                <h4 className="text-sm font-semibold mb-3">Use Case Suitability</h4>
                <div className="space-y-2">
                  {Object.entries(comparison.use_case_fit).map(([useCase, scores]) => (
                    <div key={useCase} className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground capitalize">{useCase.replace(/_/g, ' ')}:</span>
                      <div className="flex items-center gap-3">
                        <span className={scores.better_fit === 'config_a' ? 'font-semibold text-green-600' : ''}>
                          A: {scores.config_a_score}
                        </span>
                        <span className="text-muted-foreground">vs</span>
                        <span className={scores.better_fit === 'config_b' ? 'font-semibold text-green-600' : ''}>
                          B: {scores.config_b_score}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
