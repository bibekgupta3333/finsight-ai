'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { AlertTriangle, X, Bell, BellOff } from 'lucide-react';
import { cn, formatCurrency } from '@/lib/utils';
import { FraudAlert } from '@/lib/store/realtime-store';

interface FraudAlertCardProps {
  alert: FraudAlert;
  onDismiss?: (id: string) => void;
  onMute?: (id: string) => void;
  className?: string;
}

export function FraudAlertCard({ alert, onDismiss, onMute, className }: FraudAlertCardProps) {
  const getSeverityColor = (level: FraudAlert['riskLevel']) => {
    switch (level) {
      case 'CRITICAL':
        return 'border-red-500 bg-red-50 dark:bg-red-950';
      case 'HIGH':
        return 'border-orange-500 bg-orange-50 dark:bg-orange-950';
      case 'MEDIUM':
        return 'border-yellow-500 bg-yellow-50 dark:bg-yellow-950';
      case 'LOW':
        return 'border-blue-500 bg-blue-50 dark:bg-blue-950';
    }
  };

  return (
    <Card className={cn('border-l-4', getSeverityColor(alert.riskLevel), className)}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5" />
            <CardTitle className="text-base">Fraud Alert</CardTitle>
          </div>
          <div className="flex items-center gap-1">
            {onMute && (
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={() => onMute(alert.id)}
              >
                <BellOff className="h-4 w-4" />
              </Button>
            )}
            {onDismiss && (
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={() => onDismiss(alert.id)}
              >
                <X className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center justify-between">
          <Badge
            variant={
              alert.riskLevel === 'CRITICAL' || alert.riskLevel === 'HIGH'
                ? 'destructive'
                : 'secondary'
            }
          >
            {alert.riskLevel} RISK
          </Badge>
          <span className="text-xs text-muted-foreground">
            {new Date(alert.timestamp).toLocaleTimeString()}
          </span>
        </div>

        <div className="space-y-1">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Transaction Type:</span>
            <span className="font-medium">{alert.type}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Amount:</span>
            <span className="font-medium">{formatCurrency(alert.amount)}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Transaction ID:</span>
            <span className="font-mono text-xs">{alert.transactionId}</span>
          </div>
        </div>

        <p className="text-sm">{alert.message}</p>
      </CardContent>
    </Card>
  );
}

interface FraudAlertListProps {
  alerts: FraudAlert[];
  onDismiss?: (id: string) => void;
  onMute?: (id: string) => void;
  onClearAll?: () => void;
  className?: string;
}

export function FraudAlertList({
  alerts,
  onDismiss,
  onMute,
  onClearAll,
  className,
}: FraudAlertListProps) {
  if (alerts.length === 0) {
    return (
      <Card className={className}>
        <CardContent className="py-12 text-center text-muted-foreground">
          <Bell className="mx-auto h-12 w-12 opacity-20" />
          <p className="mt-2">No active alerts</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className={cn('space-y-3', className)}>
      {onClearAll && (
        <div className="flex justify-end">
          <Button variant="outline" size="sm" onClick={onClearAll}>
            Clear All ({alerts.length})
          </Button>
        </div>
      )}
      {alerts.map((alert) => (
        <FraudAlertCard
          key={alert.id}
          alert={alert}
          onDismiss={onDismiss}
          onMute={onMute}
        />
      ))}
    </div>
  );
}
