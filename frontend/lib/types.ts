// API Types based on backend/app/api/fraud.py

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

export interface FraudAnalysisResult {
  is_fraud: boolean;
  confidence: number;
  risk_score: number;
  decision: "APPROVE" | "REVIEW" | "BLOCK";
  reasoning: string;
  observations: string[];
  anomalies: string[];
  tool_results: Record<string, any>;
  explanation: string;
  timestamp: string;
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
