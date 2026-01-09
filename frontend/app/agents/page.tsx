'use client';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { apiClient } from '@/lib/api-client';
import type { AgentAnalysisResult, Transaction } from '@/lib/types';
import {
  Activity,
  Bot,
  Brain,
  CheckCircle2,
  Clock,
  GitBranch,
  Loader2,
  MessageSquare,
  Network,
  Play,
  Shield,
  Users,
  XCircle,
} from 'lucide-react';
import { useState } from 'react';
import { toast } from 'sonner';

const AGENT_TYPES = [
  {
    id: 'single',
    name: 'Single Agent',
    description: 'Individual agent with ReAct reasoning',
    icon: Bot,
    color: 'text-blue-500',
  },
  {
    id: 'manager-worker',
    name: 'Manager-Worker',
    description: 'Hierarchical delegation with consensus',
    icon: Users,
    color: 'text-green-500',
  },
  {
    id: 'planner-executor-critic',
    name: 'Planner-Executor-Critic',
    description: '3-phase investigation workflow',
    icon: GitBranch,
    color: 'text-purple-500',
  },
  {
    id: 'debate-system',
    name: 'Debate System',
    description: 'Multi-agent deliberation',
    icon: MessageSquare,
    color: 'text-orange-500',
  },
  {
    id: 'role-specialized',
    name: 'Role-Specialized',
    description: 'Domain expert ensemble',
    icon: Shield,
    color: 'text-red-500',
  },
  {
    id: 'swarm',
    name: 'Swarm Intelligence',
    description: 'Collective decision making',
    icon: Network,
    color: 'text-cyan-500',
  },
];

