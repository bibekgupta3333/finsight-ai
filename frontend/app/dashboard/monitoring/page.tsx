'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  LineChart, Line, BarChart, Bar, ScatterChart, Scatter,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  Cell, PieChart, Pie
} from 'recharts';
import { Activity, AlertCircle, TrendingUp, Zap, Database, Clock } from 'lucide-react';

interface ModelPerformance {
  timestamp: string;
  true_positives: number;
  true_negatives: number;
  false_positives: number;
  false_negatives: number;
  precision: number;
  recall: number;
  f1_score: number;
  accuracy: number;
  total_predictions: number;
}

interface LatencyMetrics {
  [endpoint: string]: {
    p50: number;
    p95: number;
    p99: number;
    mean: number;
    min: number;
    max: number;
    count: number;
  };
}

interface ErrorMetrics {
  error_type: string;
  error_count: number;
  error_rate: number;
}

interface TokenUsage {
  total_tokens: number;
  avg_tokens_per_request: number;
  max_tokens: number;
  min_tokens: number;
  total_requests: number;
  p50: number;
  p95: number;
  p99: number;
}

interface PredictionDistribution {
  fraud_count: number;
  legitimate_count: number;
  fraud_rate: number;
  avg_confidence: number;
}

interface DashboardData {
  timestamp: string;
  model_performance: ModelPerformance;
  latency: LatencyMetrics;
  errors: ErrorMetrics[];
  token_usage: TokenUsage;
  prediction_distribution: PredictionDistribution;
  drift_detection: any;
  system_health: {
    total_predictions: number;
    endpoints_monitored: number;
    error_count: number;
  };
}

