'use client';

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Loader2, Settings, Sparkles } from 'lucide-react';

type UseCase = 'fraud_detection' | 'fraud_explanation' | 'creative_fraud_scenarios' | 'quick_classification' | 'balanced_analysis';

interface SamplingConfig {
  temperature: number;
  top_p: number;
  top_k: number;
  repetition_penalty: number;
  length_penalty: number;
  max_tokens: number;
  stop_sequences: string[];
}

interface RecommendationResult {
  use_case: string;
  recommended_config: SamplingConfig;
  reasoning: string[];
  tradeoffs: Record<string, string>;
  alternatives: SamplingConfig[];
}

const USE_CASES: Record<UseCase, { label: string; description: string }> = {
  fraud_detection: { label: 'Fraud Detection', description: 'Consistent, low-variance decisions' },
  fraud_explanation: { label: 'Fraud Explanation', description: 'Clear, coherent reasoning' },
  creative_fraud_scenarios: { label: 'Creative Scenarios', description: 'Diverse, novel patterns' },
  quick_classification: { label: 'Quick Classification', description: 'Fast, deterministic' },
  balanced_analysis: { label: 'Balanced Analysis', description: 'General purpose' },
};

export function SamplingConfigurator() {
  const [useCase, setUseCase] = useState<UseCase>('fraud_detection');
  const [customConfig, setCustomConfig] = useState<SamplingConfig>({
    temperature: 0.7,
    top_p: 0.9,
    top_k: 50,
    repetition_penalty: 1.1,
    length_penalty: 1.0,
    max_tokens: 256,
    stop_sequences: [],
  });
  const [isLoading, setIsLoading] = useState(false);
  const [recommendation, setRecommendation] = useState<RecommendationResult | null>(null);

  const handleRecommend = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('http://localhost:8000/api/v1/fraud/research/sampling/recommend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ use_case: useCase }),
      });
      const data = await response.json();
      setRecommendation(data);
    } catch (error) {
      console.error('Failed to get recommendation:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const applyConfig = (config: SamplingConfig) => {
    setCustomConfig(config);
  };

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      {/* Left: Configurator */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Sampling Configuration
          </CardTitle>
          <CardDescription>
            Configure sampling parameters or get AI-recommended settings
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Use Case Selector */}
          <div className="space-y-2">
            <Label htmlFor="use-case">Use Case</Label>
            <Select value={useCase} onValueChange={(value) => setUseCase(value as UseCase)}>
              <SelectTrigger id="use-case" className="bg-background">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-white dark:bg-gray-950 border shadow-lg z-50">
                {Object.entries(USE_CASES).map(([key, { label, description }]) => (
                  <SelectItem key={key} value={key} className="bg-white dark:bg-gray-950">
                    <div className="flex flex-col">
                      <span className="font-medium">{label}</span>
                      <span className="text-xs text-muted-foreground">{description}</span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Temperature */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>Temperature</Label>
              <span className="text-sm text-muted-foreground">{customConfig.temperature.toFixed(2)}</span>
            </div>
            <input
              type="range"
              value={customConfig.temperature}
              onChange={(e) => setCustomConfig({ ...customConfig, temperature: parseFloat(e.target.value) })}
              min={0}
              max={2}
              step={0.1}
              className="w-full"
            />
            <p className="text-xs text-muted-foreground">Lower = more deterministic, Higher = more creative</p>
          </div>

          {/* Top-P */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>Top-P (Nucleus Sampling)</Label>
              <span className="text-sm text-muted-foreground">{customConfig.top_p.toFixed(2)}</span>
            </div>
            <input
              type="range"
              value={customConfig.top_p}
              onChange={(e) => setCustomConfig({ ...customConfig, top_p: parseFloat(e.target.value) })}
              min={0}
              max={1}
              step={0.05}
              className="w-full"
            />
          </div>

          {/* Top-K */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>Top-K</Label>
              <span className="text-sm text-muted-foreground">{customConfig.top_k}</span>
            </div>
            <input
              type="range"
              value={customConfig.top_k}
              onChange={(e) => setCustomConfig({ ...customConfig, top_k: parseInt(e.target.value) })}
              min={1}
              max={100}
              step={1}
              className="w-full"
            />
          </div>

          {/* Max Tokens */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>Max Tokens</Label>
              <span className="text-sm text-muted-foreground">{customConfig.max_tokens}</span>
            </div>
            <input
              type="range"
              value={customConfig.max_tokens}
              onChange={(e) => setCustomConfig({ ...customConfig, max_tokens: parseInt(e.target.value) })}
              min={64}
              max={2048}
              step={64}
              className="w-full"
            />
          </div>

          <Button
            onClick={handleRecommend}
            disabled={isLoading}
            className="w-full"
          >
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Getting Recommendation...
              </>
            ) : (
              <>
                <Sparkles className="mr-2 h-4 w-4" />
                Get AI Recommendation
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Right: Recommendation */}
      <Card>
        <CardHeader>
          <CardTitle>Recommended Configuration</CardTitle>
          <CardDescription>
            AI-optimized parameters for {USE_CASES[useCase].label}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {recommendation ? (
            <div className="space-y-4">
              {/* Main Recommendation */}
              <div className="rounded-lg border bg-muted/50 p-4 space-y-3">
                <div className="flex items-start justify-between">
                  <div className="w-full">
                    <Badge variant="default" className="mb-2">Recommended</Badge>
                    <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
                      {recommendation.reasoning.map((reason, idx) => (
                        <li key={idx}>{reason}</li>
                      ))}
                    </ul>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3 mt-3">
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">Temperature</p>
                    <p className="text-lg font-semibold">{recommendation.recommended_config.temperature.toFixed(2)}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">Top-P</p>
                    <p className="text-lg font-semibold">{recommendation.recommended_config.top_p.toFixed(2)}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">Top-K</p>
                    <p className="text-lg font-semibold">{recommendation.recommended_config.top_k}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">Max Tokens</p>
                    <p className="text-lg font-semibold">{recommendation.recommended_config.max_tokens}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">Rep. Penalty</p>
                    <p className="text-lg font-semibold">{recommendation.recommended_config.repetition_penalty.toFixed(1)}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">Len. Penalty</p>
                    <p className="text-lg font-semibold">{recommendation.recommended_config.length_penalty.toFixed(1)}</p>
                  </div>
                </div>

                <Button
                  onClick={() => applyConfig(recommendation.recommended_config)}
                  variant="outline"
                  size="sm"
                  className="w-full"
                >
                  Apply Configuration
                </Button>
              </div>

              {/* Alternatives */}
              {recommendation.alternatives && recommendation.alternatives.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-sm font-semibold">Alternative Configurations</h4>
                  {recommendation.alternatives.map((alt, idx) => (
                    <div key={idx} className="rounded-lg border p-3 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">Alternative {idx + 1}</span>
                        <Button
                          onClick={() => applyConfig(alt)}
                          variant="ghost"
                          size="sm"
                        >
                          Apply
                        </Button>
                      </div>
                      <div className="grid grid-cols-3 gap-2 text-xs">
                        <div>
                          <span className="text-muted-foreground">Temp:</span> {alt.temperature.toFixed(1)}
                        </div>
                        <div>
                          <span className="text-muted-foreground">Top-P:</span> {alt.top_p.toFixed(2)}
                        </div>
                        <div>
                          <span className="text-muted-foreground">Top-K:</span> {alt.top_k}
                        </div>
                        <div>
                          <span className="text-muted-foreground">Rep.Pen:</span> {alt.repetition_penalty.toFixed(1)}
                        </div>
                        <div>
                          <span className="text-muted-foreground">Len.Pen:</span> {alt.length_penalty.toFixed(1)}
                        </div>
                        <div>
                          <span className="text-muted-foreground">Tokens:</span> {alt.max_tokens}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="flex min-h-75 items-center justify-center text-center text-muted-foreground">
              <div>
                <Sparkles className="mx-auto h-8 w-8 mb-2 opacity-50" />
                <p className="text-sm">Select a use case and click &quot;Get AI Recommendation&quot;</p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