export default function AgentsPage() {
  const [selectedAgent, setSelectedAgent] = useState<string>('single');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AgentAnalysisResult | null>(null);

  // Sample transaction for testing
  const [transaction, setTransaction] = useState<Transaction>({
    transaction_id: 'TX_AGENT_001',
    type: 'CASH_OUT',
    amount: 175000.0,
    oldbalanceOrg: 190000.0,
    newbalanceOrig: 15000.0,
    oldbalanceDest: 0.0,
    newbalanceDest: 0.0,
    nameOrig: 'C123456',
    nameDest: 'M789012',
    timestamp: new Date().toISOString(),
  });

  const handleAnalyze = async () => {
    setLoading(true);
    setResult(null);

    try {
      let response: AgentAnalysisResult;

      switch (selectedAgent) {
        case 'single':
          response = await apiClient.analyzeSingleAgent(transaction);
          break;
        case 'manager-worker':
          response = await apiClient.analyzeManagerWorker(transaction);
          break;
        case 'planner-executor-critic':
          response = await apiClient.analyzePlannerExecutorCritic(transaction);
          break;
        case 'debate-system':
          response = await apiClient.analyzeDebateSystem(transaction);
          break;
        case 'role-specialized':
          response = await apiClient.analyzeRoleSpecialized(transaction);
          break;
        case 'swarm':
          response = await apiClient.analyzeSwarm(transaction);
          break;
        default:
          throw new Error('Unknown agent type');
      }

      setResult(response);
      toast.success('Analysis complete');
    } catch (error: any) {
      toast.error(`Analysis failed: ${error.message}`);
      console.error('Agent analysis error:', error);
    } finally {
      setLoading(false);
    }
  };

  const agentConfig = AGENT_TYPES.find((a) => a.id === selectedAgent);
  const AgentIcon = agentConfig?.icon || Bot;

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Multi-Agent Systems</h1>
        <p className="text-muted-foreground mt-2">
          Test different agent architectures for fraud detection
        </p>
      </div>

      {/* Agent Selector */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {AGENT_TYPES.map((agent) => {
          const Icon = agent.icon;
          return (
            <Card
              key={agent.id}
              className={`cursor-pointer transition-all hover:shadow-md ${
                selectedAgent === agent.id ? 'ring-2 ring-primary' : ''
              }`}
              onClick={() => setSelectedAgent(agent.id)}
            >
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">{agent.name}</CardTitle>
                <Icon className={`h-4 w-4 ${agent.color}`} />
              </CardHeader>
              <CardContent>
                <p className="text-xs text-muted-foreground">{agent.description}</p>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Transaction Input */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            Transaction Details
          </CardTitle>
          <CardDescription>Configure the transaction to analyze</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <div className="space-y-2">
              <Label htmlFor="txType">Transaction Type</Label>
              <Select
                value={transaction.type}
                onValueChange={(value) =>
                  setTransaction({ ...transaction, type: value })
                }
              >
                <SelectTrigger id="txType">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="PAYMENT">PAYMENT</SelectItem>
                  <SelectItem value="TRANSFER">TRANSFER</SelectItem>
                  <SelectItem value="CASH_OUT">CASH_OUT</SelectItem>
                  <SelectItem value="DEBIT">DEBIT</SelectItem>
                  <SelectItem value="CASH_IN">CASH_IN</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="amount">Amount</Label>
              <Input
                id="amount"
                type="number"
                value={transaction.amount}
                onChange={(e) =>
                  setTransaction({ ...transaction, amount: parseFloat(e.target.value) })
                }
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="oldBalanceOrg">Old Balance (Origin)</Label>
              <Input
                id="oldBalanceOrg"
                type="number"
                value={transaction.oldbalanceOrg}
                onChange={(e) =>
                  setTransaction({ ...transaction, oldbalanceOrg: parseFloat(e.target.value) })
                }
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="newBalanceOrig">New Balance (Origin)</Label>
              <Input
                id="newBalanceOrig"
                type="number"
                value={transaction.newbalanceOrig}
                onChange={(e) =>
                  setTransaction({ ...transaction, newbalanceOrig: parseFloat(e.target.value) })
                }
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="oldBalanceDest">Old Balance (Destination)</Label>
              <Input
                id="oldBalanceDest"
                type="number"
                value={transaction.oldbalanceDest}
                onChange={(e) =>
                  setTransaction({ ...transaction, oldbalanceDest: parseFloat(e.target.value) })
                }
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="newBalanceDest">New Balance (Destination)</Label>
              <Input
                id="newBalanceDest"
                type="number"
                value={transaction.newbalanceDest}
                onChange={(e) =>
                  setTransaction({ ...transaction, newbalanceDest: parseFloat(e.target.value) })
                }
              />
            </div>
          </div>

          <div className="mt-4 flex justify-end">
            <Button onClick={handleAnalyze} disabled={loading} className="gap-2">
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Analyzing...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4" />
                  Run {agentConfig?.name} Analysis
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Results */}
      {result && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AgentIcon className={`h-5 w-5 ${agentConfig?.color}`} />
              Analysis Results
            </CardTitle>
            <CardDescription>
              {agentConfig?.name} • {result.transaction_id}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="overview">
              <TabsList className="grid w-full grid-cols-4">
                <TabsTrigger value="overview">Overview</TabsTrigger>
                <TabsTrigger value="observations">Observations</TabsTrigger>
                <TabsTrigger value="reasoning">Reasoning</TabsTrigger>
                <TabsTrigger value="metrics">Metrics</TabsTrigger>
              </TabsList>

              {/* Overview Tab */}
              <TabsContent value="overview" className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                  <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                      <CardTitle className="text-sm font-medium">Fraud Detection</CardTitle>
                      {result.is_fraud ? (
                        <XCircle className="h-4 w-4 text-red-500" />
                      ) : (
                        <CheckCircle2 className="h-4 w-4 text-green-500" />
                      )}
                    </CardHeader>
                    <CardContent>
                      <div className="text-2xl font-bold">
                        {result.is_fraud ? 'FRAUD' : 'LEGITIMATE'}
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Risk Level: {result.risk_level || 'N/A'}
                      </p>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                      <CardTitle className="text-sm font-medium">Risk Score</CardTitle>
                      <Brain className="h-4 w-4 text-orange-500" />
                    </CardHeader>
                    <CardContent>
                      <div className="text-2xl font-bold">{result.risk_score.toFixed(1)}</div>
                      <p className="text-xs text-muted-foreground">0-100 scale</p>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                      <CardTitle className="text-sm font-medium">Confidence</CardTitle>
                      <Activity className="h-4 w-4 text-blue-500" />
                    </CardHeader>
                    <CardContent>
                      <div className="text-2xl font-bold">
                        {(result.confidence * 100).toFixed(1)}%
                      </div>
                      <p className="text-xs text-muted-foreground">Model certainty</p>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                      <CardTitle className="text-sm font-medium">Execution Time</CardTitle>
                      <Clock className="h-4 w-4 text-purple-500" />
                    </CardHeader>
                    <CardContent>
                      <div className="text-2xl font-bold">
                        {((result.execution_time || result.total_time || 0) * 1000).toFixed(0)}ms
                      </div>
                      <p className="text-xs text-muted-foreground">Processing duration</p>
                    </CardContent>
                  </Card>
                </div>

                <Card>
                  <CardHeader>
                    <CardTitle>Explanation</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm">{result.explanation}</p>
                  </CardContent>
                </Card>

                {/* Agent-specific metrics */}
                {(result.num_agents || result.swarm_size) && (
                  <Card>
                    <CardHeader>
                      <CardTitle>Agent Metrics</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2">
                      {result.num_agents && (
                        <div className="flex justify-between">
                          <span className="text-sm text-muted-foreground">Number of Agents:</span>
                          <Badge>{result.num_agents}</Badge>
                        </div>
                      )}
                      {result.swarm_size && (
                        <div className="flex justify-between">
                          <span className="text-sm text-muted-foreground">Swarm Size:</span>
                          <Badge>{result.swarm_size}</Badge>
                        </div>
                      )}
                      {result.consensus_strategy && (
                        <div className="flex justify-between">
                          <span className="text-sm text-muted-foreground">Consensus Strategy:</span>
                          <Badge variant="outline">{result.consensus_strategy}</Badge>
                        </div>
                      )}
                      {result.agreement_level !== undefined && (
                        <div className="flex justify-between">
                          <span className="text-sm text-muted-foreground">Agreement Level:</span>
                          <Badge variant="secondary">
                            {(result.agreement_level * 100).toFixed(0)}%
                          </Badge>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                )}
              </TabsContent>

              {/* Observations Tab */}
              <TabsContent value="observations" className="space-y-4">
                {result.observations && result.observations.length > 0 && (
                  <Card>
                    <CardHeader>
                      <CardTitle>Observations</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <ul className="space-y-2">
                        {result.observations.map((obs, idx) => (
                          <li key={idx} className="flex items-start gap-2 text-sm">
                            <CheckCircle2 className="h-4 w-4 mt-0.5 text-green-500 flex-shrink-0" />
                            <span>{obs}</span>
                          </li>
                        ))}
                      </ul>
                    </CardContent>
                  </Card>
                )}

                {result.anomalies && result.anomalies.length > 0 && (
                  <Card>
                    <CardHeader>
                      <CardTitle>Anomalies Detected</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <ul className="space-y-2">
                        {result.anomalies.map((anomaly, idx) => (
                          <li key={idx} className="flex items-start gap-2 text-sm">
                            <XCircle className="h-4 w-4 mt-0.5 text-red-500 flex-shrink-0" />
                            <span>{anomaly}</span>
                          </li>
                        ))}
                      </ul>
                    </CardContent>
                  </Card>
                )}
              </TabsContent>

              {/* Reasoning Tab */}
              <TabsContent value="reasoning" className="space-y-4">
                {result.reasoning_steps && result.reasoning_steps.length > 0 ? (
                  <Card>
                    <CardHeader>
                      <CardTitle>Reasoning Steps</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <ol className="space-y-2">
                        {result.reasoning_steps.map((step, idx) => (
                          <li key={idx} className="flex items-start gap-3 text-sm">
                            <Badge variant="outline" className="mt-0.5">
                              {idx + 1}
                            </Badge>
                            <span>{step}</span>
                          </li>
                        ))}
                      </ol>
                    </CardContent>
                  </Card>
                ) : (
                  <Card>
                    <CardContent className="pt-6 text-center text-muted-foreground">
                      No reasoning steps available for this agent type
                    </CardContent>
                  </Card>
                )}

                {result.self_critique && (
                  <Card>
                    <CardHeader>
                      <CardTitle>Self-Critique</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="text-sm">{result.self_critique}</p>
                    </CardContent>
                  </Card>
                )}
              </TabsContent>

              {/* Metrics Tab */}
              <TabsContent value="metrics" className="space-y-4">
                <Card>
                  <CardHeader>
                    <CardTitle>Execution Metrics</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">Agent Type:</span>
                      <Badge>{result.agent_type}</Badge>
                    </div>
                    {result.total_steps !== undefined && (
                      <div className="flex justify-between">
                        <span className="text-sm text-muted-foreground">Total Steps:</span>
                        <Badge variant="secondary">{result.total_steps}</Badge>
                      </div>
                    )}
                    {result.termination_reason && (
                      <div className="flex justify-between">
                        <span className="text-sm text-muted-foreground">Termination Reason:</span>
                        <Badge variant="outline">{result.termination_reason}</Badge>
                      </div>
                    )}
                    {result.should_escalate !== undefined && (
                      <div className="flex justify-between">
                        <span className="text-sm text-muted-foreground">Should Escalate:</span>
                        <Badge variant={result.should_escalate ? 'destructive' : 'default'}>
                          {result.should_escalate ? 'Yes' : 'No'}
                        </Badge>
                      </div>
                    )}
                    {result.escalation_reason && (
                      <div className="space-y-1">
                        <span className="text-sm text-muted-foreground">Escalation Reason:</span>
                        <p className="text-sm">{result.escalation_reason}</p>
                      </div>
                    )}
                  </CardContent>
                </Card>

                {result.tool_results && Object.keys(result.tool_results).length > 0 && (
                  <Card>
                    <CardHeader>
                      <CardTitle>Tool Results</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <pre className="text-xs bg-muted p-4 rounded-lg overflow-auto">
                        {JSON.stringify(result.tool_results, null, 2)}
                      </pre>
                    </CardContent>
                  </Card>
                )}
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
