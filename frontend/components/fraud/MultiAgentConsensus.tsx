'use client';

import { useMemo } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Users, CheckCircle2, XCircle, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface AgentVote {
  agent_name: string;
  role: string;
  decision: 'FRAUD' | 'LEGITIMATE' | 'UNCERTAIN';
  confidence: number;
  reasoning: string;
}

interface MultiAgentConsensusProps {
  votes?: AgentVote[];
  consensusThreshold?: number;
  isLoading?: boolean;
  className?: string;
}

// Mock data for demonstration (will be replaced with real API data)
const DEFAULT_VOTES: AgentVote[] = [
  {
    agent_name: 'Transaction Analyst',
    role: 'Pattern Recognition Expert',
    decision: 'FRAUD',
    confidence: 0.82,
    reasoning: 'High-value transfer with complete balance depletion pattern matches known fraud signatures',
  },
  {
    agent_name: 'Policy Expert',
    role: 'Compliance & Rules',
    decision: 'FRAUD',
    confidence: 0.91,
    reasoning: 'Transaction violates policy: high-value transfers to new accounts require verification',
  },
  {
    agent_name: 'Judge',
    role: 'Final Decision Arbiter',
    decision: 'FRAUD',
    confidence: 0.87,
    reasoning: 'Unanimous agreement from specialists. Evidence is overwhelming - recommend blocking',
  },
];

const DECISION_CONFIG = {
  FRAUD: {
    icon: XCircle,
    color: 'text-red-600',
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200',
    label: 'FRAUD',
    variant: 'destructive' as const,
  },
  LEGITIMATE: {
    icon: CheckCircle2,
    color: 'text-green-600',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200',
    label: 'LEGITIMATE',
    variant: 'success' as const,
  },
  UNCERTAIN: {
    icon: AlertCircle,
    color: 'text-yellow-600',
    bgColor: 'bg-yellow-50',
    borderColor: 'border-yellow-200',
    label: 'UNCERTAIN',
    variant: 'warning' as const,
  },
};

