'use client';

import { memo } from 'react';
import { Badge } from '@/components/ui/badge';
import { CheckCircle2, XCircle, AlertTriangle } from 'lucide-react';

interface DecisionBadgeProps {
  fraudDetected: boolean;
  riskLevel: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
}

export const DecisionBadge = memo(function DecisionBadge({ fraudDetected, riskLevel }: DecisionBadgeProps) {
  if (fraudDetected) {
    return (
      <Badge
        variant="destructive"
        className="gap-1"
        role="status"
        aria-label="Transaction blocked due to fraud detection"
      >
        <XCircle className="h-3 w-3" aria-hidden="true" />
        Block
      </Badge>
    );
  }

  if (riskLevel === 'HIGH' || riskLevel === 'MEDIUM') {
    return (
      <Badge
        variant="secondary"
        className="gap-1"
        role="status"
        aria-label={`Transaction requires review - ${riskLevel.toLowerCase()} risk level`}
      >
        <AlertTriangle className="h-3 w-3" aria-hidden="true" />
        Review
      </Badge>
    );
  }

  return (
    <Badge
      variant="outline"
      className="gap-1 border-green-500 text-green-700"
      role="status"
      aria-label="Transaction approved - low risk"
    >
      <CheckCircle2 className="h-3 w-3" aria-hidden="true" />
      Approve
    </Badge>
  );
});
