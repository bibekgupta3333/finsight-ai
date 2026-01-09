'use client';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Activity,
  Brain,
  CheckCircle,
  Clock,
  GitBranch
} from 'lucide-react';
import { useState } from 'react';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from 'recharts';

// Mock data for agent execution
const agentExecutions = [
  {
    id: 'exec-001',
    agent: 'ReAct',
    status: 'completed',
    duration: 2.5,
    toolCalls: 8,
    reasoning: 'Observation → Thought → Action',
    accuracy: 95,
  },
  {
    id: 'exec-002',
    agent: 'Chain-of-Thought',
    status: 'running',
    duration: 1.8,
    toolCalls: 5,
    reasoning: 'Step-by-step reasoning',
    accuracy: 92,
  },
  {
    id: 'exec-003',
    agent: 'Tree-of-Thought',
    status: 'completed',
    duration: 3.2,
    toolCalls: 12,
    reasoning: 'Multiple paths explored',
    accuracy: 97,
  },
  {
    id: 'exec-004',
    agent: 'Manager-Worker',
    status: 'completed',
    duration: 4.1,
    toolCalls: 15,
    reasoning: 'Coordinated analysis',
    accuracy: 94,
  },
];

const performanceData = [
  { time: '10:00', react: 2.1, cot: 1.5, tot: 3.0, manager: 3.8 },
  { time: '10:15', react: 2.3, cot: 1.7, tot: 2.8, manager: 4.2 },
  { time: '10:30', react: 2.0, cot: 1.6, tot: 3.2, manager: 3.9 },
  { time: '10:45', react: 2.5, cot: 1.8, tot: 3.1, manager: 4.0 },
  { time: '11:00', react: 2.2, cot: 1.5, tot: 2.9, manager: 3.7 },
];

const toolUsageData = [
  { tool: 'Risk Analyzer', calls: 142, avgTime: 0.3, successRate: 98 },
  { tool: 'Pattern Detector', calls: 128, avgTime: 0.5, successRate: 96 },
  { tool: 'Consensus Voter', calls: 95, avgTime: 0.2, successRate: 100 },
  { tool: 'Explanation Gen', calls: 156, avgTime: 0.8, successRate: 94 },
];

const reasoningSteps = [
  {
    step: 1,
    type: 'Observation',
    content: 'Transaction amount: $5,420.50, Type: TRANSFER, Origin balance change: -$5,420.50',
    duration: 0.2,
  },
  {
    step: 2,
    type: 'Thought',
    content: 'Large transfer with complete balance depletion suggests potential fraud',
    duration: 0.5,
  },
  {
    step: 3,
    type: 'Action',
    content: 'Call RiskAnalyzer with transaction details',
    duration: 0.3,
  },
  {
    step: 4,
    type: 'Observation',
    content: 'Risk score: 87.5, High-risk indicators: amount, balance_depletion, velocity',
    duration: 0.2,
  },
  {
    step: 5,
    type: 'Thought',
    content: 'Multiple high-risk factors indicate fraud. Need consensus from other agents',
    duration: 0.4,
  },
  {
    step: 6,
    type: 'Action',
    content: 'Initiate multi-agent consensus (3 agents)',
    duration: 1.2,
  },
  {
    step: 7,
    type: 'Final Decision',
    content: 'BLOCK transaction - 100% consensus, confidence: 0.95',
    duration: 0.1,
  },
];

