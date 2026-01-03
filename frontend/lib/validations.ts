import { z } from 'zod';

// Transaction schema matching backend PaySim data format
export const transactionSchema = z.object({
  step: z.number().int().min(0),
  type: z.enum(['PAYMENT', 'TRANSFER', 'CASH_OUT', 'DEBIT', 'CASH_IN']),
  amount: z.number().positive(),
  nameOrig: z.string().min(1),
  oldbalanceOrg: z.number().min(0),
  newbalanceOrig: z.number(),
  nameDest: z.string().min(1),
  oldbalanceDest: z.number().min(0),
  newbalanceDest: z.number(),
  isFraud: z.number().int().min(0).max(1).optional(),
  isFlaggedFraud: z.number().int().min(0).max(1).optional(),
});

export const fraudAnalysisResultSchema = z.object({
  is_fraud: z.boolean(),
  confidence: z.number().min(0).max(1),
  risk_score: z.number().min(0).max(100),
  decision: z.enum(['APPROVE', 'REVIEW', 'BLOCK']),
  reasoning: z.string(),
  observations: z.array(z.string()),
  anomalies: z.array(z.string()),
  tool_results: z.record(z.string(), z.any()),
  explanation: z.string(),
  timestamp: z.string(),
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
