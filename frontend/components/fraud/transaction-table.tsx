'use client';

import { memo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Transaction, FraudPrediction } from '@/lib/store/fraud-analysis-store';
import { formatCurrency } from '@/lib/utils';
import { RiskGauge } from './risk-gauge';
import { DecisionBadge } from './decision-badge';

interface TransactionTableProps {
  transactions: Array<{
    transaction: Transaction;
    prediction: FraudPrediction;
    id: string;
  }>;
  onRowClick?: (id: string) => void;
}

export const TransactionTable = memo(function TransactionTable({ transactions, onRowClick }: TransactionTableProps) {
  if (transactions.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-muted-foreground">
          No transactions to display
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Transaction Analysis Results</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto -mx-6 px-6 md:mx-0 md:px-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="min-w-[100px]">Type</TableHead>
                <TableHead className="min-w-[120px]">Amount</TableHead>
                <TableHead className="min-w-[100px]">Risk Level</TableHead>
                <TableHead className="min-w-[140px]">Risk Score</TableHead>
                <TableHead className="min-w-[100px]">Confidence</TableHead>
                <TableHead className="min-w-[100px]">Decision</TableHead>
                <TableHead className="min-w-[180px]">Timestamp</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {transactions.map((item) => (
                <TableRow
                  key={item.id}
                  className={onRowClick ? 'cursor-pointer hover:bg-muted' : ''}
                  onClick={() => onRowClick?.(item.id)}
                >
                  <TableCell>
                    <Badge variant="outline">{item.transaction.type}</Badge>
                  </TableCell>
                  <TableCell className="font-medium">
                    {formatCurrency(item.transaction.amount)}
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant={
                        item.prediction.risk_level === 'CRITICAL'
                          ? 'destructive'
                          : item.prediction.risk_level === 'HIGH'
                          ? 'default'
                          : item.prediction.risk_level === 'MEDIUM'
                          ? 'secondary'
                          : 'outline'
                      }
                    >
                      {item.prediction.risk_level}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <RiskGauge
                        value={item.prediction.risk_score}
                        size="sm"
                        showLabel={false}
                      />
                      <span className="text-sm text-muted-foreground">
                        {item.prediction.risk_score.toFixed(1)}
                      </span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <span className="text-sm">
                      {(item.prediction.confidence * 100).toFixed(0)}%
                    </span>
                  </TableCell>
                  <TableCell>
                    <DecisionBadge
                      fraudDetected={item.prediction.fraud_detected}
                      riskLevel={item.prediction.risk_level}
                    />
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {new Date(item.prediction.timestamp).toLocaleString()}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
});
