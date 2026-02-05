'use client';

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Loader2, AlertCircle, CheckCircle } from 'lucide-react';
import { RiskGauge } from './risk-gauge';
import { DecisionBadge } from './decision-badge';
import type { Transaction, FraudAnalysisResult } from '@/lib/types';

type ReasoningPattern = 'react' | 'cot' | 'tot' | 'debate' | 'self-critique' | 'reflection';

interface TransactionAnalyzerProps {
  onAnalysisComplete?: (result: FraudAnalysisResult) => void;
  selectedPattern?: ReasoningPattern;
  onPatternChange?: (pattern: ReasoningPattern) => void;
}

const TRANSACTION_TYPES = ['PAYMENT', 'TRANSFER', 'CASH_OUT', 'DEBIT', 'CASH_IN'];

const REASONING_PATTERNS = [
  { value: 'react', label: 'ReAct', description: 'Reasoning + Acting' },
  { value: 'cot', label: 'Chain-of-Thought', description: 'Step-by-step reasoning' },
  { value: 'tot', label: 'Tree-of-Thought', description: 'Multi-path exploration' },
  { value: 'debate', label: 'Debate', description: 'Prosecutor vs Defense' },
  { value: 'self-critique', label: 'Self-Critique', description: 'Generate → Critique → Revise' },
  { value: 'reflection', label: 'Reflection', description: 'Policy validation' },
] as const;

