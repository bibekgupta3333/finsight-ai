'use client';

import { memo, useMemo } from 'react';
import { cn } from '@/lib/utils';

interface RiskGaugeProps {
  value: number; // 0-100
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  className?: string;
}

export const RiskGauge = memo(function RiskGauge({
  value,
  size = 'md',
  showLabel = true,
  className,
}: RiskGaugeProps) {
  const sizeClasses = {
    sm: 'h-2 w-24',
    md: 'h-4 w-32',
    lg: 'h-6 w-48',
  };

  const getRiskColor = (score: number) => {
    if (score >= 75) return 'bg-red-500';
    if (score >= 50) return 'bg-orange-500';
    if (score >= 25) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  const getRiskLabel = (score: number) => {
    if (score >= 75) return 'Critical Risk';
    if (score >= 50) return 'High Risk';
    if (score >= 25) return 'Medium Risk';
    return 'Low Risk';
  };

  const riskColor = useMemo(() => getRiskColor(value), [value]);
  const riskLabel = useMemo(() => getRiskLabel(value), [value]);
  const widthPercentage = useMemo(
    () => Math.min(100, Math.max(0, value)),
    [value]
  );

  return (
    <div className={cn('flex flex-col gap-1', className)}>
      <div
        className={cn('relative rounded-full bg-muted overflow-hidden', sizeClasses[size])}
        role="progressbar"
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`Risk score: ${value.toFixed(1)} - ${riskLabel}`}
      >
        <div
          className={cn('h-full transition-all duration-500 ease-out', riskColor)}
          style={{ width: `${widthPercentage}%` }}
        />
      </div>
      {showLabel && (
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>{riskLabel}</span>
          <span className="font-medium">{value.toFixed(1)}</span>
        </div>
      )}
    </div>
  );
});
