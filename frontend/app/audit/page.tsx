"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  ClipboardList,
  FileCheck,
  GitBranch,
  TrendingUp,
  User
} from "lucide-react";
import { useState } from "react";

type ActionType = "LOGIN" | "TRANSACTION_REVIEW" | "POLICY_UPDATE" | "DATA_ACCESS" | "MODEL_PREDICTION";

interface AuditLog {
  id: string;
  timestamp: string;
  userId: string;
  action: ActionType;
  resource: string;
  details: string;
  ipAddress: string;
  outcome: "SUCCESS" | "FAILURE";
}

interface ComplianceMetric {
  category: string;
  totalRequests: number;
  compliantRequests: number;
  complianceRate: number;
  trend: number;
}

interface DataLineageNode {
  id: string;
  name: string;
  type: "SOURCE" | "TRANSFORM" | "MODEL" | "DECISION";
  timestamp: string;
  metadata: Record<string, any>;
}

export default function AuditPage() {
  const [selectedLog, setSelectedLog] = useState<string | null>(null);

  // Mock data - Audit Logs
  const auditLogs: AuditLog[] = [
    {
      id: "audit-001",
      timestamp: "2026-01-04T12:45:00Z",
      userId: "user@finsight.ai",
      action: "TRANSACTION_REVIEW",
      resource: "Transaction T12345",
      details: "Reviewed high-risk transaction, approved with conditions",
      ipAddress: "192.168.1.100",
      outcome: "SUCCESS",
    },
    {
      id: "audit-002",
      timestamp: "2026-01-04T12:30:00Z",
      userId: "admin@finsight.ai",
      action: "POLICY_UPDATE",
      resource: "Policy: High-Value Transfer",
      details: "Updated policy threshold from $5000 to $10000",
      ipAddress: "192.168.1.50",
      outcome: "SUCCESS",
    },
    {
      id: "audit-003",
      timestamp: "2026-01-04T12:15:00Z",
      userId: "analyst@finsight.ai",
      action: "DATA_ACCESS",
      resource: "Customer PII Data",
      details: "Accessed customer profile for fraud investigation",
      ipAddress: "192.168.1.75",
      outcome: "SUCCESS",
    },
    {
      id: "audit-004",
      timestamp: "2026-01-04T12:00:00Z",
      userId: "ml-service",
      action: "MODEL_PREDICTION",
      resource: "Fraud Detection Model v2.1",
      details: "Generated fraud prediction for transaction T12346",
      ipAddress: "10.0.1.25",
      outcome: "SUCCESS",
    },
  ];

  // Mock data - Compliance Metrics
  const complianceMetrics: ComplianceMetric[] = [
    {
      category: "GDPR Data Access",
      totalRequests: 150,
      compliantRequests: 148,
      complianceRate: 98.7,
      trend: 2.3,
    },
    {
      category: "Fraud Detection Accuracy",
      totalRequests: 10000,
      compliantRequests: 9450,
      complianceRate: 94.5,
      trend: 1.8,
    },
    {
      category: "Model Bias Metrics",
      totalRequests: 500,
      compliantRequests: 485,
      complianceRate: 97.0,
      trend: -0.5,
    },
    {
      category: "Regulatory Compliance",
      totalRequests: 200,
      compliantRequests: 196,
      complianceRate: 98.0,
      trend: 3.2,
    },
  ];

  // Mock data - Data Lineage
  const dataLineage: DataLineageNode[] = [
    {
      id: "node-001",
      name: "Raw Transaction Data",
      type: "SOURCE",
      timestamp: "2026-01-04T10:00:00Z",
      metadata: { source: "PaySim CSV", records: 6362620 },
    },
    {
      id: "node-002",
      name: "Data Cleaning Pipeline",
      type: "TRANSFORM",
      timestamp: "2026-01-04T10:15:00Z",
      metadata: { removed_duplicates: 42, filled_nulls: 0 },
    },
    {
      id: "node-003",
      name: "Feature Engineering",
      type: "TRANSFORM",
      timestamp: "2026-01-04T10:30:00Z",
      metadata: { features_created: 8, temporal_features: 3 },
    },
    {
      id: "node-004",
      name: "Fraud Detection Model",
      type: "MODEL",
      timestamp: "2026-01-04T10:45:00Z",
      metadata: { model_version: "2.1.0", accuracy: 0.945 },
    },
    {
      id: "node-005",
      name: "Risk Score Decision",
      type: "DECISION",
      timestamp: "2026-01-04T11:00:00Z",
      metadata: { decision: "BLOCK", confidence: 0.98, risk_score: 92 },
    },
  ];

  const getActionBadge = (action: ActionType) => {
    const colors = {
      LOGIN: "bg-blue-500",
      TRANSACTION_REVIEW: "bg-purple-500",
      POLICY_UPDATE: "bg-orange-500",
      DATA_ACCESS: "bg-yellow-500",
      MODEL_PREDICTION: "bg-green-500",
    };
    return <Badge className={colors[action]}>{action.replace("_", " ")}</Badge>;
  };

  const getLineageTypeBadge = (type: DataLineageNode["type"]) => {
    const colors = {
      SOURCE: "bg-blue-500",
      TRANSFORM: "bg-purple-500",
      MODEL: "bg-green-500",
      DECISION: "bg-red-500",
    };
    return <Badge className={colors[type]}>{type}</Badge>;
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Audit & Compliance</h1>
        <p className="text-zinc-500 mt-1">
          Audit logs, compliance reports, and data lineage visualization
        </p>
      </div>

      {/* Audit Log Viewer */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <ClipboardList className="h-5 w-5" />
                Audit Log Viewer
              </CardTitle>
              <CardDescription>
                Track user actions, transactions, and model predictions
              </CardDescription>
            </div>
            <Button variant="outline" size="sm">
              Export Logs
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Timestamp</TableHead>
                <TableHead>User</TableHead>
                <TableHead>Action</TableHead>
                <TableHead>Resource</TableHead>
                <TableHead>Details</TableHead>
                <TableHead>IP Address</TableHead>
                <TableHead>Outcome</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {auditLogs.map((log) => (
                <TableRow key={log.id} className="cursor-pointer hover:bg-zinc-50" onClick={() => setSelectedLog(log.id)}>
                  <TableCell className="font-mono text-xs">
                    {new Date(log.timestamp).toLocaleString()}
                  </TableCell>
                  <TableCell className="flex items-center gap-2">
                    <User className="h-4 w-4 text-zinc-500" />
                    <span className="font-mono text-sm">{log.userId}</span>
                  </TableCell>
                  <TableCell>{getActionBadge(log.action)}</TableCell>
                  <TableCell className="font-medium">{log.resource}</TableCell>
                  <TableCell className="max-w-xs truncate text-sm">{log.details}</TableCell>
                  <TableCell className="font-mono text-sm">{log.ipAddress}</TableCell>
                  <TableCell>
                    {log.outcome === "SUCCESS" ? (
                      <Badge className="bg-green-500">SUCCESS</Badge>
                    ) : (
                      <Badge variant="destructive">FAILURE</Badge>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Compliance Reports */}
      <div>
        <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
          <FileCheck className="h-5 w-5" />
          Compliance Reports
        </h2>
        <div className="grid gap-4 md:grid-cols-2">
          {complianceMetrics.map((metric) => (
            <Card key={metric.category}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-medium">{metric.category}</CardTitle>
                  <Badge variant={metric.trend >= 0 ? "default" : "destructive"} className="gap-1">
                    <TrendingUp className="h-3 w-3" />
                    {metric.trend >= 0 ? "+" : ""}
                    {metric.trend}%
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-2xl font-bold">{metric.complianceRate}%</span>
                    <span className="text-sm text-zinc-500">
                      {metric.compliantRequests} / {metric.totalRequests}
                    </span>
                  </div>
                  <Progress value={metric.complianceRate} />
                  <div className="flex justify-between text-xs text-zinc-500">
                    <span>Compliant</span>
                    <span>Non-Compliant: {metric.totalRequests - metric.compliantRequests}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* Data Lineage Visualization */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <GitBranch className="h-5 w-5" />
                Data Lineage Visualization
              </CardTitle>
              <CardDescription>
                Track data flow from source to decision
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {dataLineage.map((node, index) => (
              <div key={node.id} className="flex gap-4">
                {/* Timeline connector */}
                <div className="flex flex-col items-center">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-500 text-white text-sm font-semibold">
                    {index + 1}
                  </div>
                  {index < dataLineage.length - 1 && (
                    <div className="flex-1 w-px bg-zinc-200 min-h-[3rem]" />
                  )}
                </div>

                {/* Node content */}
                <div className="flex-1 pb-4">
                  <Card>
                    <CardHeader className="pb-2">
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-sm">{node.name}</CardTitle>
                        {getLineageTypeBadge(node.type)}
                      </div>
                      <CardDescription className="text-xs">
                        {new Date(node.timestamp).toLocaleString()}
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="pb-3">
                      <div className="bg-zinc-50 rounded p-2">
                        <pre className="text-xs font-mono">
                          {JSON.stringify(node.metadata, null, 2)}
                        </pre>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
