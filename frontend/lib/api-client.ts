import axios, { AxiosError, AxiosInstance } from 'axios';
import type {
  BatchAnalysisRequest,
  BatchAnalysisResult,
  FraudAnalysisResult,
  HealthStatus,
  StatefulSession,
  Transaction,
} from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class APIClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => {
        console.log(`[API] Response:`, response.status);
        return response;
      },
      (error: AxiosError) => {
        console.error(`[API] Error:`, error.response?.status, error.message);
        return Promise.reject(this.handleError(error));
      }
    );
  }

  private handleError(error: AxiosError): Error {
    if (error.response) {
      // Server responded with error
      const message = (error.response.data as any)?.detail || error.message;
      return new Error(`API Error: ${message}`);
    } else if (error.request) {
      // Request made but no response
      return new Error('Network Error: No response from server');
    } else {
      // Something else happened
      return new Error(`Request Error: ${error.message}`);
    }
  }

  // Health Check
  async checkHealth(): Promise<HealthStatus> {
    const response = await this.client.get('/health');
    return response.data;
  }

  // Single Transaction Analysis
  async analyzeFraud(transaction: Transaction): Promise<FraudAnalysisResult> {
    const response = await this.client.post('/api/v1/fraud/analyze', {
      transaction,
    });
    return response.data;
  }

  // Batch Analysis
  async analyzeBatch(request: BatchAnalysisRequest): Promise<BatchAnalysisResult> {
    const response = await this.client.post('/api/v1/fraud/analyze/batch', request);
    return response.data;
  }

  // Stateful Analysis (with session)
  async analyzeStateful(
    transaction: Transaction,
    sessionId?: string
  ): Promise<{ result: FraudAnalysisResult; session: StatefulSession }> {
    const response = await this.client.post('/api/v1/fraud/analyze/stateful', {
      transaction,
      session_id: sessionId,
    });
    return response.data;
  }

  // Resume Session
  async resumeSession(sessionId: string, transaction: Transaction): Promise<FraudAnalysisResult> {
    const response = await this.client.post(`/api/v1/fraud/sessions/${sessionId}/resume`, {
      transaction,
    });
    return response.data;
  }

  // Reasoning Patterns
  async analyzeWithReAct(transaction: Transaction): Promise<FraudAnalysisResult> {
    const response = await this.client.post('/api/v1/fraud/analyze/react', {
      transaction,
    });
    return response.data;
  }

  async analyzeWithCoT(transaction: Transaction): Promise<FraudAnalysisResult> {
    const response = await this.client.post('/api/v1/fraud/analyze/cot', {
      transaction,
    });
    return response.data;
  }

  async analyzeWithToT(transaction: Transaction): Promise<FraudAnalysisResult> {
    const response = await this.client.post('/api/v1/fraud/analyze/tot', {
      transaction,
    });
    return response.data;
  }

  // Agent Architectures
  async analyzeSingleAgent(transaction: Transaction): Promise<any> {
    const response = await this.client.post('/api/v1/fraud/agents/single', {
      transaction,
    });
    return response.data;
  }

  async analyzeManagerWorker(transaction: Transaction): Promise<any> {
    const response = await this.client.post('/api/v1/fraud/agents/manager-worker', {
      transaction,
    });
    return response.data;
  }

  async analyzeSwarm(
    transaction: Transaction,
    swarmSize: number = 5,
    threshold: number = 0.6
  ): Promise<any> {
    const response = await this.client.post('/api/v1/fraud/agents/swarm', {
      transaction,
      swarm_size: swarmSize,
      threshold,
    });
    return response.data;
  }
}

export const apiClient = new APIClient();
export default apiClient;