export function MultiAgentConsensus({
  votes = DEFAULT_VOTES,
  consensusThreshold = 0.67,
  isLoading,
  className,
}: MultiAgentConsensusProps) {
  const consensusData = useMemo(() => {
    if (!votes || votes.length === 0) {
      return {
        consensusReached: false,
        finalDecision: null,
        agreementPercentage: 0,
        avgConfidence: 0,
        fraudVotes: 0,
        legitimateVotes: 0,
        uncertainVotes: 0,
      };
    }

    const fraudVotes = votes.filter((v) => v.decision === 'FRAUD').length;
    const legitimateVotes = votes.filter((v) => v.decision === 'LEGITIMATE').length;
    const uncertainVotes = votes.filter((v) => v.decision === 'UNCERTAIN').length;

    const totalVotes = votes.length;
    const maxVotes = Math.max(fraudVotes, legitimateVotes, uncertainVotes);
    const agreementPercentage = (maxVotes / totalVotes) * 100;
    const avgConfidence = votes.reduce((sum, v) => sum + v.confidence, 0) / totalVotes;

    let finalDecision: 'FRAUD' | 'LEGITIMATE' | 'UNCERTAIN' | null = null;
    if (fraudVotes === maxVotes) finalDecision = 'FRAUD';
    else if (legitimateVotes === maxVotes) finalDecision = 'LEGITIMATE';
    else finalDecision = 'UNCERTAIN';

    const consensusReached = agreementPercentage >= consensusThreshold * 100;

    return {
      consensusReached,
      finalDecision,
      agreementPercentage,
      avgConfidence,
      fraudVotes,
      legitimateVotes,
      uncertainVotes,
    };
  }, [votes, consensusThreshold]);

  const finalDecisionConfig = consensusData.finalDecision
    ? DECISION_CONFIG[consensusData.finalDecision]
    : null;

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Users className="h-5 w-5" />
              Multi-Agent Consensus
            </CardTitle>
            <CardDescription>
              Collaborative decision-making across {votes.length} specialized agents
            </CardDescription>
          </div>
          {consensusData.consensusReached && finalDecisionConfig && (
            <Badge variant={finalDecisionConfig.variant} className="text-xs">
              {consensusData.agreementPercentage.toFixed(0)}% Agreement
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {isLoading ? (
          <div className="flex min-h-[300px] items-center justify-center">
            <div className="text-center text-muted-foreground">
              <Users className="mx-auto h-8 w-8 animate-pulse" />
              <p className="mt-4 text-sm">Agents are deliberating...</p>
            </div>
          </div>
        ) : (
          <>
            {/* Consensus Summary */}
            {finalDecisionConfig && (
              <div className={cn('rounded-lg border p-4', finalDecisionConfig.borderColor, finalDecisionConfig.bgColor)}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <finalDecisionConfig.icon className={cn('h-6 w-6', finalDecisionConfig.color)} />
                    <div>
                      <p className="text-sm font-medium text-muted-foreground">Final Decision</p>
                      <p className={cn('text-2xl font-bold', finalDecisionConfig.color)}>
                        {finalDecisionConfig.label}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-muted-foreground">Avg Confidence</p>
                    <p className="text-2xl font-bold">{(consensusData.avgConfidence * 100).toFixed(0)}%</p>
                  </div>
                </div>
                {consensusData.consensusReached ? (
                  <div className="mt-3 flex items-center gap-2 text-sm">
                    <CheckCircle2 className="h-4 w-4" />
                    <span className="font-medium">
                      Consensus reached ({consensusData.agreementPercentage.toFixed(0)}% agreement)
                    </span>
                  </div>
                ) : (
                  <div className="mt-3 flex items-center gap-2 text-sm text-yellow-600">
                    <AlertCircle className="h-4 w-4" />
                    <span className="font-medium">
                      No consensus - {consensusData.agreementPercentage.toFixed(0)}% agreement (need {(consensusThreshold * 100).toFixed(0)}%)
                    </span>
                  </div>
                )}
              </div>
            )}

            {/* Vote Breakdown */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <p className="text-sm font-semibold">Vote Breakdown</p>
                <p className="text-xs text-muted-foreground">{votes.length} agents</p>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-center">
                  <p className="text-2xl font-bold text-red-600">{consensusData.fraudVotes}</p>
                  <p className="text-xs text-muted-foreground">FRAUD</p>
                </div>
                <div className="rounded-lg border border-green-200 bg-green-50 p-3 text-center">
                  <p className="text-2xl font-bold text-green-600">{consensusData.legitimateVotes}</p>
                  <p className="text-xs text-muted-foreground">LEGITIMATE</p>
                </div>
                <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-3 text-center">
                  <p className="text-2xl font-bold text-yellow-600">{consensusData.uncertainVotes}</p>
                  <p className="text-xs text-muted-foreground">UNCERTAIN</p>
                </div>
              </div>
            </div>

            {/* Individual Agent Votes */}
            <div className="space-y-3">
              <p className="text-sm font-semibold">Individual Agent Decisions</p>
              {votes.map((vote, index) => {
                const config = DECISION_CONFIG[vote.decision];
                const Icon = config.icon;

                return (
                  <div
                    key={index}
                    className={cn('rounded-lg border p-4', config.borderColor)}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex items-start gap-3 flex-1">
                        <div className={cn('mt-0.5 rounded-full p-2', config.bgColor)}>
                          <Icon className={cn('h-4 w-4', config.color)} />
                        </div>
                        <div className="flex-1 space-y-2">
                          <div>
                            <p className="font-semibold">{vote.agent_name}</p>
                            <p className="text-xs text-muted-foreground">{vote.role}</p>
                          </div>
                          <div className="flex items-center gap-3">
                            <Badge variant={config.variant} className="text-xs">
                              {vote.decision}
                            </Badge>
                            <div className="flex items-center gap-2">
                              <span className="text-xs text-muted-foreground">Confidence:</span>
                              <span className="text-sm font-semibold">
                                {(vote.confidence * 100).toFixed(0)}%
                              </span>
                            </div>
                          </div>
                          <Progress value={vote.confidence * 100} className="h-1.5" />
                          <p className="text-sm text-muted-foreground">{vote.reasoning}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </>
        )}

        {!isLoading && votes.length === 0 && (
          <div className="flex min-h-[300px] items-center justify-center text-center text-muted-foreground">
            <div>
              <Users className="mx-auto h-8 w-8 opacity-50" />
              <p className="mt-4 text-sm">No agent votes available</p>
              <p className="mt-1 text-xs">Analyze a transaction to see multi-agent consensus</p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
