'use client';

import { useState, useMemo } from 'react';
import { TransactionAnalyzer } from '@/components/fraud/TransactionAnalyzer';
import { AgentReasoning, type ReasoningStep } from '@/components/fraud/AgentReasoning';
import { MultiAgentConsensus, type AgentVote } from '@/components/fraud/MultiAgentConsensus';
import type { FraudAnalysisResult } from '@/lib/types';

type ReasoningPattern = 'react' | 'cot' | 'tot' | 'debate' | 'self-critique' | 'reflection'

export default function FraudDetectionDashboard() {
  const [analysisResult, setAnalysisResult] = useState<FraudAnalysisResult | null>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [selectedPattern, setSelectedPattern] = useState<ReasoningPattern>('react')

  const handleAnalysisComplete = (result: FraudAnalysisResult) => {
    setAnalysisResult(result);
    setIsAnalyzing(false);
  };

  // Transform reasoning_steps from API into ReasoningStep format
  const reasoningSteps = useMemo<ReasoningStep[] | undefined>(() => {
    if (!analysisResult?.prediction.reasoning_steps) return undefined;

    const timestamp = new Date().toLocaleTimeString('en-US', { hour12: false });
    return analysisResult.prediction.reasoning_steps.map((step, idx) => {
      // Parse step content to determine type
      const stepLower = step.toLowerCase();
      let type: ReasoningStep['type'] = 'thought';

      if (stepLower.includes('calculate') || stepLower.includes('check') || stepLower.includes('analyze')) {
        type = 'action';
      } else if (stepLower.includes('risk score') || stepLower.includes('result') || stepLower.includes('policy')) {
        type = 'observation';
      } else if (stepLower.includes('decision') || stepLower.includes('recommend') || stepLower.includes('fraud') || stepLower.includes('legitimate')) {
        type = 'decision';
      }

      return {
        type,
        content: step,
        timestamp,
      };
    });
  }, [analysisResult]);

  // Generate agent votes from analysis result
  const agentVotes = useMemo<AgentVote[] | undefined>(() => {
    if (!analysisResult) return undefined;

    const { is_fraud, confidence, explanation, risk_score } = analysisResult.prediction;
    const decision = is_fraud ? 'FRAUD' : 'LEGITIMATE';

    // Simulate 3 agents with slight confidence variations
    return [
      {
        agent_name: 'Transaction Analyst',
        role: 'Pattern Recognition Expert',
        decision,
        confidence: Math.min(confidence * 0.95, 0.99),
        reasoning: `Risk score ${risk_score.toFixed(1)} indicates ${is_fraud ? 'fraudulent' : 'legitimate'} pattern`
      },
      {
        agent_name: 'Policy Expert',
        role: 'Compliance & Rules',
        decision,
        confidence: Math.min(confidence * 1.05, 0.99),
        reasoning: explanation
      },
      {
        agent_name: 'Judge',
        role: 'Final Decision Arbiter',
        decision,
        confidence,
        reasoning: `Confidence: ${(confidence * 100).toFixed(0)}% - ${is_fraud ? 'Blocking recommended' : 'Approved'}`
      }
    ];
  }, [analysisResult]);

  return (
    <div className="container mx-auto space-y-6 py-8">
      {/* Header */}
      <div className="space-y-2">
        <h1 className="text-4xl font-bold tracking-tight">Fraud Detection Dashboard</h1>
        <p className="text-muted-foreground">
          Real-time multi-agent fraud detection with explainable AI reasoning
        </p>
      </div>

      {/* Transaction Analyzer - Full Width */}
      <TransactionAnalyzer
        onAnalysisComplete={handleAnalysisComplete}
        selectedPattern={selectedPattern}
        onPatternChange={setSelectedPattern}
      />

      {/* Agent Reasoning & Consensus - Two Columns */}
      <div className="grid gap-6 lg:grid-cols-2">
        <AgentReasoning
          steps={reasoningSteps}
          isLoading={isAnalyzing}
          pattern={analysisResult?.metadata?.pattern}
          metadata={analysisResult?.metadata ?? undefined}
        />
        <MultiAgentConsensus
          votes={agentVotes}
          isLoading={isAnalyzing}
        />
      </div>
    </div>
  );
}
