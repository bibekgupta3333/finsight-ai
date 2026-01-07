'use client';

import { Badge } from '@/components/ui/badge';
import { CheckCircle2, XCircle, AlertTriangle } from 'lucide-react';

interface DecisionBadgeProps {
  fraudDetected: boolean;
  riskLevel: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
}

export function DecisionBadge({ fraudDetected, riskLevel }: DecisionBadgeProps) {
  if (fraudDetected) {
    return (
      <Badge variant="destructive" className="gap-1">
        <XCircle className="h-3 w-3" />
        Block
      </Badge>
    );
  }

  if (riskLevel === 'HIGH' || riskLevel === 'MEDIUM') {
    return (
      <Badge variant="secondary" className="gap-1">
        <AlertTriangle className="h-3 w-3" />
        Review
      </Badge>
    );
  }

  return (
    <Badge variant="outline" className="gap-1 border-green-500 text-green-700">
      <CheckCircle2 className="h-3 w-3" />
      Approve
    </Badge>
  );
}
