'use client';

import { memo } from 'react';
import { Badge } from '@/components/ui/badge';
import { CheckCircle2, XCircle, AlertTriangle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface DecisionBadgeProps {
  isFraud?: boolean;
  fraudDetected?: boolean;
  riskLevel?: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const DecisionBadge = memo(function DecisionBadge({
  isFraud,
  fraudDetected,
  riskLevel,
  size = 'md',
  className,
}: DecisionBadgeProps) {
  const fraudFlag = isFraud ?? fraudDetected ?? false;

  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5',
    md: 'text-sm px-3 py-1',
    lg: 'text-base px-4 py-1.5',
  };

  if (fraudFlag) {
    return (
      <Badge
        variant="destructive"
        className={cn('gap-1.5 font-semibold', sizeClasses[size], className)}
        role="status"
        aria-label="Transaction blocked due to fraud detection"
      >
        <XCircle className={cn('h-4 w-4', size === 'lg' && 'h-5 w-5')} aria-hidden="true" />
        FRAUD DETECTED
      </Badge>
    );
  }

  if (riskLevel === 'HIGH' || riskLevel === 'MEDIUM') {
    return (
      <Badge
        variant="secondary"
        className={cn('gap-1.5 font-semibold', sizeClasses[size], className)}
        role="status"
        aria-label={`Transaction requires review - ${riskLevel?.toLowerCase()} risk level`}
      >
        <AlertTriangle className={cn('h-4 w-4', size === 'lg' && 'h-5 w-5')} aria-hidden="true" />
        REVIEW REQUIRED
      </Badge>
    );
  }

  return (
    <Badge
      variant="outline"
      className={cn('gap-1.5 border-green-500 text-green-700 font-semibold', sizeClasses[size], className)}
      role="status"
      aria-label="Transaction approved - low risk"
    >
      <CheckCircle2 className={cn('h-4 w-4', size === 'lg' && 'h-5 w-5')} aria-hidden="true" />
      LEGITIMATE
    </Badge>
  );
});
