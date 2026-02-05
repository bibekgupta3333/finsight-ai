'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ZAxis } from 'recharts';
import { TrendingUp } from 'lucide-react';

interface ModelPoint {
  name: string;
  cost: number;
  performance: number;
  size: number;
}

const modelData: ModelPoint[] = [
  { name: 'GPT-4', cost: 100, performance: 95, size: 1000 },
  { name: 'GPT-3.5', cost: 60, performance: 85, size: 600 },
  { name: 'Distilled Model', cost: 25, performance: 82, size: 250 },
  { name: 'Small Model', cost: 10, performance: 70, size: 100 },
  { name: 'Hybrid (Optimal)', cost: 35, performance: 88, size: 400 },
];

const CustomTooltip = ({ active, payload }: { active?: boolean; payload?: { payload: ModelPoint }[] }) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-white dark:bg-gray-800 border rounded-lg shadow-lg p-3">
        <p className="font-semibold">{data.name}</p>
        <p className="text-xs text-muted-foreground mt-1">Cost: ${data.cost}</p>
        <p className="text-xs text-muted-foreground">Performance: {data.performance}%</p>
        <p className="text-xs text-muted-foreground">Size: {data.size}M params</p>
      </div>
    );
  }
  return null;
};

export function CostPerformanceChart() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <TrendingUp className="h-5 w-5" />
          Cost vs Performance Analysis
        </CardTitle>
        <CardDescription>
          Model trade-offs across cost and performance dimensions
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Scatter Plot */}
        <ResponsiveContainer width="100%" height={300}>
          <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              type="number"
              dataKey="cost"
              name="Cost"
              unit="$"
              label={{ value: 'Relative Cost ($)', position: 'insideBottom', offset: -10 }}
            />
            <YAxis
              type="number"
              dataKey="performance"
              name="Performance"
              unit="%"
              label={{ value: 'Performance (%)', angle: -90, position: 'insideLeft' }}
            />
            <ZAxis type="number" dataKey="size" range={[50, 400]} name="Size" />
            <Tooltip content={<CustomTooltip />} />
            <Legend />
            <Scatter
              name="Models"
              data={modelData}
              fill="#8b5cf6"
            />
          </ScatterChart>
        </ResponsiveContainer>

        {/* Model Comparison Table */}
        <div className="space-y-2">
          <h4 className="text-sm font-semibold">Model Comparison</h4>
          <div className="rounded-lg border overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 dark:bg-gray-900">
                <tr>
                  <th className="px-4 py-2 text-left font-medium">Model</th>
                  <th className="px-4 py-2 text-right font-medium">Cost</th>
                  <th className="px-4 py-2 text-right font-medium">Performance</th>
                  <th className="px-4 py-2 text-right font-medium">Efficiency</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {modelData.map((model) => {
                  const efficiency = (model.performance / model.cost).toFixed(2);
                  const isOptimal = model.name === 'Hybrid (Optimal)';
                  return (
                    <tr key={model.name} className={isOptimal ? 'bg-green-50 dark:bg-green-950/20' : ''}>
                      <td className="px-4 py-2 flex items-center gap-2">
                        {model.name}
                        {isOptimal && <Badge variant="secondary" className="text-xs">Optimal</Badge>}
                      </td>
                      <td className="px-4 py-2 text-right">${model.cost}</td>
                      <td className="px-4 py-2 text-right">{model.performance}%</td>
                      <td className="px-4 py-2 text-right font-semibold">{efficiency}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Pareto Frontier Insight */}
        <div className="rounded-lg bg-purple-50 dark:bg-purple-950/20 border border-purple-200 dark:border-purple-900 p-4">
          <h4 className="text-sm font-semibold mb-2 text-purple-900 dark:text-purple-100">Pareto Efficiency</h4>
          <p className="text-sm text-purple-800 dark:text-purple-200">
            The hybrid approach achieves the best cost-performance trade-off, sitting on the Pareto frontier.
            It delivers 88% of GPT-4&apos;s performance at only 35% of the cost by intelligently routing tasks.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
