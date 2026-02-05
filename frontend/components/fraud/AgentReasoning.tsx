'use client';

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { Brain, Play, Eye, CheckCircle, AlertTriangle } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface ReasoningStep {
  type: 'thought' | 'action' | 'observation' | 'decision';
  content: string;
  timestamp?: string;
  metadata?: Record<string, any>;
}

interface AgentReasoningProps {
  steps?: ReasoningStep[];
  isLoading?: boolean;
  pattern?: string;
  metadata?: Record<string, any>;
  className?: string;
}

// Mock data for demonstration (will be replaced with real data from API)
const DEFAULT_STEPS: ReasoningStep[] = [
  {
    type: 'thought',
    content: 'This is a high-value TRANSFER transaction with significant balance depletion. Need to analyze the pattern.',
    timestamp: new Date().toISOString(),
  },
  {
    type: 'action',
    content: 'calculate_risk_score(transaction)',
    timestamp: new Date().toISOString(),
    metadata: { tool: 'calculate_risk_score', params: { transaction_id: 'TXN-123' } },
  },
  {
    type: 'observation',
    content: 'Risk score: 87.3 (HIGH). Amount-to-balance ratio is unusual. Destination account shows zero previous balance.',
    timestamp: new Date().toISOString(),
    metadata: { risk_score: 87.3, risk_level: 'HIGH' },
  },
  {
    type: 'action',
    content: 'check_fraud_policy("high_value_transfers")',
    timestamp: new Date().toISOString(),
    metadata: { tool: 'check_fraud_policy', params: { policy_type: 'high_value_transfers' } },
  },
  {
    type: 'observation',
    content: 'Policy states: Transfers >$5000 to new accounts require additional verification. This transaction meets the criteria.',
    timestamp: new Date().toISOString(),
  },
  {
    type: 'decision',
    content: 'FRAUD - Recommend blocking this transaction. High risk score combined with policy violation.',
    timestamp: new Date().toISOString(),
    metadata: { decision: 'FRAUD', confidence: 0.87, should_block: true },
  },
];

const STEP_CONFIG = {
  thought: {
    icon: Brain,
    color: 'text-purple-600',
    bgColor: 'bg-purple-50',
    borderColor: 'border-purple-200',
    label: 'Thought',
  },
  action: {
    icon: Play,
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    label: 'Action',
  },
  observation: {
    icon: Eye,
    color: 'text-green-600',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200',
    label: 'Observation',
  },
  decision: {
    icon: CheckCircle,
    color: 'text-orange-600',
    bgColor: 'bg-orange-50',
    borderColor: 'border-orange-200',
    label: 'Decision',
  },
};

