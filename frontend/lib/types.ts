// API Types based on backend/app/api/fraud.py

// CSV schema (what we parse from uploaded files)
export interface CSVTransaction {
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

// API schema (what backend expects)
export interface Transaction {
  transaction_id: string;
  type: string;
  amount: number;
  oldbalanceOrg: number;
  newbalanceOrig: number;
  oldbalanceDest: number;
  newbalanceDest: number;
  nameOrig?: string;
  nameDest?: string;
  timestamp?: string;
}

// Fraud prediction from backend
export interface FraudPrediction {
  is_fraud: boolean;
  risk_score: number;
  risk_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  confidence: number;
  explanation: string;
  factors: string[] | null;
  reasoning_steps: string[] | null;
}

// Backend response structure
export interface FraudAnalysisResult {
  transaction_id: string;
  prediction: FraudPrediction;
  processing_time_ms: number;
  timestamp: string;
  metadata: Record<string, any> | null;
}

export interface BatchAnalysisRequest {
  transactions: Transaction[];
  batch_id?: string;
  config?: {
    max_workers?: number;
    timeout?: number;
  };
}

export interface BatchAnalysisResult {
  batch_id: string;
  total: number;
  processed: number;
  fraud_count: number;
  results: FraudAnalysisResult[];
  processing_time: number;
  avg_confidence: number;
}

export interface AgentExecutionTrace {
  node_type: string;
  input: any;
  output: any;
  duration: number;
  timestamp: string;
}

export interface ReasoningPattern {
  pattern: "react" | "cot" | "tot" | "debate" | "self_critique" | "reflection";
  steps: string[];
  confidence: number;
}

export interface StatefulSession {
  session_id: string;
  history: FraudAnalysisResult[];
  memory: {
    short_term: string[];
    working: string[];
    long_term: string[];
  };
  created_at: string;
  last_updated: string;
}

export interface HealthStatus {
  status: "healthy" | "degraded" | "unhealthy";
  version: string;
  uptime: number;
  timestamp: string;
}
