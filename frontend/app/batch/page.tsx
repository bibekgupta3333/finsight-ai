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
import { parseCSVFile } from '@/lib/export-utils';
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

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
  };

  const handleStartBatch = async () => {
    if (!selectedFile) return;

    try {
      const transactions = await parseCSVFile(selectedFile);

      const newJob: BatchJob = {
        id: `batch-${String(jobs.length + 1).padStart(3, '0')}`,
        name: selectedFile.name,
        status: 'running',
        progress: 0,
        totalTransactions: transactions.length,
        processedTransactions: 0,
        fraudDetected: 0,
        startTime: new Date().toISOString(),
      };

      setJobs([newJob, ...jobs]);

      // Start batch analysis
      await batchAnalysis.mutateAsync({
        transactions,
        batch_id: newJob.id,
      });

      // Update job status
      setJobs((prev) =>
        prev.map((job) =>
          job.id === newJob.id
            ? {
                ...job,
                status: 'completed',
                progress: 100,
                processedTransactions: transactions.length,
                endTime: new Date().toISOString(),
              }
            : job
        )
      );
    } catch (error) {
      console.error('Batch analysis failed:', error);
    }
  };

  const cancelJob = (jobId: string) => {
    setJobs((prev) =>
      prev.map((job) => (job.id === jobId ? { ...job, status: 'cancelled' as const } : job))
    );
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
                      {job.status === 'completed' && (
                        <Button variant="outline" size="sm" className="gap-1">
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
