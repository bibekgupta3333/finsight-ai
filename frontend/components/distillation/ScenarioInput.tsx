'use client';

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Sliders } from 'lucide-react';

export interface DistillationScenario {
  scenario: string;
  data_size: number;
  task_variability: 'fixed' | 'variable' | 'unknown';
}

interface ScenarioInputProps {
  onSubmit: (scenario: DistillationScenario) => void;
  isLoading: boolean;
}

export function ScenarioInput({ onSubmit, isLoading }: ScenarioInputProps) {
  const [scenario, setScenario] = useState<DistillationScenario>({
    scenario: 'fraud_detection',
    data_size: 10000,
    task_variability: 'unknown',
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(scenario);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Sliders className="h-5 w-5" />
          Scenario Configuration
        </CardTitle>
        <CardDescription>
          Define your task requirements for distillation recommendation
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Scenario */}
          <div className="space-y-2">
            <Label htmlFor="scenario">Task Scenario</Label>
            <Select
              value={scenario.scenario}
              onValueChange={(value) => setScenario({ ...scenario, scenario: value })}
            >
              <SelectTrigger id="scenario" className="bg-background">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-background z-50">
                <SelectItem value="fraud_detection">Fraud Detection</SelectItem>
                <SelectItem value="fraud_explanation">Fraud Explanation</SelectItem>
                <SelectItem value="classification">Classification</SelectItem>
                <SelectItem value="generation">Generation</SelectItem>
                <SelectItem value="reasoning">Reasoning</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              The primary task your model will perform
            </p>
          </div>

          {/* Data Size */}
          <div className="space-y-2">
            <Label htmlFor="data-size">Data Size (samples)</Label>
            <Input
              id="data-size"
              type="number"
              min="100"
              max="10000000"
              step="100"
              value={scenario.data_size}
              onChange={(e) => setScenario({ ...scenario, data_size: parseInt(e.target.value) || 0 })}
            />
            <p className="text-xs text-muted-foreground">
              Number of training samples available (100 - 10M)
            </p>
          </div>

          {/* Task Variability */}
          <div className="space-y-2">
            <Label htmlFor="variability">Task Variability</Label>
            <Select
              value={scenario.task_variability}
              onValueChange={(value: 'fixed' | 'variable' | 'unknown') => setScenario({ ...scenario, task_variability: value })}
            >
              <SelectTrigger id="variability" className="bg-background">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-background z-50">
                <SelectItem value="fixed">Fixed (Repetitive tasks)</SelectItem>
                <SelectItem value="variable">Variable (Diverse tasks)</SelectItem>
                <SelectItem value="unknown">Unknown</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              How much variation exists in your task inputs and outputs
            </p>
          </div>

          {/* Submit Button */}
          <Button type="submit" disabled={isLoading} className="w-full">
            {isLoading ? 'Analyzing...' : 'Get Recommendation'}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
