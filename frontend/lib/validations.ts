import { z } from 'zod';

// CSV Transaction schema (what we parse from uploaded files)
export const csvTransactionSchema = z.object({
  step: z.number().int().min(0),
  type: z.enum(['PAYMENT', 'TRANSFER', 'CASH_OUT', 'DEBIT', 'CASH_IN']),
  amount: z.number().min(0),
  nameOrig: z.string().min(1),
  oldbalanceOrg: z.number().min(0),
  newbalanceOrig: z.number(),
  nameDest: z.string().min(1),
  oldbalanceDest: z.number().min(0),
  newbalanceDest: z.number(),
  isFraud: z.number().int().min(0).max(1).optional(),
  isFlaggedFraud: z.number().int().min(0).max(1).optional(),
});

// API Transaction schema (what backend expects)
export const apiTransactionSchema = z.object({
  transaction_id: z.string().min(1),
  type: z.enum(['PAYMENT', 'TRANSFER', 'CASH_OUT', 'DEBIT', 'CASH_IN']),
  amount: z.number().min(0),
  oldbalanceOrg: z.number().min(0),
  newbalanceOrig: z.number().min(0),
  oldbalanceDest: z.number().min(0),
  newbalanceDest: z.number().min(0),
  nameOrig: z.string().optional(),
  nameDest: z.string().optional(),
  timestamp: z.string().optional(),
});

// Keep legacy transactionSchema for backward compatibility
export const transactionSchema = csvTransactionSchema;

export const fraudPredictionSchema = z.object({
  is_fraud: z.boolean(),
  risk_score: z.number().min(0).max(100),
  risk_level: z.enum(['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']),
  confidence: z.number().min(0).max(1),
  explanation: z.string(),
  factors: z.array(z.string()).nullable(),
  reasoning_steps: z.array(z.string()).nullable(),
});

export const fraudAnalysisResultSchema = z.object({
  transaction_id: z.string(),
  prediction: fraudPredictionSchema,
  processing_time_ms: z.number(),
  timestamp: z.string(),
  metadata: z.record(z.string(), z.any()).nullable(),
});

export const batchAnalysisRequestSchema = z.object({
  transactions: z.array(transactionSchema),
  batch_id: z.string().optional(),
  config: z
    .object({
      max_workers: z.number().int().positive().optional(),
      timeout: z.number().positive().optional(),
    })
    .optional(),
});

export const healthStatusSchema = z.object({
  status: z.enum(['healthy', 'degraded', 'unhealthy']),
  version: z.string(),
  uptime: z.number(),
  timestamp: z.string(),
});

// Type exports
export type Transaction = z.infer<typeof transactionSchema>;
export type FraudAnalysisResult = z.infer<typeof fraudAnalysisResultSchema>;
export type BatchAnalysisRequest = z.infer<typeof batchAnalysisRequestSchema>;
export type HealthStatus = z.infer<typeof healthStatusSchema>;
