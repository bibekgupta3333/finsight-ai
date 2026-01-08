'use client';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useBatchAnalysis } from '@/hooks/use-fraud-analysis';
import { apiClient } from '@/lib/api-client';
import { exportToCSV, parseCSVFile } from '@/lib/export-utils';
import type { CSVTransaction, FraudAnalysisResult, Transaction } from '@/lib/types';
import { csvTransactionSchema } from '@/lib/validations';
import {
  CheckCircle,
  Clock,
  Download,
  FileText,
  PauseCircle,
  PlayCircle,
  Upload,
  XCircle,
} from 'lucide-react';
import { useState } from 'react';

interface BatchJob {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  totalTransactions: number;
  processedTransactions: number;
  fraudDetected: number;
  startTime?: string;
  endTime?: string;
  results?: FraudAnalysisResult[];
  taskId?: string;
}

export default function BatchProcessingPage() {
  const [jobs, setJobs] = useState<BatchJob[]>([
    {
      id: 'batch-001',
      name: 'January Transactions',
      status: 'completed',
      progress: 100,
      totalTransactions: 5420,
      processedTransactions: 5420,
      fraudDetected: 127,
      startTime: '2026-01-03T10:00:00',
      endTime: '2026-01-03T10:15:32',
    },
    {
      id: 'batch-002',
      name: 'February Transactions',
      status: 'running',
      progress: 45,
      totalTransactions: 4850,
      processedTransactions: 2182,
      fraudDetected: 58,
      startTime: '2026-01-03T11:30:00',
    },
    {
      id: 'batch-003',
      name: 'March Transactions',
      status: 'pending',
      progress: 0,
      totalTransactions: 5100,
      processedTransactions: 0,
      fraudDetected: 0,
    },
  ]);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const batchAnalysis = useBatchAnalysis();

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

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
  };

  const handleStartBatch = async () => {
    if (!selectedFile) return;

    try {
      const csvData = await parseCSVFile(selectedFile);

      // Validate and transform CSV transactions to API format
      const csvTransactions: CSVTransaction[] = csvData.map((row: any) =>
        csvTransactionSchema.parse(row)
      );

      const apiTransactions: Transaction[] = csvTransactions.map(transformToAPITransaction);

      const newJob: BatchJob = {
        id: `batch-${String(jobs.length + 1).padStart(3, '0')}`,
        name: selectedFile.name,
        status: 'running',
        progress: 0,
        totalTransactions: apiTransactions.length,
        processedTransactions: 0,
        fraudDetected: 0,
        startTime: new Date().toISOString(),
      };

      setJobs([newJob, ...jobs]);

      // Start batch analysis with transformed transactions
      const batchResponse = await batchAnalysis.mutateAsync({
        transactions: apiTransactions,
        // Don't send batch_id - let backend generate task_id
      });

      // Store task_id and poll for results
      const taskId = batchResponse.task_id;
      setJobs((prev) =>
        prev.map((job) =>
          job.id === newJob.id
            ? {
                ...job,
                taskId,
                status: 'running',
              }
            : job
        )
      );

      // Start polling for results
      pollTaskStatus(taskId, newJob.id);
    } catch (error) {
      console.error('Batch analysis failed:', error);
      // Update job status to failed
      setSelectedFile(null);
      setJobs((prev) =>
        prev.map((job) =>
          job.name === selectedFile?.name
            ? { ...job, status: 'failed' as const }
            : job
        )
      );
    }
  };

  // Poll for task completion and results
  const pollTaskStatus = async (taskId: string, jobId: string) => {
    const maxAttempts = 60; // Poll for up to 60 attempts (5 minutes at 5s interval)
    let attempts = 0;

    const poll = async () => {
      try {
        const taskStatus = await apiClient.getTaskStatus(taskId);

        // Update job with progress
        if (taskStatus.progress) {
          setJobs((prev) =>
            prev.map((job) =>
              job.id === jobId
                ? {
                    ...job,
                    progress: taskStatus.progress?.percentage || 0,
                    processedTransactions: taskStatus.progress?.processed || 0,
                    fraudDetected: taskStatus.progress?.fraud_detected_so_far || 0,
                  }
                : job
            )
          );
        }

        // Check if completed
        if (taskStatus.status === 'completed' && taskStatus.results) {
          const fraudCount = taskStatus.results.filter((r) => r.prediction.is_fraud).length;
          setJobs((prev) =>
            prev.map((job) =>
              job.id === jobId
                ? {
                    ...job,
                    status: 'completed',
                    progress: 100,
                    processedTransactions: taskStatus.results?.length || 0,
                    fraudDetected: fraudCount,
                    results: taskStatus.results,
                    endTime: new Date().toISOString(),
                  }
                : job
            )
          );
          return; // Stop polling
        }

        // Check if failed
        if (taskStatus.status === 'failed') {
          setJobs((prev) =>
            prev.map((job) =>
              job.id === jobId ? { ...job, status: 'failed' } : job
            )
          );
          return; // Stop polling
        }

        // Continue polling if still running
        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(poll, 5000); // Poll every 5 seconds
        } else {
          console.warn('Polling timeout - max attempts reached');
        }
      } catch (error) {
        console.error('Error polling task status:', error);
      }
    };

    // Start polling
    poll();
  };

  const cancelJob = (jobId: string) => {
    setJobs((prev) =>
      prev.map((job) => (job.id === jobId ? { ...job, status: 'cancelled' as const } : job))
    );
  };

  const handleExport = (job: BatchJob) => {
    if (!job.results || job.results.length === 0) {
      console.warn('No results available to export for job:', job.id);
      return;
    }
    exportToCSV(job.results, `${job.id}-fraud-analysis-results.csv`);
  };

  const handleFetchResults = async (job: BatchJob) => {
    if (!job.taskId) {
      console.error('No task ID available for job:', job.id);
      return;
    }

    try {
      const taskStatus = await apiClient.getTaskStatus(job.taskId);

      if (taskStatus.status === 'completed' && taskStatus.results) {
        const fraudCount = taskStatus.results.filter((r) => r.prediction.is_fraud).length;
        setJobs((prev) =>
          prev.map((j) =>
            j.id === job.id
              ? {
                  ...j,
                  results: taskStatus.results,
                  fraudDetected: fraudCount,
                  processedTransactions: taskStatus.results?.length || 0,
                }
              : j
          )
        );
      }
    } catch (error) {
      console.error('Failed to fetch results:', error);
    }
  };

  const getStatusIcon = (status: BatchJob['status']) => {
    switch (status) {
      case 'pending':
        return <Clock className="h-4 w-4" />;
      case 'running':
        return <PlayCircle className="h-4 w-4" />;
      case 'completed':
        return <CheckCircle className="h-4 w-4" />;
      case 'failed':
        return <XCircle className="h-4 w-4" />;
      case 'cancelled':
        return <PauseCircle className="h-4 w-4" />;
    }
  };

  const getStatusColor = (status: BatchJob['status']) => {
    switch (status) {
      case 'pending':
        return 'bg-zinc-500';
      case 'running':
        return 'bg-blue-500';
      case 'completed':
        return 'bg-green-500';
      case 'failed':
        return 'bg-red-500';
      case 'cancelled':
        return 'bg-yellow-500';
    }
  };

  return (
    <div className="container mx-auto py-8 px-4">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-zinc-900 dark:text-zinc-100 mb-2">
          Batch Processing
        </h1>
        <p className="text-zinc-600 dark:text-zinc-400">
          Upload and process large transaction datasets in batches
        </p>
      </div>

      {/* Upload Section */}
      <Card className="mb-8">
        <CardHeader>
          <CardTitle>New Batch Job</CardTitle>
          <CardDescription>Upload a CSV file to start batch processing</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4 items-end">
            <div className="flex-1">
              <label className="block mb-2 text-sm font-medium">
                Upload Transaction CSV
              </label>
              <input
                type="file"
                accept=".csv"
                onChange={handleFileUpload}
                className="w-full px-3 py-2 border border-zinc-300 dark:border-zinc-700 rounded-md"
              />
              {selectedFile && (
                <p className="text-sm text-zinc-600 dark:text-zinc-400 mt-2">
                  Selected: {selectedFile.name} ({(selectedFile.size / 1024).toFixed(2)} KB)
                </p>
              )}
            </div>
            <Button
              onClick={handleStartBatch}
              disabled={!selectedFile || batchAnalysis.isPending}
              className="gap-2"
            >
              <Upload className="h-4 w-4" />
              {batchAnalysis.isPending ? 'Processing...' : 'Start Batch'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Stats Cards */}
      <div className="grid gap-6 md:grid-cols-4 mb-8">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Jobs</CardTitle>
            <FileText className="h-4 w-4 text-zinc-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{jobs.length}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Running</CardTitle>
            <PlayCircle className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {jobs.filter((j) => j.status === 'running').length}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Completed</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {jobs.filter((j) => j.status === 'completed').length}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Frauds</CardTitle>
            <XCircle className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {jobs.reduce((sum, job) => sum + job.fraudDetected, 0)}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Jobs Table */}
      <Card>
        <CardHeader>
          <CardTitle>Batch Jobs</CardTitle>
          <CardDescription>Monitor and manage batch processing jobs</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Job ID</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Progress</TableHead>
                <TableHead>Transactions</TableHead>
                <TableHead>Frauds</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {jobs.map((job) => (
                <TableRow key={job.id}>
                  <TableCell className="font-mono">{job.id}</TableCell>
                  <TableCell>{job.name}</TableCell>
                  <TableCell>
                    <Badge className={`gap-1 ${getStatusColor(job.status)}`}>
                      {getStatusIcon(job.status)}
                      {job.status.toUpperCase()}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <Progress value={job.progress} className="w-24" />
                      <span className="text-sm">{job.progress}%</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    {job.processedTransactions} / {job.totalTransactions}
                  </TableCell>
                  <TableCell>
                    <Badge variant="destructive">{job.fraudDetected}</Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-2">
                      {job.status === 'running' && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => cancelJob(job.id)}
                        >
                          Cancel
                        </Button>
                      )}
                      {job.status === 'completed' && !job.results && job.taskId && (
                        <Button
                          variant="outline"
                          size="sm"
                          className="gap-1"
                          onClick={() => handleFetchResults(job)}
                        >
                          <Download className="h-3 w-3" />
                          Fetch Results
                        </Button>
                      )}
                      {job.status === 'completed' && job.results && job.results.length > 0 && (
                        <Button
                          variant="outline"
                          size="sm"
                          className="gap-1"
                          onClick={() => handleExport(job)}
                        >
                          <Download className="h-3 w-3" />
                          Export
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
