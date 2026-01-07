'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { apiClient } from '@/lib/api-client';
import { TrendingUp, TrendingDown, Activity, AlertTriangle, DollarSign } from 'lucide-react';
import { formatCurrency, formatNumber, formatPercentage } from '@/lib/utils';

interface Stats {
  total_analyzed: number;
  fraud_detected: number;
  avg_processing_time_ms: number;
}

interface CategoryData {
  type: string;
  count: number;
  fraudCount: number;
  fraudRate: number;
  [key: string]: string | number; // Index signature for Recharts compatibility
}

export default function InsightsPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [categoryData, setCategoryData] = useState<CategoryData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      // Fetch statistics
      const statsData = await apiClient.getStats();
      setStats(statsData);

      // Mock category data (will be replaced with actual API call)
      const mockCategories: CategoryData[] = [
        { type: 'TRANSFER', count: 5320, fraudCount: 412, fraudRate: 0.077 },
        { type: 'CASH_OUT', count: 3840, fraudCount: 298, fraudRate: 0.078 },
        { type: 'PAYMENT', count: 12450, fraudCount: 86, fraudRate: 0.007 },
        { type: 'DEBIT', count: 1920, fraudCount: 12, fraudRate: 0.006 },
        { type: 'CASH_IN', count: 8760, fraudCount: 5, fraudRate: 0.001 },
      ];
      setCategoryData(mockCategories);
    } catch (error) {
      console.error('Failed to load insights data:', error);
    } finally {
      setLoading(false);
    }
  };

  const fraudRate = stats ? (stats.fraud_detected / stats.total_analyzed) * 100 : 0;

  const COLORS = ['#ef4444', '#f59e0b', '#3b82f6', '#10b981', '#6366f1'];

  // Mock trend data
  const trendData = [
    { time: '00:00', transactions: 120, fraud: 8 },
    { time: '04:00', transactions: 180, fraud: 15 },
    { time: '08:00', transactions: 340, fraud: 28 },
    { time: '12:00', transactions: 520, fraud: 42 },
    { time: '16:00', transactions: 480, fraud: 38 },
    { time: '20:00', transactions: 280, fraud: 22 },
  ];

  return (
    <div className="container mx-auto space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Insights & Analytics</h1>
        <p className="text-muted-foreground">
          Comprehensive fraud detection statistics and trends
        </p>
      </div>

      {/* Key Metrics */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Analyzed</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats ? formatNumber(stats.total_analyzed) : '-'}
            </div>
            <p className="text-xs text-muted-foreground">All-time transactions</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Fraud Detected</CardTitle>
            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-destructive">
              {stats ? formatNumber(stats.fraud_detected) : '-'}
            </div>
            <p className="text-xs text-muted-foreground">
              {fraudRate > 0 ? `${fraudRate.toFixed(2)}% fraud rate` : 'No fraud detected'}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Processing Time</CardTitle>
            <TrendingDown className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats ? `${stats.avg_processing_time_ms.toFixed(1)}ms` : '-'}
            </div>
            <p className="text-xs text-muted-foreground">Per transaction</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Risk Score Avg</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">32.5</div>
            <p className="text-xs text-muted-foreground">Out of 100</p>
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <Tabs defaultValue="trends" className="space-y-4">
        <TabsList>
          <TabsTrigger value="trends">Trends</TabsTrigger>
          <TabsTrigger value="categories">Categories</TabsTrigger>
          <TabsTrigger value="distribution">Distribution</TabsTrigger>
        </TabsList>

        <TabsContent value="trends" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Transaction & Fraud Trends</CardTitle>
              <CardDescription>24-hour transaction volume and fraud detection</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={350}>
                <LineChart data={trendData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="transactions"
                    stroke="#3b82f6"
                    name="Transactions"
                  />
                  <Line type="monotone" dataKey="fraud" stroke="#ef4444" name="Fraud Detected" />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="categories" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Fraud by Transaction Type</CardTitle>
              <CardDescription>Breakdown of fraud cases by category</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={350}>
                <BarChart data={categoryData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="type" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="count" fill="#3b82f6" name="Total Transactions" />
                  <Bar dataKey="fraudCount" fill="#ef4444" name="Fraud Detected" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Category Statistics</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {categoryData.map((category) => (
                  <div key={category.type} className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Badge variant="outline">{category.type}</Badge>
                      <div className="text-sm">
                        <div className="font-medium">{formatNumber(category.count)} transactions</div>
                        <div className="text-muted-foreground">
                          {category.fraudCount} fraud ({formatPercentage(category.fraudRate)})
                        </div>
                      </div>
                    </div>
                    <div className="h-2 w-32 overflow-hidden rounded-full bg-muted">
                      <div
                        className="h-full bg-destructive"
                        style={{ width: `${category.fraudRate * 100}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="distribution" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Transaction Type Distribution</CardTitle>
              <CardDescription>Proportion of each transaction type</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={350}>
                <PieChart>
                  <Pie
                    data={categoryData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={(entry: any) => entry.type}
                    outerRadius={120}
                    fill="#8884d8"
                    dataKey="count"
                  >
                    {categoryData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
