import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';

interface UserPreferencesState {
  // Theme
  theme: 'light' | 'dark' | 'system';

  // Dashboard preferences
  dashboardLayout: 'compact' | 'comfortable';
  defaultChartType: 'line' | 'bar' | 'area';

  // Notifications
  enableNotifications: boolean;
  notificationSound: boolean;
  alertThreshold: 'all' | 'high' | 'critical';

  // Analysis preferences
  autoRefreshInterval: number; // in seconds
  showConfidenceScores: boolean;
  showReasoningSteps: boolean;

  // Display preferences
  itemsPerPage: number;
  dateFormat: 'MM/DD/YYYY' | 'DD/MM/YYYY' | 'YYYY-MM-DD';
  currencyFormat: 'USD' | 'EUR' | 'GBP';

  // Actions
  setTheme: (theme: UserPreferencesState['theme']) => void;
  setDashboardLayout: (layout: UserPreferencesState['dashboardLayout']) => void;
  setDefaultChartType: (type: UserPreferencesState['defaultChartType']) => void;
  toggleNotifications: () => void;
  toggleNotificationSound: () => void;
  setAlertThreshold: (threshold: UserPreferencesState['alertThreshold']) => void;
  setAutoRefreshInterval: (interval: number) => void;
  toggleConfidenceScores: () => void;
  toggleReasoningSteps: () => void;
  setItemsPerPage: (items: number) => void;
  setDateFormat: (format: UserPreferencesState['dateFormat']) => void;
  setCurrencyFormat: (format: UserPreferencesState['currencyFormat']) => void;
  reset: () => void;
}

const initialState = {
  theme: 'system' as const,
  dashboardLayout: 'comfortable' as const,
  defaultChartType: 'line' as const,
  enableNotifications: true,
  notificationSound: true,
  alertThreshold: 'high' as const,
  autoRefreshInterval: 30,
  showConfidenceScores: true,
  showReasoningSteps: true,
  itemsPerPage: 20,
  dateFormat: 'MM/DD/YYYY' as const,
  currencyFormat: 'USD' as const,
};

export const useUserPreferencesStore = create<UserPreferencesState>()(
  devtools(
    persist(
      (set) => ({
        ...initialState,

        setTheme: (theme) =>
          set({ theme }),

        setDashboardLayout: (layout) =>
          set({ dashboardLayout: layout }),

        setDefaultChartType: (type) =>
          set({ defaultChartType: type }),

        toggleNotifications: () =>
          set((state) => ({ enableNotifications: !state.enableNotifications })),

        toggleNotificationSound: () =>
          set((state) => ({ notificationSound: !state.notificationSound })),

        setAlertThreshold: (threshold) =>
          set({ alertThreshold: threshold }),

        setAutoRefreshInterval: (interval) =>
          set({ autoRefreshInterval: interval }),

        toggleConfidenceScores: () =>
          set((state) => ({ showConfidenceScores: !state.showConfidenceScores })),

        toggleReasoningSteps: () =>
          set((state) => ({ showReasoningSteps: !state.showReasoningSteps })),

        setItemsPerPage: (items) =>
          set({ itemsPerPage: items }),

        setDateFormat: (format) =>
          set({ dateFormat: format }),

        setCurrencyFormat: (format) =>
          set({ currencyFormat: format }),

        reset: () =>
          set(initialState),
      }),
      {
        name: 'user-preferences-storage',
      }
    ),
    { name: 'UserPreferencesStore' }
  )
);
