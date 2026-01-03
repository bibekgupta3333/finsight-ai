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

// Single transaction analysis mutation
export function useFraudAnalysis() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (transaction: Transaction) => {
      const result = await apiClient.analyzeFraud(transaction);
      // Validate response with Zod
      return fraudAnalysisResultSchema.parse(result);
    },
    onSuccess: (data) => {
      toast.success(
        `Analysis complete: ${data.decision} (${(data.confidence * 100).toFixed(0)}% confidence)`
      );
      queryClient.invalidateQueries({ queryKey: fraudKeys.all });
    },
    onError: (error: Error) => {
      toast.error(`Analysis failed: ${error.message}`);
    },
    retry: 2,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 5000),
  });
}

// Batch analysis mutation
export function useBatchAnalysis() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: BatchAnalysisRequest) => {
      return await apiClient.analyzeBatch(request);
    },
    onSuccess: (data) => {
      toast.success(
        `Batch analysis complete: ${data.fraud_count}/${data.total} flagged as fraud`
      );
      queryClient.invalidateQueries({ queryKey: fraudKeys.all });
    },
    onError: (error: Error) => {
      toast.error(`Batch analysis failed: ${error.message}`);
    },
  });
}

// ReAct pattern analysis
export function useReActAnalysis() {
  return useMutation({
    mutationFn: async (transaction: Transaction) => {
      return await apiClient.analyzeWithReAct(transaction);
    },
    onSuccess: (data) => {
      toast.success(`ReAct analysis: ${data.decision}`);
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
      toast.success(`Chain-of-Thought analysis: ${data.decision}`);
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
      toast.success(`Tree-of-Thought analysis: ${data.decision}`);
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