export default function MonitoringDashboard() {
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [timeWindow, setTimeWindow] = useState(24); // hours
  const [isLoading, setIsLoading] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<string>('');

  const fetchMetrics = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`http://localhost:8000/api/v1/fraud/monitoring/metrics?time_window_hours=${timeWindow}`);
      const data = await response.json();
      setDashboardData(data);
      setLastUpdate(new Date().toLocaleTimeString());
    } catch (error) {
      console.error('Failed to fetch metrics:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, [timeWindow]);

  if (!dashboardData) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <Activity className="h-12 w-12 mx-auto mb-4 animate-pulse text-muted-foreground" />
          <p className="text-muted-foreground">Loading monitoring data...</p>
        </div>
      </div>
    );
  }

  const { model_performance, latency, errors, token_usage, prediction_distribution, system_health } = dashboardData;

  // Prepare confusion matrix data
  const confusionMatrixData = [
    { name: 'True Positive', value: model_performance.true_positives, color: '#10b981' },
    { name: 'True Negative', value: model_performance.true_negatives, color: '#3b82f6' },
    { name: 'False Positive', value: model_performance.false_positives, color: '#f59e0b' },
    { name: 'False Negative', value: model_performance.false_negatives, color: '#ef4444' },
  ];

  // Prepare prediction distribution data
  const predictionDistData = [
    { name: 'Fraud', value: prediction_distribution.fraud_count, color: '#ef4444' },
    { name: 'Legitimate', value: prediction_distribution.legitimate_count, color: '#10b981' },
  ];

  // Prepare latency data for chart
  const latencyChartData = Object.entries(latency).map(([endpoint, metrics]) => ({
    endpoint: endpoint.split('/').pop() || endpoint,
    p50: metrics.p50,
    p95: metrics.p95,
    p99: metrics.p99,
    mean: metrics.mean
  }));

  return (
    <div className="flex flex-col gap-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Monitoring & Observability</h1>
          <p className="text-muted-foreground mt-2">
            Real-time metrics, model performance, and system health monitoring
          </p>
        </div>
        <div className="flex items-center gap-4">
          <select
            value={timeWindow}
            onChange={(e) => setTimeWindow(parseInt(e.target.value))}
            className="border rounded-md px-3 py-2 text-sm"
          >
            <option value={1}>Last Hour</option>
            <option value={6}>Last 6 Hours</option>
            <option value={24}>Last 24 Hours</option>
            <option value={168}>Last Week</option>
          </select>
          <Badge variant="outline">
            Last updated: {lastUpdate}
          </Badge>
        </div>
      </div>

      {/* System Health Overview */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Predictions</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{system_health.total_predictions.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Fraud rate: {(prediction_distribution.fraud_rate * 100).toFixed(1)}%
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Endpoints Monitored</CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{system_health.endpoints_monitored}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Avg confidence: {(prediction_distribution.avg_confidence * 100).toFixed(1)}%
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Error Count</CardTitle>
            <AlertCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{system_health.error_count}</div>
            <p className="text-xs text-muted-foreground mt-1">
              {errors.length} error types
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs for different metric views */}
      <Tabs defaultValue="performance" className="space-y-4">
        <TabsList>
          <TabsTrigger value="performance">Model Performance</TabsTrigger>
          <TabsTrigger value="latency">Latency</TabsTrigger>
          <TabsTrigger value="tokens">Token Usage</TabsTrigger>
          <TabsTrigger value="predictions">Predictions</TabsTrigger>
        </TabsList>

        {/* Model Performance Tab */}
        <TabsContent value="performance" className="space-y-4">
          <div className="grid gap-6 md:grid-cols-2">
            {/* Metrics Cards */}
            <Card>
              <CardHeader>
                <CardTitle>Classification Metrics</CardTitle>
                <CardDescription>
                  {model_performance.total_predictions} labeled predictions
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">F1 Score</p>
                    <p className="text-3xl font-bold text-green-600">
                      {(model_performance.f1_score * 100).toFixed(1)}%
                    </p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Accuracy</p>
                    <p className="text-3xl font-bold text-blue-600">
                      {(model_performance.accuracy * 100).toFixed(1)}%
                    </p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Precision</p>
                    <p className="text-2xl font-bold">
                      {(model_performance.precision * 100).toFixed(1)}%
                    </p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Recall</p>
                    <p className="text-2xl font-bold">
                      {(model_performance.recall * 100).toFixed(1)}%
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Confusion Matrix */}
            <Card>
              <CardHeader>
                <CardTitle>Confusion Matrix</CardTitle>
                <CardDescription>Prediction outcomes breakdown</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={250}>
                  <PieChart>
                    <Pie
                      data={confusionMatrixData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, value }) => `${name}: ${value}`}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {confusionMatrixData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Latency Tab */}
        <TabsContent value="latency" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Clock className="h-5 w-5" />
                Latency Percentiles by Endpoint
              </CardTitle>
              <CardDescription>Response time distribution (milliseconds)</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={400}>
                <BarChart data={latencyChartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="endpoint" angle={-45} textAnchor="end" height={100} />
                  <YAxis label={{ value: 'Latency (ms)', angle: -90, position: 'insideLeft' }} />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="p50" fill="#3b82f6" name="p50 (median)" />
                  <Bar dataKey="p95" fill="#f59e0b" name="p95" />
                  <Bar dataKey="p99" fill="#ef4444" name="p99" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Token Usage Tab */}
        <TabsContent value="tokens" className="space-y-4">
          <div className="grid gap-6 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Database className="h-5 w-5" />
                  LLM Token Usage
                </CardTitle>
                <CardDescription>{token_usage.total_requests} requests tracked</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Total Tokens</p>
                    <p className="text-2xl font-bold">{token_usage.total_tokens.toLocaleString()}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Avg/Request</p>
                    <p className="text-2xl font-bold">{Math.round(token_usage.avg_tokens_per_request)}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Min Tokens</p>
                    <p className="text-lg font-semibold">{token_usage.min_tokens}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Max Tokens</p>
                    <p className="text-lg font-semibold">{token_usage.max_tokens}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Token Percentiles</CardTitle>
                <CardDescription>Distribution of token usage</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">p50 (median)</span>
                    <span className="text-sm font-bold">{Math.round(token_usage.p50)} tokens</span>
                  </div>
                  <div className="h-2 bg-gray-200 rounded-full">
                    <div className="h-full bg-blue-500 rounded-full" style={{ width: `${(token_usage.p50 / token_usage.max_tokens) * 100}%` }} />
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">p95</span>
                    <span className="text-sm font-bold">{Math.round(token_usage.p95)} tokens</span>
                  </div>
                  <div className="h-2 bg-gray-200 rounded-full">
                    <div className="h-full bg-orange-500 rounded-full" style={{ width: `${(token_usage.p95 / token_usage.max_tokens) * 100}%` }} />
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">p99</span>
                    <span className="text-sm font-bold">{Math.round(token_usage.p99)} tokens</span>
                  </div>
                  <div className="h-2 bg-gray-200 rounded-full">
                    <div className="h-full bg-red-500 rounded-full" style={{ width: `${(token_usage.p99 / token_usage.max_tokens) * 100}%` }} />
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Predictions Tab */}
        <TabsContent value="predictions" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Prediction Distribution</CardTitle>
              <CardDescription>
                {prediction_distribution.fraud_count + prediction_distribution.legitimate_count} total predictions
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-6 md:grid-cols-2">
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={predictionDistData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, value, percent }) => `${name}: ${value} (${(percent * 100).toFixed(0)}%)`}
                      outerRadius={100}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {predictionDistData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>

                <div className="space-y-4">
                  <div className="rounded-lg border p-4 bg-red-50 dark:bg-red-950/20">
                    <p className="text-sm text-muted-foreground mb-1">Fraud Predictions</p>
                    <p className="text-3xl font-bold text-red-600">
                      {prediction_distribution.fraud_count}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {(prediction_distribution.fraud_rate * 100).toFixed(2)}% of total
                    </p>
                  </div>

                  <div className="rounded-lg border p-4 bg-green-50 dark:bg-green-950/20">
                    <p className="text-sm text-muted-foreground mb-1">Legitimate Predictions</p>
                    <p className="text-3xl font-bold text-green-600">
                      {prediction_distribution.legitimate_count}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {((1 - prediction_distribution.fraud_rate) * 100).toFixed(2)}% of total
                    </p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
