import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

export interface FraudAlert {
  id: string;
  transactionId: string;
  riskLevel: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  amount: number;
  type: string;
  timestamp: string;
  message: string;
}

export interface RealtimeUpdate {
  type: 'fraud_alert' | 'analysis_complete' | 'stats_update' | 'system_notification';
  data: any;
  timestamp: string;
}

interface RealtimeState {
  // WebSocket connection
  isConnected: boolean;
  connectionError: string | null;
  reconnectAttempts: number;

  // Real-time alerts
  alerts: FraudAlert[];
  unreadAlertCount: number;

  // Recent updates
  recentUpdates: RealtimeUpdate[];

  // Live statistics
  liveStats: {
    transactionsPerMinute: number;
    fraudRatePercentage: number;
    activeMonitoring: boolean;
  };

  // Actions
  setIsConnected: (isConnected: boolean) => void;
  setConnectionError: (error: string | null) => void;
  setReconnectAttempts: (attempts: number) => void;
  addAlert: (alert: FraudAlert) => void;
  markAlertsAsRead: () => void;
  clearAlerts: () => void;
  addUpdate: (update: RealtimeUpdate) => void;
  updateLiveStats: (stats: Partial<RealtimeState['liveStats']>) => void;
  reset: () => void;
}

const initialState = {
  isConnected: false,
  connectionError: null,
  reconnectAttempts: 0,
  alerts: [],
  unreadAlertCount: 0,
  recentUpdates: [],
  liveStats: {
    transactionsPerMinute: 0,
    fraudRatePercentage: 0,
    activeMonitoring: false,
  },
};

export const useRealtimeStore = create<RealtimeState>()(
  devtools(
    (set) => ({
      ...initialState,

      setIsConnected: (isConnected) =>
        set({ isConnected, connectionError: isConnected ? null : undefined }),

      setConnectionError: (error) =>
        set({ connectionError: error }),

      setReconnectAttempts: (attempts) =>
        set({ reconnectAttempts: attempts }),

      addAlert: (alert) =>
        set((state) => ({
          alerts: [alert, ...state.alerts].slice(0, 100), // Keep last 100
          unreadAlertCount: state.unreadAlertCount + 1,
        })),

      markAlertsAsRead: () =>
        set({ unreadAlertCount: 0 }),

      clearAlerts: () =>
        set({ alerts: [], unreadAlertCount: 0 }),

      addUpdate: (update) =>
        set((state) => ({
          recentUpdates: [update, ...state.recentUpdates].slice(0, 50), // Keep last 50
        })),

      updateLiveStats: (stats) =>
        set((state) => ({
          liveStats: { ...state.liveStats, ...stats },
        })),

      reset: () =>
        set(initialState),
    }),
    { name: 'RealtimeStore' }
  )
);
