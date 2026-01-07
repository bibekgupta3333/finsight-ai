'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { FraudAlertList } from '@/components/fraud/fraud-alert-card';
import { useRealtimeStore } from '@/lib/store/realtime-store';
import { useNotificationStore } from '@/lib/store/notification-store';
import { useWebSocket } from '@/hooks/use-websocket';
import { Activity, AlertCircle, CheckCircle2, Wifi, WifiOff, RefreshCw } from 'lucide-react';

export default function MonitoringPage() {
  const {
    alerts,
    isConnected,
    connectionError,
    liveStats,
    markAlertsAsRead,
    clearAlerts,
  } = useRealtimeStore();

  const addNotification = useNotificationStore((state) => state.addNotification);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);

  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const wsUrl = baseUrl.replace('http', 'ws') + '/ws/monitoring';

  // WebSocket connection
  const { reconnect, disconnect } = useWebSocket({
    url: wsUrl,
    onConnect: () => {
      addNotification({
        type: 'success',
        title: 'Connected',
        message: 'Real-time monitoring is active',
        duration: 3000,
      });
      setReconnectAttempts(0);
    },
    onDisconnect: () => {
      addNotification({
        type: 'warning',
        title: 'Disconnected',
        message: 'Lost connection to monitoring server',
      });
    },
    onError: (error) => {
      addNotification({
        type: 'error',
        title: 'Connection Error',
        message: 'Failed to connect to monitoring server',
      });
    },
  });

  useEffect(() => {
    // WebSocket auto-connects via the hook
    // Cleanup on unmount
    return () => disconnect();
  }, [disconnect]);

  const handleReconnect = () => {
    setReconnectAttempts((prev) => prev + 1);
    disconnect();
    setTimeout(() => reconnect(), 1000);
  };

  return (
    <div className="container mx-auto space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Real-Time Monitoring</h1>
          <p className="text-muted-foreground">
            Live fraud detection alerts and system status
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Badge variant={isConnected ? 'default' : 'destructive'} className="gap-2">
            {isConnected ? (
              <>
                <Wifi className="h-3 w-3" />
                Connected
              </>
            ) : (
              <>
                <WifiOff className="h-3 w-3" />
                Disconnected
              </>
            )}
          </Badge>
          {!isConnected && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleReconnect}
              className="gap-2"
            >
              <RefreshCw className="h-4 w-4" />
              Reconnect ({reconnectAttempts})
            </Button>
          )}
        </div>
      </div>

      {/* Connection Error */}
      {connectionError && (
        <Card className="border-destructive">
          <CardContent className="flex items-center gap-3 py-4">
            <AlertCircle className="h-5 w-5 text-destructive" />
            <div className="flex-1">
              <p className="font-medium">Connection Error</p>
              <p className="text-sm text-muted-foreground">{connectionError}</p>
            </div>
            <Button variant="outline" size="sm" onClick={handleReconnect}>
              Retry
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Live Statistics */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Transactions/Min</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {liveStats.transactionsPerMinute.toFixed(1)}
            </div>
            <p className="text-xs text-muted-foreground">
              {liveStats.activeMonitoring ? 'Monitoring active' : 'Monitoring paused'}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Fraud Rate</CardTitle>
            <AlertCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {liveStats.fraudRatePercentage.toFixed(2)}%
            </div>
            <p className="text-xs text-muted-foreground">
              Of monitored transactions
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Alerts</CardTitle>
            <AlertCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{alerts.length}</div>
            <p className="text-xs text-muted-foreground">
              Requires attention
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Alert Feed */}
      <div>
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold">Alert Feed</h2>
            <p className="text-sm text-muted-foreground">
              Recent fraud detection alerts
            </p>
          </div>
          {alerts.length > 0 && (
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={markAlertsAsRead}>
                Mark All Read
              </Button>
              <Button variant="outline" size="sm" onClick={clearAlerts}>
                Clear All
              </Button>
            </div>
          )}
        </div>

        <FraudAlertList
          alerts={alerts}
          onDismiss={(id) => {
            // Remove specific alert
            useRealtimeStore.setState((state) => ({
              alerts: state.alerts.filter((a) => a.id !== id),
            }));
          }}
          onClearAll={clearAlerts}
        />
      </div>

      {/* System Status */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5" />
            System Status
          </CardTitle>
          <CardDescription>Backend service health and connectivity</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">WebSocket Connection</span>
              <Badge variant={isConnected ? 'default' : 'destructive'}>
                {isConnected ? 'Active' : 'Inactive'}
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Monitoring Status</span>
              <Badge variant={liveStats.activeMonitoring ? 'default' : 'secondary'}>
                {liveStats.activeMonitoring ? 'Running' : 'Paused'}
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Reconnect Attempts</span>
              <span className="text-sm font-medium">{reconnectAttempts}</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
