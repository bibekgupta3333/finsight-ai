'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

// Mock data - will be replaced with real data from API
const fraudTrendData = [
  { month: 'Jan', frauds: 24, total: 1000, rate: 2.4 },
  { month: 'Feb', frauds: 18, total: 950, rate: 1.9 },
  { month: 'Mar', frauds: 32, total: 1100, rate: 2.9 },
  { month: 'Apr', frauds: 28, total: 1050, rate: 2.7 },
  { month: 'May', frauds: 22, total: 980, rate: 2.2 },
  { month: 'Jun', frauds: 35, total: 1200, rate: 2.9 },
];

const riskDistribution = [
  { name: 'Low (0-30)', value: 650, color: '#22c55e' },
  { name: 'Medium (31-70)', value: 280, color: '#eab308' },
  { name: 'High (71-100)', value: 70, color: '#ef4444' },
];

const transactionTypeData = [
  { type: 'PAYMENT', approved: 450, blocked: 12, reviewed: 38 },
  { type: 'TRANSFER', approved: 280, blocked: 25, reviewed: 45 },
  { type: 'CASH_OUT', approved: 180, blocked: 32, reviewed: 28 },
  { type: 'DEBIT', approved: 320, blocked: 8, reviewed: 22 },
  { type: 'CASH_IN', approved: 210, blocked: 5, reviewed: 15 },
];

const confidenceData = [
  { range: '0-20%', count: 15 },
  { range: '21-40%', count: 45 },
  { range: '41-60%', count: 120 },
  { range: '61-80%', count: 280 },
  { range: '81-100%', count: 540 },
];

export function FraudTrendChart() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Fraud Detection Trends</CardTitle>
        <CardDescription>Monthly fraud rate over time</CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={fraudTrendData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="month" />
            <YAxis yAxisId="left" />
            <YAxis yAxisId="right" orientation="right" />
            <Tooltip />
            <Legend />
            <Area
              yAxisId="left"
              type="monotone"
              dataKey="frauds"
              stroke="#ef4444"
              fill="#ef4444"
              fillOpacity={0.6}
              name="Frauds Detected"
            />
            <Area
              yAxisId="right"
              type="monotone"
              dataKey="rate"
              stroke="#3b82f6"
              fill="#3b82f6"
              fillOpacity={0.3}
              name="Fraud Rate (%)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

export function RiskDistributionChart() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Risk Score Distribution</CardTitle>
        <CardDescription>Transaction risk categories</CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={riskDistribution}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={({ name, percent }) => `${name}: ${((percent || 0) * 100).toFixed(0)}%`}
              outerRadius={100}
              fill="#8884d8"
              dataKey="value"
            >
              {riskDistribution.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

export function TransactionTypeChart() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Decisions by Transaction Type</CardTitle>
        <CardDescription>Approval, review, and block rates</CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={transactionTypeData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="type" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey="approved" stackId="a" fill="#22c55e" name="Approved" />
            <Bar dataKey="reviewed" stackId="a" fill="#eab308" name="Reviewed" />
            <Bar dataKey="blocked" stackId="a" fill="#ef4444" name="Blocked" />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

export function ConfidenceDistributionChart() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Confidence Score Distribution</CardTitle>
        <CardDescription>Model confidence levels</CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={confidenceData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="range" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Line
              type="monotone"
              dataKey="count"
              stroke="#3b82f6"
              strokeWidth={2}
              name="Transactions"
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