export default function AgentMonitoringPage() {
  const [selectedExecution, setSelectedExecution] = useState<string | null>(null);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-500';
      case 'running':
        return 'bg-blue-500';
      case 'failed':
        return 'bg-red-500';
      default:
        return 'bg-zinc-500';
    }
  };

  return (
    <div className="container mx-auto py-8 px-4">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-zinc-900 dark:text-zinc-100 mb-2">
          Agent Monitoring Dashboard
        </h1>
        <p className="text-zinc-600 dark:text-zinc-400">
          Real-time monitoring of AI agent execution and reasoning
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-6 md:grid-cols-4 mb-8">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Agents</CardTitle>
            <Brain className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">8</div>
            <p className="text-xs text-zinc-500 mt-1">2 running now</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Response Time</CardTitle>
            <Clock className="h-4 w-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">2.8s</div>
            <p className="text-xs text-green-500 mt-1">↓ 15% from last hour</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Accuracy</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">94.5%</div>
            <p className="text-xs text-green-500 mt-1">↑ 2.3% improvement</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Tool Calls</CardTitle>
            <Activity className="h-4 w-4 text-purple-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">521</div>
            <p className="text-xs text-zinc-500 mt-1">Last hour</p>
          </CardContent>
        </Card>
      </div>

      {/* Performance Chart */}
      <Card className="mb-8">
        <CardHeader>
          <CardTitle>Agent Execution Time Trends</CardTitle>
          <CardDescription>Average response time by agent type (seconds)</CardDescription>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={performanceData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="react" stroke="#3b82f6" name="ReAct" />
              <Line type="monotone" dataKey="cot" stroke="#22c55e" name="Chain-of-Thought" />
              <Line type="monotone" dataKey="tot" stroke="#eab308" name="Tree-of-Thought" />
              <Line type="monotone" dataKey="manager" stroke="#a855f7" name="Manager-Worker" />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2 mb-8">
        {/* Agent Executions */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Agent Executions</CardTitle>
            <CardDescription>Latest agent analysis runs</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Agent</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Duration</TableHead>
                  <TableHead>Accuracy</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {agentExecutions.map((exec) => (
                  <TableRow
                    key={exec.id}
                    className="cursor-pointer hover:bg-zinc-50 dark:hover:bg-zinc-800"
                    onClick={() => setSelectedExecution(exec.id)}
                  >
                    <TableCell className="font-medium">{exec.agent}</TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(exec.status)}>
                        {exec.status.toUpperCase()}
                      </Badge>
                    </TableCell>
                    <TableCell>{exec.duration}s</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Progress value={exec.accuracy} className="w-16" />
                        <span className="text-sm">{exec.accuracy}%</span>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        {/* Tool Usage */}
        <Card>
          <CardHeader>
            <CardTitle>Tool Usage Statistics</CardTitle>
            <CardDescription>Most frequently used tools</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Tool</TableHead>
                  <TableHead>Calls</TableHead>
                  <TableHead>Avg Time</TableHead>
                  <TableHead>Success</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {toolUsageData.map((tool) => (
                  <TableRow key={tool.tool}>
                    <TableCell className="font-medium">{tool.tool}</TableCell>
                    <TableCell>{tool.calls}</TableCell>
                    <TableCell>{tool.avgTime}s</TableCell>
                    <TableCell>
                      <Badge
                        className={
                          tool.successRate >= 95 ? 'bg-green-500' : 'bg-yellow-500'
                        }
                      >
                        {tool.successRate}%
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>

      {/* Reasoning Trace */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <GitBranch className="h-5 w-5" />
            Reasoning Trace Explorer
          </CardTitle>
          <CardDescription>Step-by-step agent reasoning process (ReAct pattern)</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {reasoningSteps.map((step) => (
              <div key={step.step} className="flex gap-4">
                <div className="flex flex-col items-center">
                  <div className="rounded-full bg-blue-500 text-white h-8 w-8 flex items-center justify-center font-bold text-sm">
                    {step.step}
                  </div>
                  {step.step < reasoningSteps.length && (
                    <div className="w-0.5 h-full bg-zinc-300 dark:bg-zinc-700 mt-2" />
                  )}
                </div>
                <div className="flex-1 pb-6">
                  <div className="flex items-center gap-2 mb-2">
                    <Badge variant="outline">{step.type}</Badge>
                    <span className="text-xs text-zinc-500">{step.duration}s</span>
                  </div>
                  <p className="text-sm text-zinc-700 dark:text-zinc-300">{step.content}</p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
