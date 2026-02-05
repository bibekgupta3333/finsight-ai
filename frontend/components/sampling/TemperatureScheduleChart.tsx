'use client';

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { TrendingUp } from 'lucide-react';

type ScheduleType = 'static' | 'linear' | 'exponential' | 'cosine' | 'adaptive';

interface ScheduleData {
  schedule_type: string;
  initial_temp: number;
  final_temp: number;
  steps: number;
  temperatures: number[];
}

const SCHEDULE_TYPES: Record<ScheduleType, { label: string; description: string }> = {
  static: { label: 'Static', description: 'Constant temperature' },
  linear: { label: 'Linear', description: 'Linear interpolation' },
  exponential: { label: 'Exponential', description: 'Exponential decay/growth' },
  cosine: { label: 'Cosine', description: 'Cosine annealing' },
  adaptive: { label: 'Adaptive', description: 'Sine wave pattern' },
};

export function TemperatureScheduleChart() {
  const [scheduleType, setScheduleType] = useState<ScheduleType>('linear');
  const [initialTemp, setInitialTemp] = useState(0.8);
  const [finalTemp, setFinalTemp] = useState(0.3);
  const [steps, setSteps] = useState(10);
  const [scheduleData, setScheduleData] = useState<ScheduleData | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleGenerate = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('http://localhost:8000/api/v1/fraud/research/sampling/schedule', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          schedule_type: scheduleType,
          initial_temp: initialTemp,
          final_temp: finalTemp,
          steps,
        }),
      });
      const data = await response.json();
      setScheduleData(data);
    } catch (error) {
      console.error('Failed to generate schedule:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const chartData = scheduleData?.temperatures.map((temp, idx) => ({
    step: idx + 1,
    temperature: parseFloat(temp.toFixed(3)),
  })) || [];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <TrendingUp className="h-5 w-5" />
          Temperature Schedule
        </CardTitle>
        <CardDescription>
          Adaptive temperature scheduling for multi-step reasoning
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Configuration */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <div className="space-y-2">
            <Label htmlFor="schedule-type">Schedule Type</Label>
            <Select value={scheduleType} onValueChange={(value) => setScheduleType(value as ScheduleType)}>
              <SelectTrigger id="schedule-type" className="bg-background">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-white dark:bg-gray-950 border shadow-lg z-50">
                {Object.entries(SCHEDULE_TYPES).map(([key, { label }]) => (
                  <SelectItem key={key} value={key} className="bg-white dark:bg-gray-950">
                    {label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">{SCHEDULE_TYPES[scheduleType].description}</p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="initial-temp">Initial Temp</Label>
            <Input
              id="initial-temp"
              type="number"
              step="0.1"
              min="0"
              max="2"
              value={initialTemp}
              onChange={(e) => setInitialTemp(parseFloat(e.target.value))}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="final-temp">Final Temp</Label>
            <Input
              id="final-temp"
              type="number"
              step="0.1"
              min="0"
              max="2"
              value={finalTemp}
              onChange={(e) => setFinalTemp(parseFloat(e.target.value))}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="steps">Steps</Label>
            <Input
              id="steps"
              type="number"
              min="2"
              max="100"
              value={steps}
              onChange={(e) => setSteps(parseInt(e.target.value))}
            />
          </div>
        </div>

        <Button onClick={handleGenerate} disabled={isLoading} className="w-full">
          {isLoading ? 'Generating...' : 'Generate Schedule'}
        </Button>

        {/* Chart */}
        {chartData.length > 0 && (
          <div className="mt-6">
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis
                  dataKey="step"
                  label={{ value: 'Step', position: 'insideBottom', offset: -5 }}
                  stroke="#6b7280"
                />
                <YAxis
                  label={{ value: 'Temperature', angle: -90, position: 'insideLeft' }}
                  domain={[0, 2]}
                  stroke="#6b7280"
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'white',
                    border: '1px solid #e5e7eb',
                    borderRadius: '6px'
                  }}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="temperature"
                  stroke="#8b5cf6"
                  strokeWidth={2}
                  dot={{ fill: '#8b5cf6', r: 4 }}
                  activeDot={{ r: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>

            {/* Stats */}
            <div className="mt-4 grid grid-cols-3 gap-4 text-center">
              <div className="rounded-lg border p-3">
                <p className="text-xs text-muted-foreground">Min Temp</p>
                <p className="text-lg font-semibold">{Math.min(...scheduleData!.temperatures).toFixed(3)}</p>
              </div>
              <div className="rounded-lg border p-3">
                <p className="text-xs text-muted-foreground">Max Temp</p>
                <p className="text-lg font-semibold">{Math.max(...scheduleData!.temperatures).toFixed(3)}</p>
              </div>
              <div className="rounded-lg border p-3">
                <p className="text-xs text-muted-foreground">Avg Temp</p>
                <p className="text-lg font-semibold">
                  {(scheduleData!.temperatures.reduce((a, b) => a + b, 0) / scheduleData!.temperatures.length).toFixed(3)}
                </p>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
