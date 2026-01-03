'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
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
  TrendingUp,
  TrendingDown,
  Shield,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Brain,
} from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import type { HealthStatus } from '@/lib/types';

export default function DashboardPage() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkHealth();
  }, []);

  const checkHealth = async () => {
    setLoading(true);
    try {
      const status = await apiClient.checkHealth();
      setHealth(status);
    } catch (error) {
      console.error('Health check failed:', error);
    } finally {
      setLoading(false);
    }
  };

  // Mock data for demo
  const mockStats = {
    totalTransactions: 10547,
    fraudDetected: 245,
    fraudRate: 2.3,
    avgConfidence: 0.87,
    avgRiskScore: 32.5,
    totalApproved: 9840,
    totalReviewed: 462,
    totalBlocked: 245,
  };

  const mockRecentTransactions = [
    {
      id: 'TXN-001',
      amount: 5420.5,
      type: 'TRANSFER',
      decision: 'APPROVE',
      riskScore: 15.2,
      confidence: 0.95,
      timestamp: '2026-01-03 14:23:45',
    },
    {
      id: 'TXN-002',
      amount: 125000.0,
      type: 'CASH_OUT',
      decision: 'BLOCK',
      riskScore: 92.8,
      confidence: 0.98,
      timestamp: '2026-01-03 14:21:12',
    },
    {
      id: 'TXN-003',
      amount: 3200.0,
      type: 'PAYMENT',
      decision: 'REVIEW',
      riskScore: 68.5,
      confidence: 0.73,
      timestamp: '2026-01-03 14:18:30',
    },
    {
      id: 'TXN-004',
      amount: 890.25,
      type: 'DEBIT',
      decision: 'APPROVE',
      riskScore: 22.1,
      confidence: 0.91,
      timestamp: '2026-01-03 14:15:08',
    },
    {
      id: 'TXN-005',
      amount: 45000.0,
      type: 'TRANSFER',
      decision: 'REVIEW',
      riskScore: 71.3,
      confidence: 0.68,
      timestamp: '2026-01-03 14:12:45',
    },
  ];

  const getDecisionBadge = (decision: string) => {
    switch (decision) {
      case 'APPROVE':
        return (
          <Badge className="bg-green-500">
            <CheckCircle className="h-3 w-3 mr-1" />
            APPROVE
          </Badge>
        );
      case 'REVIEW':
        return (
          <Badge className="bg-yellow-500">
            <AlertTriangle className="h-3 w-3 mr-1" />
            REVIEW
          </Badge>
        );
      case 'BLOCK':
        return (
          <Badge className="bg-red-500">
            <XCircle className="h-3 w-3 mr-1" />
            BLOCK
          </Badge>
        );
      default:
        return <Badge>{decision}</Badge>;
    }
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-zinc-900 dark:text-zinc-50 mb-2">
          Fraud Detection Dashboard
        </h1>
        <p className="text-lg text-zinc-600 dark:text-zinc-400">
          Real-time monitoring and analytics for fraud detection system
        </p>
      </div>

      {/* System Health */}
      <Card className="mb-8">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>System Health</CardTitle>
            {health && (
              <Badge
                className={
                  health.status === 'healthy'
                    ? 'bg-green-500'
                    : health.status === 'degraded'
                    ? 'bg-yellow-500'
                    : 'bg-red-500'
                }
              >
                {health.status.toUpperCase()}
              </Badge>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-center text-zinc-500">Checking system health...</p>
          ) : health ? (
            <div className="grid gap-4 md:grid-cols-3">
              <div>
                <p className="text-sm text-zinc-500 dark:text-zinc-400">Backend API</p>
                <p className="text-xl font-semibold">Connected</p>
              </div>
              <div>
                <p className="text-sm text-zinc-500 dark:text-zinc-400">API Version</p>
                <p className="text-xl font-semibold">{health.version}</p>
              </div>
              <div>
                <p className="text-sm text-zinc-500 dark:text-zinc-400">Uptime</p>
                <p className="text-xl font-semibold">{Math.floor(health.uptime / 60)} min</p>
              </div>
            </div>
          ) : (
            <div className="text-center">
              <p className="text-red-600 mb-4">Unable to connect to backend</p>
              <Button onClick={checkHealth}>Retry</Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Stats Cards */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4 mb-8">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Transactions</CardTitle>
            <Activity className="h-4 w-4 text-zinc-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{mockStats.totalTransactions.toLocaleString()}</div>
            <p className="text-xs text-zinc-500 mt-1">+12.5% from last month</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Fraud Detected</CardTitle>
            <Shield className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{mockStats.fraudDetected}</div>
            <p className="text-xs text-zinc-500 mt-1">
              {mockStats.fraudRate.toFixed(1)}% fraud rate
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Confidence</CardTitle>
            <Brain className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {(mockStats.avgConfidence * 100).toFixed(1)}%
            </div>
            <p className="text-xs text-green-600 mt-1 flex items-center gap-1">
              <TrendingUp className="h-3 w-3" />
              +3.2% improvement
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Risk Score</CardTitle>
            <AlertTriangle className="h-4 w-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{mockStats.avgRiskScore.toFixed(1)}</div>
            <p className="text-xs text-green-600 mt-1 flex items-center gap-1">
              <TrendingDown className="h-3 w-3" />
              -5.1% lower risk
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Decision Breakdown */}
      <Card className="mb-8">
        <CardHeader>
          <CardTitle>Decision Distribution</CardTitle>
          <CardDescription>Transaction decisions across all analyses</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="flex items-center justify-between p-4 border rounded-lg">
              <div className="flex items-center gap-3">
                <div className="h-12 w-12 rounded-full bg-green-100 dark:bg-green-950 flex items-center justify-center">
                  <CheckCircle className="h-6 w-6 text-green-600 dark:text-green-400" />
                </div>
                <div>
                  <p className="text-sm font-medium text-zinc-500 dark:text-zinc-400">Approved</p>
                  <p className="text-2xl font-bold">{mockStats.totalApproved}</p>
                </div>
              </div>
              <Badge className="bg-green-500">93.3%</Badge>
            </div>

            <div className="flex items-center justify-between p-4 border rounded-lg">
              <div className="flex items-center gap-3">
                <div className="h-12 w-12 rounded-full bg-yellow-100 dark:bg-yellow-950 flex items-center justify-center">
                  <AlertTriangle className="h-6 w-6 text-yellow-600 dark:text-yellow-400" />
                </div>
                <div>
                  <p className="text-sm font-medium text-zinc-500 dark:text-zinc-400">Review</p>
                  <p className="text-2xl font-bold">{mockStats.totalReviewed}</p>
                </div>
              </div>
              <Badge className="bg-yellow-500">4.4%</Badge>
            </div>

            <div className="flex items-center justify-between p-4 border rounded-lg">
              <div className="flex items-center gap-3">
                <div className="h-12 w-12 rounded-full bg-red-100 dark:bg-red-950 flex items-center justify-center">
                  <XCircle className="h-6 w-6 text-red-600 dark:text-red-400" />
                </div>
                <div>
                  <p className="text-sm font-medium text-zinc-500 dark:text-zinc-400">Blocked</p>
                  <p className="text-2xl font-bold">{mockStats.totalBlocked}</p>
                </div>
              </div>
              <Badge className="bg-red-500">2.3%</Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Recent Transactions */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Transactions</CardTitle>
          <CardDescription>Latest fraud detection analyses</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Transaction ID</TableHead>
                <TableHead>Type</TableHead>
                <TableHead className="text-right">Amount</TableHead>
                <TableHead className="text-right">Risk Score</TableHead>
                <TableHead className="text-right">Confidence</TableHead>
                <TableHead>Decision</TableHead>
                <TableHead>Timestamp</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {mockRecentTransactions.map((txn) => (
                <TableRow key={txn.id}>
                  <TableCell className="font-medium">{txn.id}</TableCell>
                  <TableCell>
                    <Badge variant="outline">{txn.type}</Badge>
                  </TableCell>
                  <TableCell className="text-right font-mono">
                    ${txn.amount.toLocaleString()}
                  </TableCell>
                  <TableCell className="text-right">
                    <span
                      className={
                        txn.riskScore > 70
                          ? 'text-red-600 font-semibold'
                          : txn.riskScore > 50
                          ? 'text-yellow-600 font-semibold'
                          : 'text-green-600 font-semibold'
                      }
                    >
                      {txn.riskScore.toFixed(1)}
                    </span>
                  </TableCell>
                  <TableCell className="text-right">
                    {(txn.confidence * 100).toFixed(0)}%
                  </TableCell>
                  <TableCell>{getDecisionBadge(txn.decision)}</TableCell>
                  <TableCell className="text-sm text-zinc-500">{txn.timestamp}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
