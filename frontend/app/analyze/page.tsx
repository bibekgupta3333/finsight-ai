'use client';

import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import { Upload, FileText, AlertCircle, CheckCircle2, XCircle } from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import type { Transaction, FraudAnalysisResult } from '@/lib/types';

export default function AnalyzePage() {
  const [file, setFile] = useState<File | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [results, setResults] = useState<FraudAnalysisResult[]>([]);
  const [error, setError] = useState<string | null>(null);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      setFile(acceptedFiles[0]);
      setError(null);
      setResults([]);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'application/pdf': ['.pdf'],
    },
    multiple: false,
  });

  const parseCSV = (text: string): Transaction[] => {
    const lines = text.trim().split('\n');
    const headers = lines[0].split(',');
    
    return lines.slice(1).map((line) => {
      const values = line.split(',');
      return {
        step: parseInt(values[0]) || 0,
        type: values[1] || '',
        amount: parseFloat(values[2]) || 0,
        nameOrig: values[3] || '',
        oldbalanceOrg: parseFloat(values[4]) || 0,
        newbalanceOrig: parseFloat(values[5]) || 0,
        nameDest: values[6] || '',
        oldbalanceDest: parseFloat(values[7]) || 0,
        newbalanceDest: parseFloat(values[8]) || 0,
        isFraud: parseInt(values[9]) || 0,
        isFlaggedFraud: parseInt(values[10]) || 0,
      };
    });
  };

  const analyzeFile = async () => {
    if (!file) return;

    setAnalyzing(true);
    setError(null);
    setProgress(0);

    try {
      const text = await file.text();
      const transactions = parseCSV(text);

      if (transactions.length === 0) {
        throw new Error('No valid transactions found in CSV');
      }

      // Analyze transactions (limit to first 10 for demo)
      const transactionsToAnalyze = transactions.slice(0, 10);
      const analysisResults: FraudAnalysisResult[] = [];

      for (let i = 0; i < transactionsToAnalyze.length; i++) {
        const result = await apiClient.analyzeFraud(transactionsToAnalyze[i]);
        analysisResults.push(result);
        setProgress(((i + 1) / transactionsToAnalyze.length) * 100);
      }

      setResults(analysisResults);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed');
    } finally {
      setAnalyzing(false);
    }
  };

  const getDecisionColor = (decision: string) => {
    switch (decision) {
      case 'APPROVE':
        return 'bg-green-500';
      case 'REVIEW':
        return 'bg-yellow-500';
      case 'BLOCK':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getDecisionIcon = (decision: string) => {
    switch (decision) {
      case 'APPROVE':
        return <CheckCircle2 className="h-4 w-4" />;
      case 'REVIEW':
        return <AlertCircle className="h-4 w-4" />;
      case 'BLOCK':
        return <XCircle className="h-4 w-4" />;
      default:
        return null;
    }
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-zinc-900 dark:text-zinc-50 mb-2">
          Fraud Analysis
        </h1>
        <p className="text-lg text-zinc-600 dark:text-zinc-400">
          Upload CSV or PDF files to analyze transactions for fraudulent activity
        </p>
      </div>

      {/* File Upload */}
      <Card className="mb-8">
        <CardHeader>
          <CardTitle>Upload Transactions</CardTitle>
          <CardDescription>
            Upload a CSV file with transaction data or a PDF document for analysis
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors ${
              isDragActive
                ? 'border-blue-500 bg-blue-50 dark:bg-blue-950'
                : 'border-zinc-300 dark:border-zinc-700 hover:border-blue-400'
            }`}
          >
            <input {...getInputProps()} />
            <Upload className="h-12 w-12 mx-auto mb-4 text-zinc-400" />
            {isDragActive ? (
              <p className="text-lg font-medium">Drop the file here...</p>
            ) : (
              <>
                <p className="text-lg font-medium mb-2">
                  Drag & drop a file here, or click to select
                </p>
                <p className="text-sm text-zinc-500 dark:text-zinc-400">
                  Supports CSV and PDF files
                </p>
              </>
            )}
          </div>

          {file && (
            <div className="mt-4 flex items-center justify-between p-4 bg-zinc-100 dark:bg-zinc-800 rounded-lg">
              <div className="flex items-center gap-3">
                <FileText className="h-8 w-8 text-blue-600" />
                <div>
                  <p className="font-medium">{file.name}</p>
                  <p className="text-sm text-zinc-500">
                    {(file.size / 1024).toFixed(2)} KB
                  </p>
                </div>
              </div>
              <Button onClick={analyzeFile} disabled={analyzing}>
                {analyzing ? 'Analyzing...' : 'Analyze'}
              </Button>
            </div>
          )}

          {analyzing && (
            <div className="mt-4">
              <Progress value={progress} className="mb-2" />
              <p className="text-sm text-center text-zinc-600 dark:text-zinc-400">
                Analyzing transactions... {Math.round(progress)}%
              </p>
            </div>
          )}

          {error && (
            <Alert variant="destructive" className="mt-4">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Results */}
      {results.length > 0 && (
        <div>
          <h2 className="text-2xl font-bold mb-4">Analysis Results</h2>
          <div className="grid gap-4">
            {results.map((result, index) => (
              <Card key={index}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg">Transaction #{index + 1}</CardTitle>
                    <Badge className={getDecisionColor(result.decision)}>
                      <div className="flex items-center gap-1">
                        {getDecisionIcon(result.decision)}
                        {result.decision}
                      </div>
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid gap-4 md:grid-cols-2">
                    <div>
                      <p className="text-sm font-medium text-zinc-500 dark:text-zinc-400">
                        Risk Score
                      </p>
                      <p className="text-2xl font-bold">{result.risk_score.toFixed(1)}/100</p>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-zinc-500 dark:text-zinc-400">
                        Confidence
                      </p>
                      <p className="text-2xl font-bold">
                        {(result.confidence * 100).toFixed(1)}%
                      </p>
                    </div>
                  </div>

                  <div className="mt-4">
                    <p className="text-sm font-medium text-zinc-500 dark:text-zinc-400 mb-2">
                      Reasoning
                    </p>
                    <p className="text-sm">{result.reasoning}</p>
                  </div>

                  {result.anomalies && result.anomalies.length > 0 && (
                    <div className="mt-4">
                      <p className="text-sm font-medium text-zinc-500 dark:text-zinc-400 mb-2">
                        Anomalies Detected
                      </p>
                      <ul className="list-disc list-inside space-y-1">
                        {result.anomalies.map((anomaly, i) => (
                          <li key={i} className="text-sm text-red-600 dark:text-red-400">
                            {anomaly}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