export function TransactionAnalyzer({
  onAnalysisComplete,
  selectedPattern = 'react',
  onPatternChange
}: TransactionAnalyzerProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<FraudAnalysisResult | null>(null);

  // Form state
  const [formData, setFormData] = useState({
    type: 'TRANSFER',
    amount: '9000',
    oldbalanceOrg: '10000',
    newbalanceOrig: '1000',
    oldbalanceDest: '0',
    newbalanceDest: '9000',
  });

  const handleInputChange = (field: string, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleAnalyze = async () => {
    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const transaction: Transaction = {
        transaction_id: `TXN-${Date.now()}`,
        type: formData.type,
        amount: parseFloat(formData.amount),
        oldbalanceOrg: parseFloat(formData.oldbalanceOrg),
        newbalanceOrig: parseFloat(formData.newbalanceOrig),
        oldbalanceDest: parseFloat(formData.oldbalanceDest),
        newbalanceDest: parseFloat(formData.newbalanceDest),
        timestamp: new Date().toISOString(),
      };

      const response = await fetch(`http://localhost:8000/api/v1/fraud/analyze/${selectedPattern}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ transaction }),
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      const rawData = await response.json();

      // Pattern-specific endpoints return wrapped data: { pattern: string, result: {...} }
      // Regular endpoint returns FraudAnalysisResult directly
      let data: FraudAnalysisResult;

      if (rawData.pattern) {
        // Pattern endpoint response - extract result and transform to FraudAnalysisResult
        let parsedResult = rawData.result;

        // If decision is a JSON string, parse it
        if (typeof parsedResult.decision === 'string') {
          try {
            parsedResult.decision = JSON.parse(parsedResult.decision);
          } catch (e) {
            // Keep as string if parsing fails
          }
        }

        const decision = parsedResult.decision || {};
        const resultData = typeof decision === 'object' ? decision : parsedResult;

        data = {
          transaction_id: transaction.transaction_id,
          prediction: {
            is_fraud: resultData.is_fraud ?? parsedResult.is_fraud ?? false,
            risk_score: resultData.risk_score ?? parsedResult.risk_score ?? 0,
            risk_level: resultData.risk_level ?? parsedResult.risk_level ?? 'LOW',
            confidence: resultData.confidence ?? parsedResult.confidence ?? 0,
            explanation: resultData.reasoning ?? resultData.explanation ?? parsedResult.reasoning ?? parsedResult.explanation ?? 'No explanation provided',
            factors: resultData.factors ?? resultData.evidence ?? parsedResult.factors ?? null,
            reasoning_steps: parsedResult.reasoning_trace ?? parsedResult.trace?.map((t: any) => `${t.thought || ''} ${t.action || ''} ${t.observation || ''}`.trim()) ?? null,
          },
          processing_time_ms: 0,
          timestamp: new Date().toISOString(),
          metadata: {
            pattern: rawData.pattern,
            steps_taken: rawData.steps_taken,
            reasoning_steps: rawData.reasoning_steps,
            paths_explored: rawData.paths_explored,
            debate_rounds: rawData.debate_rounds,
            revisions: rawData.revisions,
          },
        };
      } else {
        // Regular endpoint response
        data = rawData as FraudAnalysisResult;
      }

      setResult(data);
      onAnalysisComplete?.(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed');
    } finally {
      setIsLoading(false);
    }
  };

  const handleLoadExample = (exampleType: 'fraud' | 'legitimate') => {
    if (exampleType === 'fraud') {
      setFormData({
        type: 'TRANSFER',
        amount: '9000',
        oldbalanceOrg: '10000',
        newbalanceOrig: '1000',
        oldbalanceDest: '0',
        newbalanceDest: '9000',
      });
    } else {
      setFormData({
        type: 'PAYMENT',
        amount: '150',
        oldbalanceOrg: '5000',
        newbalanceOrig: '4850',
        oldbalanceDest: '1000',
        newbalanceDest: '1150',
      });
    }
  };

  return (
    <div className="grid gap-6 md:grid-cols-2">
      {/* Left Column: Input Form */}
      <Card>
        <CardHeader>
          <CardTitle>Transaction Input</CardTitle>
          <CardDescription>Enter transaction details for fraud analysis</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Reasoning Pattern Selector */}
          <div className="space-y-2">
            <Label htmlFor="pattern">AI Reasoning Pattern</Label>
            <Select
              value={selectedPattern}
              onValueChange={(value) => onPatternChange?.(value as ReasoningPattern)}
            >
              <SelectTrigger id="pattern" className="bg-background">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-white dark:bg-gray-950 border shadow-lg z-50">
                {REASONING_PATTERNS.map((pattern) => (
                  <SelectItem key={pattern.value} value={pattern.value} className="bg-white dark:bg-gray-950 hover:bg-gray-100 dark:hover:bg-gray-800">
                    {pattern.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              {REASONING_PATTERNS.find(p => p.value === selectedPattern)?.description}
            </p>
          </div>

          {/* Transaction Type */}
          <div className="space-y-2">
            <Label htmlFor="type">Transaction Type</Label>
            <Select value={formData.type} onValueChange={(value) => handleInputChange('type', value)}>
              <SelectTrigger id="type">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {TRANSACTION_TYPES.map((type) => (
                  <SelectItem key={type} value={type}>
                    {type}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Amount */}
          <div className="space-y-2">
            <Label htmlFor="amount">Amount ($)</Label>
            <Input
              id="amount"
              type="number"
              step="0.01"
              value={formData.amount}
              onChange={(e) => handleInputChange('amount', e.target.value)}
              placeholder="0.00"
            />
          </div>

          {/* Origin Balances */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="oldbalanceOrg">Old Balance (Origin)</Label>
              <Input
                id="oldbalanceOrg"
                type="number"
                step="0.01"
                value={formData.oldbalanceOrg}
                onChange={(e) => handleInputChange('oldbalanceOrg', e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="newbalanceOrig">New Balance (Origin)</Label>
              <Input
                id="newbalanceOrig"
                type="number"
                step="0.01"
                value={formData.newbalanceOrig}
                onChange={(e) => handleInputChange('newbalanceOrig', e.target.value)}
              />
            </div>
          </div>

          {/* Destination Balances */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="oldbalanceDest">Old Balance (Dest)</Label>
              <Input
                id="oldbalanceDest"
                type="number"
                step="0.01"
                value={formData.oldbalanceDest}
                onChange={(e) => handleInputChange('oldbalanceDest', e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="newbalanceDest">New Balance (Dest)</Label>
              <Input
                id="newbalanceDest"
                type="number"
                step="0.01"
                value={formData.newbalanceDest}
                onChange={(e) => handleInputChange('newbalanceDest', e.target.value)}
              />
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-2 pt-4">
            <Button onClick={handleAnalyze} disabled={isLoading} className="flex-1">
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Analyzing...
                </>
              ) : (
                'Analyze Transaction'
              )}
            </Button>
          </div>

          {/* Example Buttons */}
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleLoadExample('fraud')}
              className="flex-1"
            >
              Load Fraud Example
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleLoadExample('legitimate')}
              className="flex-1"
            >
              Load Legitimate Example
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Right Column: Results */}
      <Card>
        <CardHeader>
          <CardTitle>Analysis Results</CardTitle>
          <CardDescription>Real-time fraud detection analysis</CardDescription>
        </CardHeader>
        <CardContent>
          {error && (
            <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">
              <AlertCircle className="h-5 w-5" />
              <p className="text-sm font-medium">{error}</p>
            </div>
          )}

          {!result && !error && !isLoading && (
            <div className="flex min-h-[300px] items-center justify-center text-center text-muted-foreground">
              <p>Enter transaction details and click "Analyze" to detect fraud</p>
            </div>
          )}

          {isLoading && (
            <div className="flex min-h-[300px] items-center justify-center">
              <div className="text-center">
                <Loader2 className="mx-auto h-8 w-8 animate-spin text-primary" />
                <p className="mt-4 text-sm text-muted-foreground">Analyzing transaction...</p>
              </div>
            </div>
          )}

          {result && (
            <div className="space-y-6">
              {/* Decision Badge */}
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Decision</p>
                  <DecisionBadge isFraud={result.prediction.is_fraud} size="lg" />
                </div>
                <div className="text-right">
                  <p className="text-sm text-muted-foreground">Processing Time</p>
                  <p className="text-lg font-semibold">{result.processing_time_ms}ms</p>
                </div>
              </div>

              {/* Risk Score */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label>Risk Score</Label>
                  <span className="text-2xl font-bold">{result.prediction.risk_score.toFixed(1)}</span>
                </div>
                <RiskGauge value={result.prediction.risk_score} size="lg" showLabel />
              </div>

              {/* Confidence */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label>Confidence</Label>
                  <span className="text-lg font-semibold">
                    {(result.prediction.confidence * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full bg-blue-500 transition-all"
                    style={{ width: `${result.prediction.confidence * 100}%` }}
                  />
                </div>
              </div>

              {/* Explanation */}
              <div className="space-y-2">
                <Label>Explanation</Label>
                <div className="rounded-lg border bg-muted/50 p-4">
                  <p className="text-sm">{result.prediction.explanation}</p>
                </div>
              </div>

              {/* Risk Factors */}
              {result.prediction.factors && result.prediction.factors.length > 0 && (
                <div className="space-y-2">
                  <Label>Risk Factors</Label>
                  <ul className="space-y-2">
                    {result.prediction.factors.map((factor, index) => (
                      <li key={index} className="flex items-start gap-2 text-sm">
                        <AlertCircle className="mt-0.5 h-4 w-4 text-orange-500 flex-shrink-0" />
                        <span>{factor}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Success Indicator */}
              {!result.prediction.is_fraud && (
                <div className="flex items-center gap-2 rounded-lg border border-green-200 bg-green-50 p-4 text-green-800">
                  <CheckCircle className="h-5 w-5" />
                  <p className="text-sm font-medium">Transaction appears legitimate</p>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