export function AgentReasoning({ steps = DEFAULT_STEPS, isLoading, pattern, metadata, className }: AgentReasoningProps) {
  const [expandedSteps, setExpandedSteps] = useState<string[]>(['step-0']);

  const formatTimestamp = (timestamp?: string) => {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const getPatternBadge = () => {
    if (!pattern) return null;

    const patternLabels: Record<string, { label: string; color: string }> = {
      ReAct: { label: 'ReAct', color: 'bg-purple-100 text-purple-800' },
      'Chain-of-Thought': { label: 'Chain-of-Thought', color: 'bg-blue-100 text-blue-800' },
      'Tree-of-Thought': { label: 'Tree-of-Thought', color: 'bg-green-100 text-green-800' },
      Debate: { label: 'Debate', color: 'bg-orange-100 text-orange-800' },
      'Self-Critique': { label: 'Self-Critique', color: 'bg-pink-100 text-pink-800' },
      Reflection: { label: 'Reflection', color: 'bg-indigo-100 text-indigo-800' },
    };

    const config = patternLabels[pattern] || { label: pattern, color: 'bg-gray-100 text-gray-800' };
    return <Badge className={cn(config.color, 'ml-2')}>{config.label}</Badge>;
  };

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <CardTitle className="flex items-center gap-2">
              <Brain className="h-5 w-5" />
              Agent Reasoning
              {getPatternBadge()}
            </CardTitle>
            <CardDescription>
              {pattern === 'Chain-of-Thought' && 'Step-by-step explicit reasoning chain'}
              {pattern === 'Tree-of-Thought' && 'Multi-path exploration with best path selection'}
              {pattern === 'Debate' && 'Prosecutor vs Defense with Judge verdict'}
              {pattern === 'Self-Critique' && 'Generate → Critique → Revise iterations'}
              {pattern === 'Reflection' && 'Policy validation and reasoning verification'}
              {(!pattern || pattern === 'ReAct') && 'Thought → Action → Observation → Decision'}
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            {metadata?.steps_taken && (
              <Badge variant="outline" className="text-xs">
                {metadata.steps_taken} steps
              </Badge>
            )}
            {metadata?.paths_explored && (
              <Badge variant="outline" className="text-xs">
                {metadata.paths_explored} paths
              </Badge>
            )}
            {metadata?.debate_rounds && (
              <Badge variant="outline" className="text-xs">
                {metadata.debate_rounds} rounds
              </Badge>
            )}
            {metadata?.revisions && (
              <Badge variant="outline" className="text-xs">
                {metadata.revisions} revisions
              </Badge>
            )}
            {!metadata && (
              <Badge variant="outline" className="text-xs">
                {steps.length} steps
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex min-h-[300px] items-center justify-center">
            <div className="text-center text-muted-foreground">
              <Brain className="mx-auto h-8 w-8 animate-pulse" />
              <p className="mt-4 text-sm">Agent is thinking...</p>
            </div>
          </div>
        ) : (
          <Accordion
            type="multiple"
            value={expandedSteps}
            onValueChange={setExpandedSteps}
            className="space-y-3"
          >
            {steps.map((step, index) => {
              const config = STEP_CONFIG[step.type];
              const Icon = config.icon;
              const stepId = `step-${index}`;

              return (
                <AccordionItem
                  key={stepId}
                  value={stepId}
                  className={cn('rounded-lg border', config.borderColor)}
                >
                  <AccordionTrigger className="px-4 hover:no-underline">
                    <div className="flex items-center gap-3 text-left">
                      <div className={cn('rounded-full p-2', config.bgColor)}>
                        <Icon className={cn('h-4 w-4', config.color)} />
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className="text-xs font-normal">
                            Step {index + 1}
                          </Badge>
                          <span className={cn('text-sm font-semibold', config.color)}>
                            {config.label}
                          </span>
                          {step.timestamp && (
                            <span className="text-xs text-muted-foreground">
                              {formatTimestamp(step.timestamp)}
                            </span>
                          )}
                        </div>
                        <p className="mt-1 text-sm text-muted-foreground line-clamp-1">
                          {step.content}
                        </p>
                      </div>
                    </div>
                  </AccordionTrigger>
                  <AccordionContent className="px-4 pb-4">
                    <div className={cn('rounded-lg p-4', config.bgColor)}>
                      <p className="text-sm leading-relaxed">{step.content}</p>

                      {step.metadata && Object.keys(step.metadata).length > 0 && (
                        <div className="mt-3 space-y-1 border-t border-dashed pt-3">
                          <p className="text-xs font-semibold uppercase text-muted-foreground">
                            Metadata
                          </p>
                          <div className="grid gap-1">
                            {Object.entries(step.metadata).map(([key, value]) => (
                              <div key={key} className="flex gap-2 text-xs">
                                <span className="font-mono text-muted-foreground">{key}:</span>
                                <span className="font-mono">
                                  {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </AccordionContent>
                </AccordionItem>
              );
            })}
          </Accordion>
        )}

        {!isLoading && steps.length === 0 && (
          <div className="flex min-h-[300px] items-center justify-center text-center text-muted-foreground">
            <div>
              <AlertTriangle className="mx-auto h-8 w-8 opacity-50" />
              <p className="mt-4 text-sm">No reasoning steps available</p>
              <p className="mt-1 text-xs">Analyze a transaction to see the agent's thought process</p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
