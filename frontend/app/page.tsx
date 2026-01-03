import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Brain, GitBranch, Shield, Target, Users, Zap } from 'lucide-react';
import Link from 'next/link';

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-zinc-50 to-zinc-100 dark:from-zinc-950 dark:to-zinc-900">
      {/* Hero Section */}
      <section className="container mx-auto px-4 py-20">
        <div className="flex flex-col items-center text-center space-y-8">
          <div className="inline-flex items-center gap-2 rounded-full bg-blue-100 dark:bg-blue-950 px-4 py-1.5 text-sm font-medium text-blue-700 dark:text-blue-300">
            <Shield className="h-4 w-4" />
            <span>AI-Powered Fraud Detection</span>
          </div>

          <h1 className="max-w-4xl text-5xl font-bold leading-tight tracking-tight text-zinc-900 dark:text-zinc-50 sm:text-6xl md:text-7xl">
            FinSight AI
            <span className="block text-blue-600 dark:text-blue-400">
              Advanced Fraud Detection
            </span>
          </h1>

          <p className="max-w-2xl text-xl text-zinc-600 dark:text-zinc-400">
            Leverage multi-agent reasoning systems with ReAct, Chain-of-Thought, and Tree-of-Thought
            patterns to detect financial fraud with unprecedented accuracy and transparency.
          </p>

          <div className="flex flex-col gap-4 sm:flex-row">
            <Button asChild size="lg" className="text-base">
              <Link href="/analyze">
                Start Analysis
              </Link>
            </Button>
            <Button asChild size="lg" variant="outline" className="text-base">
              <Link href="/dashboard">
                View Dashboard
              </Link>
            </Button>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="container mx-auto px-4 py-16">
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          <Card>
            <CardHeader>
              <Brain className="h-10 w-10 text-blue-600 dark:text-blue-400 mb-2" />
              <CardTitle>Multi-Agent Reasoning</CardTitle>
              <CardDescription>
                5 agent architectures including Manager-Worker, Debate, and Swarm intelligence
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm text-zinc-600 dark:text-zinc-400">
                <li>• Single-agent analysis</li>
                <li>• Manager-worker coordination</li>
                <li>• Planner-executor-critic</li>
                <li>• Debate agents with consensus</li>
                <li>• Swarm intelligence (5+ agents)</li>
              </ul>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <Target className="h-10 w-10 text-green-600 dark:text-green-400 mb-2" />
              <CardTitle>Advanced Reasoning Patterns</CardTitle>
              <CardDescription>
                6 reasoning strategies for comprehensive fraud analysis
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm text-zinc-600 dark:text-zinc-400">
                <li>• ReAct (Reasoning + Acting)</li>
                <li>• Chain-of-Thought (CoT)</li>
                <li>• Tree-of-Thought (ToT)</li>
                <li>• Debate reasoning</li>
                <li>• Self-critique</li>
                <li>• Reflection loops</li>
              </ul>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <Zap className="h-10 w-10 text-yellow-600 dark:text-yellow-400 mb-2" />
              <CardTitle>Tool Execution & Recovery</CardTitle>
              <CardDescription>
                Robust tool execution with comprehensive failure recovery
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm text-zinc-600 dark:text-zinc-400">
                <li>• Risk score calculation</li>
                <li>• Policy retrieval (RAG)</li>
                <li>• Transaction history lookup</li>
                <li>• Automatic fallback chains</li>
                <li>• Partial result aggregation</li>
                <li>• Health monitoring</li>
              </ul>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <GitBranch className="h-10 w-10 text-purple-600 dark:text-purple-400 mb-2" />
              <CardTitle>Planning & Task Decomposition</CardTitle>
              <CardDescription>
                Intelligent task planning with DAG execution
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm text-zinc-600 dark:text-zinc-400">
                <li>• 7-task fraud analysis pipeline</li>
                <li>• Dependency tracking</li>
                <li>• Parallel execution (1.4x speedup)</li>
                <li>• Dynamic replanning</li>
                <li>• Goal validation</li>
              </ul>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <Users className="h-10 w-10 text-orange-600 dark:text-orange-400 mb-2" />
              <CardTitle>Human-in-the-Loop</CardTitle>
              <CardDescription>
                Seamless escalation for uncertain cases
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm text-zinc-600 dark:text-zinc-400">
                <li>• Confidence-based escalation</li>
                <li>• 7 escalation triggers</li>
                <li>• Priority classification</li>
                <li>• Suggested decisions</li>
                <li>• Feedback loop integration</li>
              </ul>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <Shield className="h-10 w-10 text-red-600 dark:text-red-400 mb-2" />
              <CardTitle>Production-Ready</CardTitle>
              <CardDescription>
                Async patterns and real-time monitoring
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm text-zinc-600 dark:text-zinc-400">
                <li>• Worker pool (10 workers)</li>
                <li>• WebSocket real-time updates</li>
                <li>• Connection pooling</li>
                <li>• Resource management</li>
                <li>• 42 documented API endpoints</li>
              </ul>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Stats Section */}
      <section className="container mx-auto px-4 py-16">
        <div className="rounded-lg bg-blue-600 dark:bg-blue-950 p-12 text-center text-white">
          <h2 className="text-3xl font-bold mb-8">Platform Capabilities</h2>
          <div className="grid gap-8 md:grid-cols-4">
            <div>
              <div className="text-4xl font-bold">42</div>
              <div className="text-blue-200">API Endpoints</div>
            </div>
            <div>
              <div className="text-4xl font-bold">5</div>
              <div className="text-blue-200">Agent Architectures</div>
            </div>
            <div>
              <div className="text-4xl font-bold">6</div>
              <div className="text-blue-200">Reasoning Patterns</div>
            </div>
            <div>
              <div className="text-4xl font-bold">100%</div>
              <div className="text-blue-200">Swagger Coverage</div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="container mx-auto px-4 py-16 text-center">
        <h2 className="text-3xl font-bold text-zinc-900 dark:text-zinc-50 mb-4">
          Ready to detect fraud with AI?
        </h2>
        <p className="text-lg text-zinc-600 dark:text-zinc-400 mb-8 max-w-2xl mx-auto">
          Upload transactions, get instant risk assessments, and see the complete reasoning trace
          from our multi-agent system.
        </p>
        <Button asChild size="lg" className="text-base">
          <Link href="/analyze">
            Get Started Now
          </Link>
        </Button>
      </section>
    </div>
  );
}

