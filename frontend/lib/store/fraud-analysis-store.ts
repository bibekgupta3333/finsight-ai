import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';

export interface Transaction {
  step: number;
  type: string;
  amount: number;
  nameOrig: string;
  oldbalanceOrg: number;
  newbalanceOrig: number;
  nameDest: string;
  oldbalanceDest: number;
  newbalanceDest: number;
  isFraud?: number;
  isFlaggedFraud?: number;
}

export interface FraudPrediction {
  fraud_detected: boolean;
  risk_level: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  confidence: number;
  risk_score: number;
  explanation: string;
  timestamp: string;
}

export interface AnalysisResult {
  transaction: Transaction;
  prediction: FraudPrediction;
  id: string;
  analyzedAt: string;
}

interface FraudAnalysisState {
  // Current analysis
  currentTransaction: Transaction | null;
  currentAnalysis: AnalysisResult | null;
  isAnalyzing: boolean;
  error: string | null;

  // Analysis history
  analysisHistory: AnalysisResult[];

  // Batch processing
  batchTaskId: string | null;
  batchStatus: 'idle' | 'processing' | 'completed' | 'failed';
  batchProgress: number;
  batchResults: AnalysisResult[];

  // Statistics
  stats: {
    totalAnalyzed: number;
    fraudDetected: number;
    avgProcessingTime: number;
  };

  // Actions
  setCurrentTransaction: (transaction: Transaction) => void;
  setCurrentAnalysis: (analysis: AnalysisResult | null) => void;
  setIsAnalyzing: (isAnalyzing: boolean) => void;
  setError: (error: string | null) => void;
  addToHistory: (result: AnalysisResult) => void;
  clearHistory: () => void;
  setBatchTaskId: (taskId: string | null) => void;
  setBatchStatus: (status: FraudAnalysisState['batchStatus']) => void;
  setBatchProgress: (progress: number) => void;
  setBatchResults: (results: AnalysisResult[]) => void;
  updateStats: (stats: Partial<FraudAnalysisState['stats']>) => void;
  reset: () => void;
}

const initialState = {
  currentTransaction: null,
  currentAnalysis: null,
  isAnalyzing: false,
  error: null,
  analysisHistory: [],
  batchTaskId: null,
  batchStatus: 'idle' as const,
  batchProgress: 0,
  batchResults: [],
  stats: {
    totalAnalyzed: 0,
    fraudDetected: 0,
    avgProcessingTime: 0,
  },
};

export const useFraudAnalysisStore = create<FraudAnalysisState>()(
  devtools(
    persist(
      (set) => ({
        ...initialState,

        setCurrentTransaction: (transaction) =>
          set({ currentTransaction: transaction }),

        setCurrentAnalysis: (analysis) =>
          set({ currentAnalysis: analysis }),

        setIsAnalyzing: (isAnalyzing) =>
          set({ isAnalyzing }),

        setError: (error) =>
          set({ error }),

        addToHistory: (result) =>
          set((state) => ({
            analysisHistory: [result, ...state.analysisHistory].slice(0, 50), // Keep last 50
          })),

        clearHistory: () =>
          set({ analysisHistory: [] }),

        setBatchTaskId: (taskId) =>
          set({ batchTaskId: taskId }),

        setBatchStatus: (status) =>
          set({ batchStatus: status }),

        setBatchProgress: (progress) =>
          set({ batchProgress: progress }),

        setBatchResults: (results) =>
          set({ batchResults: results }),

        updateStats: (stats) =>
          set((state) => ({
            stats: { ...state.stats, ...stats },
          })),

        reset: () =>
          set(initialState),
      }),
      {
        name: 'fraud-analysis-storage',
        partialize: (state) => ({
          analysisHistory: state.analysisHistory,
          stats: state.stats,
        }),
      }
    ),
    { name: 'FraudAnalysisStore' }
  )
);
