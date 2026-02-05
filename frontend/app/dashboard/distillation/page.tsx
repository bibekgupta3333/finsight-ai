'use client';

import { useState } from 'react';
import { ScenarioInput, DistillationScenario } from '@/components/distillation/ScenarioInput';
import { DecisionRecommendation, DistillationRecommendation } from '@/components/distillation/DecisionRecommendation';
import { HybridWorkflow } from '@/components/distillation/HybridWorkflow';
import { CostPerformanceChart } from '@/components/distillation/CostPerformanceChart';

export default function DistillationPage() {
  const [recommendation, setRecommendation] = useState<DistillationRecommendation | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleScenarioSubmit = async (scenario: DistillationScenario) => {
    setIsLoading(true);
    try {
      const response = await fetch('http://localhost:8000/api/v1/fraud/research/llm-knowledge/distillation-decision', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(scenario),
      });
      const data = await response.json();
      setRecommendation(data);
    } catch (error) {
      console.error('Failed to get distillation recommendation:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <h1 className="text-3xl font-bold">Distillation Decision Framework</h1>
        <p className="text-muted-foreground mt-2">
          Get AI-powered recommendations on when and how to distill large language models
        </p>
      </div>

      <div className="grid gap-6">
        {/* Row 1: Scenario Input + Decision Recommendation */}
        <div className="grid gap-6 lg:grid-cols-2">
          <ScenarioInput onSubmit={handleScenarioSubmit} isLoading={isLoading} />
          <DecisionRecommendation recommendation={recommendation} />
        </div>

        {/* Row 2: Hybrid Workflow + Cost Performance Chart */}
        <div className="grid gap-6 lg:grid-cols-2">
          <HybridWorkflow />
          <CostPerformanceChart />
        </div>
      </div>
    </div>
  );
}
