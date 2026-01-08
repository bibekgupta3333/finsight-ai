import { apiClient } from '@/lib/api-client';
import type { BatchAnalysisRequest, Transaction } from '@/lib/types';
import { fraudAnalysisResultSchema } from '@/lib/validations';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-hot-toast';

// Query keys for better organization
export const fraudKeys = {
  all: ['fraud'] as const,
  analysis: (txn: Transaction) => [...fraudKeys.all, 'analysis', txn] as const,
  batch: (batchId: string) => [...fraudKeys.all, 'batch', batchId] as const,
  health: () => [...fraudKeys.all, 'health'] as const,
};

// Health check query
export function useHealthCheck() {
  return useQuery({
    queryKey: fraudKeys.health(),
    queryFn: () => apiClient.checkHealth(),
    refetchInterval: 30000, // Refetch every 30 seconds
    retry: 2,
  });
}

// Single transaction analysis mutation with optimistic updates
export function useFraudAnalysis() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (transaction: Transaction) => {
      const result = await apiClient.analyzeFraud(transaction);
      // Validate response with Zod
      return fraudAnalysisResultSchema.parse(result);
    },

    // Optimistic update
    onMutate: async (transaction) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: fraudKeys.all });

      // Snapshot previous value
      const previousResults = queryClient.getQueryData(fraudKeys.all);

      // Optimistically show analyzing state
      toast.loading('Analyzing transaction...', { id: 'analysis' });

      return { previousResults };
    },

    onSuccess: (data) => {
      const riskLevel = data.prediction.risk_level;
      const confidence = (data.prediction.confidence * 100).toFixed(0);
      toast.success(
        `Analysis complete: ${riskLevel} risk (${confidence}% confidence)`,
        { id: 'analysis' }
      );
      queryClient.invalidateQueries({ queryKey: fraudKeys.all });
    },

    onError: (error: Error, transaction, context) => {
      toast.error(`Analysis failed: ${error.message}`, { id: 'analysis' });
      // Rollback on error
      if (context?.previousResults) {
        queryClient.setQueryData(fraudKeys.all, context.previousResults);
      }
    },

    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: fraudKeys.all });
    },

    retry: 2,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 5000),
  });
}

// Batch analysis mutation with optimistic updates
export function useBatchAnalysis() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: BatchAnalysisRequest) => {
      return await apiClient.analyzeBatch(request);
    },

    onMutate: async (request) => {
      // Show optimistic loading state
      toast.loading(`Submitting ${request.transactions.length} transactions for batch analysis...`, {
        id: 'batch-analysis',
      });

      return { transactionCount: request.transactions.length };
    },

    onSuccess: (data) => {
      toast.success(
        `Batch analysis submitted: ${data.total_transactions} transactions. Task ID: ${data.task_id}`,
        { id: 'batch-analysis' }
      );
      queryClient.invalidateQueries({ queryKey: fraudKeys.all });
    },

    onError: (error: Error) => {
      toast.error(`Batch analysis failed: ${error.message}`, { id: 'batch-analysis' });
    },

    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: fraudKeys.all });
    },

    retry: 2,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 5000),
  });
}

// ReAct pattern analysis
export function useReActAnalysis() {
  return useMutation({
    mutationFn: async (transaction: Transaction) => {
      return await apiClient.analyzeWithReAct(transaction);
    },
    onSuccess: (data) => {
      toast.success(`ReAct analysis: ${data.prediction.risk_level} risk`);
    },
    onError: (error: Error) => {
      toast.error(`ReAct analysis failed: ${error.message}`);
    },
  });
}

// Chain-of-Thought pattern analysis
export function useCoTAnalysis() {
  return useMutation({
    mutationFn: async (transaction: Transaction) => {
      return await apiClient.analyzeWithCoT(transaction);
    },
    onSuccess: (data) => {
      toast.success(`Chain-of-Thought analysis: ${data.prediction.risk_level} risk`);
    },
    onError: (error: Error) => {
      toast.error(`CoT analysis failed: ${error.message}`);
    },
  });
}

// Tree-of-Thought pattern analysis
export function useToTAnalysis() {
  return useMutation({
    mutationFn: async (transaction: Transaction) => {
      return await apiClient.analyzeWithToT(transaction);
    },
    onSuccess: (data) => {
      toast.success(`Tree-of-Thought analysis: ${data.prediction.risk_level} risk`);
    },
    onError: (error: Error) => {
      toast.error(`ToT analysis failed: ${error.message}`);
    },
  });
}

// Single agent analysis
export function useSingleAgent() {
  return useMutation({
    mutationFn: async (transaction: Transaction) => {
      return await apiClient.analyzeSingleAgent(transaction);
    },
    onSuccess: () => {
      toast.success('Single agent analysis complete');
    },
    onError: (error: Error) => {
      toast.error(`Single agent failed: ${error.message}`);
    },
  });
}

// Manager-Worker analysis
export function useManagerWorker() {
  return useMutation({
    mutationFn: async (transaction: Transaction) => {
      return await apiClient.analyzeManagerWorker(transaction);
    },
    onSuccess: () => {
      toast.success('Manager-Worker analysis complete');
    },
    onError: (error: Error) => {
      toast.error(`Manager-Worker failed: ${error.message}`);
    },
  });
}

// Swarm intelligence analysis
export function useSwarmAnalysis() {
  return useMutation({
    mutationFn: async ({
      transaction,
      swarmSize = 5,
      threshold = 0.6,
    }: {
      transaction: Transaction;
      swarmSize?: number;
      threshold?: number;
    }) => {
      return await apiClient.analyzeSwarm(transaction, swarmSize, threshold);
    },
    onSuccess: () => {
      toast.success('Swarm analysis complete');
    },
    onError: (error: Error) => {
      toast.error(`Swarm analysis failed: ${error.message}`);
    },
  });
}
