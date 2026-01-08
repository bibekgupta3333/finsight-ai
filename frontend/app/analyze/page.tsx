'use client';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { useBatchAnalysis, useFraudAnalysis } from '@/hooks/use-fraud-analysis';
import { exportToCSV, exportToPDF } from '@/lib/export-utils';
import type { FraudAnalysisResult, Transaction, CSVTransaction } from '@/lib/types';
import { csvTransactionSchema } from '@/lib/validations';
import { AlertCircle, CheckCircle2, Download, FileDown, FileText, Upload, XCircle } from 'lucide-react';
import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';

export default function AnalyzePage() {
  const [file, setFile] = useState<File | null>(null);
  const [progress, setProgress] = useState(0);
  const [results, setResults] = useState<FraudAnalysisResult[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Use React Query mutation hooks
  const fraudAnalysis = useFraudAnalysis();
  const batchAnalysis = useBatchAnalysis();

  const analyzing = fraudAnalysis.isPending || batchAnalysis.isPending;

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

  const parseCSV = (text: string): CSVTransaction[] => {
    const lines = text.trim().split('\n');
    const headers = lines[0].split(',');

    return lines.slice(1).map((line) => {
      const values = line.split(',');
      const transaction = {
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

      // Validate with Zod
      return csvTransactionSchema.parse(transaction);
    });
  };

  // Transform CSV transaction to API format
  const transformToAPITransaction = (csvTx: CSVTransaction): Transaction => {
    // Generate unique transaction ID from step and account info
    const transactionId = `TX_${csvTx.step}_${csvTx.nameOrig.substring(1, 7)}`;

    return {
      transaction_id: transactionId,
      type: csvTx.type,
      amount: csvTx.amount,
      oldbalanceOrg: csvTx.oldbalanceOrg,
      newbalanceOrig: csvTx.newbalanceOrig,
      oldbalanceDest: csvTx.oldbalanceDest,
      newbalanceDest: csvTx.newbalanceDest,
      nameOrig: csvTx.nameOrig,
      nameDest: csvTx.nameDest,
      timestamp: new Date().toISOString(),
    };
  };

  const analyzeFile = async () => {
    if (!file) return;

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
        // Transform CSV transaction to API format
        const apiTransaction = transformToAPITransaction(transactionsToAnalyze[i]);
        const result = await fraudAnalysis.mutateAsync(apiTransaction);
        analysisResults.push(result);
        setProgress(((i + 1) / transactionsToAnalyze.length) * 100);
      }

      setResults(analysisResults);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed');
    }
  };

  const getDecisionColor = (risk_level: string) => {
    switch (risk_level) {
      case 'LOW':
        return 'bg-green-500';
      case 'MEDIUM':
        return 'bg-yellow-500';
      case 'HIGH':
      case 'CRITICAL':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getDecisionIcon = (risk_level: string) => {
    switch (risk_level) {
      case 'LOW':
        return <CheckCircle2 className="h-4 w-4" />;
      case 'MEDIUM':
        return <AlertCircle className="h-4 w-4" />;
      case 'HIGH':
      case 'CRITICAL':
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
          <div className="mt-4 p-4 bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800 rounded-lg">
            <p className="text-sm font-medium text-blue-900 dark:text-blue-100 mb-2">
              📥 Sample Test Files
            </p>
            <p className="text-xs text-blue-700 dark:text-blue-300 mb-3">
              Download sample CSV files to test the fraud detection system:
            </p>
            <div className="flex flex-wrap gap-2">
              <a
                href="https://raw.githubusercontent.com/bibekgupta3333/finsight-ai/main/data/samples/sample_transactions_small.csv"
                download
                className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-blue-700 dark:text-blue-300 bg-white dark:bg-blue-900/50 border border-blue-300 dark:border-blue-700 rounded hover:bg-blue-50 dark:hover:bg-blue-900 transition-colors"
              >
                <Download className="h-3 w-3" />
                Small (25 rows)
              </a>
              <a
                href="https://raw.githubusercontent.com/bibekgupta3333/finsight-ai/main/data/samples/sample_transactions_normal.csv"
                download
                className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-blue-700 dark:text-blue-300 bg-white dark:bg-blue-900/50 border border-blue-300 dark:border-blue-700 rounded hover:bg-blue-50 dark:hover:bg-blue-900 transition-colors"
              >
                <Download className="h-3 w-3" />
                Normal (20 rows)
              </a>
              <a
                href="https://raw.githubusercontent.com/bibekgupta3333/finsight-ai/main/data/samples/sample_transactions_fraudulent.csv"
                download
                className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-blue-700 dark:text-blue-300 bg-white dark:bg-blue-900/50 border border-blue-300 dark:border-blue-700 rounded hover:bg-blue-50 dark:hover:bg-blue-900 transition-colors"
              >
                <Download className="h-3 w-3" />
                Fraudulent (20 rows)
              </a>
              <a
                href="https://raw.githubusercontent.com/bibekgupta3333/finsight-ai/main/data/samples/sample_transactions_edge_cases.csv"
                download
                className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-blue-700 dark:text-blue-300 bg-white dark:bg-blue-900/50 border border-blue-300 dark:border-blue-700 rounded hover:bg-blue-50 dark:hover:bg-blue-900 transition-colors"
              >
                <Download className="h-3 w-3" />
                Edge Cases (20 rows)
              </a>
            </div>
          </div>
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
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-2xl font-bold">Analysis Results</h2>
            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={() => exportToCSV(results)}
                className="gap-2"
              >
                <Download className="h-4 w-4" />
                Export CSV
              </Button>
              <Button
                variant="outline"
                onClick={() => exportToPDF(results)}
                className="gap-2"
              >
                <FileDown className="h-4 w-4" />
                Export PDF
              </Button>
            </div>
          </div>
          <div className="grid gap-4">
            {results.map((result, index) => (
              <Card key={index}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg">Transaction #{index + 1}</CardTitle>
                    <Badge className={getDecisionColor(result.prediction.risk_level)}>
                      <div className="flex items-center gap-1">
                        {getDecisionIcon(result.prediction.risk_level)}
                        {result.prediction.risk_level}
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
                      <p className="text-2xl font-bold">{result.prediction.risk_score.toFixed(1)}/100</p>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-zinc-500 dark:text-zinc-400">
                        Confidence
                      </p>
                      <p className="text-2xl font-bold">
                        {(result.prediction.confidence * 100).toFixed(1)}%
                      </p>
                    </div>
                  </div>

                  <div className="mt-4">
                    <p className="text-sm font-medium text-zinc-500 dark:text-zinc-400 mb-2">
                      Explanation
                    </p>
                    <p className="text-sm">{result.prediction.explanation}</p>
                  </div>

                  {result.prediction.factors && result.prediction.factors.length > 0 && (
                    <div className="mt-4">
                      <p className="text-sm font-medium text-zinc-500 dark:text-zinc-400 mb-2">
                        Risk Factors
                      </p>
                      <ul className="list-disc list-inside space-y-1">
                        {result.prediction.factors.map((factor, i) => (
                          <li key={i} className="text-sm text-red-600 dark:text-red-400">
                            {factor}
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
