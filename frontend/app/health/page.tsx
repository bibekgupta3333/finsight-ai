"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  Activity,
  AlertCircle,
  CheckCircle,
  Database,
  Gauge,
  Server,
  Wifi,
  XCircle
} from "lucide-react";
import { useState } from "react";

type ToolStatus = "HEALTHY" | "DEGRADED" | "UNHEALTHY";
type IncidentSeverity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

interface ToolHealth {
  name: string;
  status: ToolStatus;
  successRate: number;
  avgResponseTime: number;
  lastCheck: string;
  errorCount: number;
}

interface RecoveryIncident {
  id: string;
  timestamp: string;
  tool: string;
  severity: IncidentSeverity;
  rootCause: string;
  recoveryStrategy: string;
  recoveryTime: number;
  status: "RECOVERED" | "RECOVERING" | "FAILED";
}

interface ResourceMetrics {
  workerPoolUtilization: number;
  activeWorkers: number;
  totalWorkers: number;
  queueDepth: number;
  connectionPoolSize: number;
  activeConnections: number;
  memoryUsage: number;
  memoryLimit: number;
}

interface WebSocketConnection {
  id: string;
  clientId: string;
  connectedAt: string;
  topics: string[];
  messagesSent: number;
  messagesReceived: number;
  status: "CONNECTED" | "DISCONNECTED";
}

export default function HealthPage() {
  const [selectedTool, setSelectedTool] = useState<string | null>(null);

  // Mock data - Tool Health
  const toolsHealth: ToolHealth[] = [
    {
      name: "Risk Analyzer",
      status: "HEALTHY",
      successRate: 98.5,
      avgResponseTime: 320,
      lastCheck: "2026-01-04T12:45:00Z",
      errorCount: 3,
    },
    {
      name: "Pattern Detector",
      status: "HEALTHY",
      successRate: 97.2,
      avgResponseTime: 450,
      lastCheck: "2026-01-04T12:45:00Z",
      errorCount: 8,
    },
    {
      name: "Consensus Voter",
      status: "DEGRADED",
      successRate: 89.5,
      avgResponseTime: 680,
      lastCheck: "2026-01-04T12:44:00Z",
      errorCount: 24,
    },
    {
      name: "Explanation Generator",
      status: "HEALTHY",
      successRate: 96.8,
      avgResponseTime: 520,
      lastCheck: "2026-01-04T12:45:00Z",
      errorCount: 12,
    },
  ];

  // Mock data - Recovery Incidents
  const incidents: RecoveryIncident[] = [
    {
      id: "INC-001",
      timestamp: "2026-01-04T10:30:00Z",
      tool: "Consensus Voter",
      severity: "MEDIUM",
      rootCause: "Timeout waiting for LLM response",
      recoveryStrategy: "Circuit breaker opened, fallback to cached result",
      recoveryTime: 2.3,
      status: "RECOVERED",
    },
    {
      id: "INC-002",
      timestamp: "2026-01-04T09:15:00Z",
      tool: "Pattern Detector",
      severity: "LOW",
      rootCause: "High memory usage during pattern matching",
      recoveryStrategy: "Reduced batch size, triggered GC",
      recoveryTime: 1.8,
      status: "RECOVERED",
    },
    {
      id: "INC-003",
      timestamp: "2026-01-04T08:00:00Z",
      tool: "Risk Analyzer",
      severity: "HIGH",
      rootCause: "Database connection pool exhausted",
      recoveryStrategy: "Created new connection pool, killed idle connections",
      recoveryTime: 5.2,
      status: "RECOVERED",
    },
  ];

  // Mock data - Resource Metrics
  const resourceMetrics: ResourceMetrics = {
    workerPoolUtilization: 65,
    activeWorkers: 13,
    totalWorkers: 20,
    queueDepth: 8,
    connectionPoolSize: 50,
    activeConnections: 32,
    memoryUsage: 2.4,
    memoryLimit: 4.0,
  };

  // Mock data - WebSocket Connections
  const wsConnections: WebSocketConnection[] = [
    {
      id: "ws-001",
      clientId: "client-abc123",
      connectedAt: "2026-01-04T12:30:00Z",
      topics: ["fraud_alerts", "agent_updates"],
      messagesSent: 45,
      messagesReceived: 12,
      status: "CONNECTED",
    },
    {
      id: "ws-002",
      clientId: "client-def456",
      connectedAt: "2026-01-04T12:15:00Z",
      topics: ["fraud_alerts"],
      messagesSent: 23,
      messagesReceived: 5,
      status: "CONNECTED",
    },
    {
      id: "ws-003",
      clientId: "client-ghi789",
      connectedAt: "2026-01-04T11:50:00Z",
      topics: ["fraud_alerts", "agent_updates", "batch_progress"],
      messagesSent: 67,
      messagesReceived: 18,
      status: "CONNECTED",
    },
  ];

  const getStatusColor = (status: ToolStatus) => {
    switch (status) {
      case "HEALTHY":
        return "text-green-500";
      case "DEGRADED":
        return "text-yellow-500";
      case "UNHEALTHY":
        return "text-red-500";
    }
  };

  const getStatusBadge = (status: ToolStatus) => {
    switch (status) {
      case "HEALTHY":
        return <Badge className="bg-green-500">HEALTHY</Badge>;
      case "DEGRADED":
        return <Badge className="bg-yellow-500">DEGRADED</Badge>;
      case "UNHEALTHY":
        return <Badge variant="destructive">UNHEALTHY</Badge>;
    }
  };

  const getSeverityBadge = (severity: IncidentSeverity) => {
    switch (severity) {
      case "LOW":
        return <Badge variant="secondary">LOW</Badge>;
      case "MEDIUM":
        return <Badge className="bg-yellow-500">MEDIUM</Badge>;
      case "HIGH":
        return <Badge className="bg-orange-500">HIGH</Badge>;
      case "CRITICAL":
        return <Badge variant="destructive">CRITICAL</Badge>;
    }
  };

  const getRecoveryStatusBadge = (status: RecoveryIncident["status"]) => {
    switch (status) {
      case "RECOVERED":
        return <Badge className="bg-green-500">RECOVERED</Badge>;
      case "RECOVERING":
        return <Badge className="bg-blue-500">RECOVERING</Badge>;
      case "FAILED":
        return <Badge variant="destructive">FAILED</Badge>;
    }
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">System Health & Monitoring</h1>
        <p className="text-zinc-500 mt-1">
          Real-time monitoring of tools, resources, and system health
        </p>
      </div>

      {/* Tool Health Dashboard */}
      <div>
        <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
          <Activity className="h-5 w-5" />
          Tool Health Dashboard
        </h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {toolsHealth.map((tool) => (
            <Card key={tool.name} className="cursor-pointer hover:border-blue-500" onClick={() => setSelectedTool(tool.name)}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-medium">{tool.name}</CardTitle>
                  {tool.status === "HEALTHY" ? (
                    <CheckCircle className={`h-5 w-5 ${getStatusColor(tool.status)}`} />
                  ) : tool.status === "DEGRADED" ? (
                    <AlertCircle className={`h-5 w-5 ${getStatusColor(tool.status)}`} />
                  ) : (
                    <XCircle className={`h-5 w-5 ${getStatusColor(tool.status)}`} />
                  )}
                </div>
                {getStatusBadge(tool.status)}
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-zinc-500">Success Rate:</span>
                    <span className="font-semibold">{tool.successRate}%</span>
                  </div>
                  <Progress value={tool.successRate} />
                  <div className="flex justify-between text-sm">
                    <span className="text-zinc-500">Avg Response:</span>
                    <span className="font-semibold">{tool.avgResponseTime}ms</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-zinc-500">Errors (24h):</span>
                    <span className="font-semibold text-red-500">{tool.errorCount}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* Recovery Incident Viewer */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <AlertCircle className="h-5 w-5" />
                Recovery Incident Viewer
              </CardTitle>
              <CardDescription>Recent recovery incidents and root cause analysis</CardDescription>
            </div>
            <Button variant="outline" size="sm">
              View All
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Incident ID</TableHead>
                <TableHead>Timestamp</TableHead>
                <TableHead>Tool</TableHead>
                <TableHead>Severity</TableHead>
                <TableHead>Root Cause</TableHead>
                <TableHead>Recovery Strategy</TableHead>
                <TableHead>Recovery Time</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {incidents.map((incident) => (
                <TableRow key={incident.id}>
                  <TableCell className="font-mono">{incident.id}</TableCell>
                  <TableCell className="text-sm">
                    {new Date(incident.timestamp).toLocaleString()}
                  </TableCell>
                  <TableCell>{incident.tool}</TableCell>
                  <TableCell>{getSeverityBadge(incident.severity)}</TableCell>
                  <TableCell className="max-w-xs truncate">{incident.rootCause}</TableCell>
                  <TableCell className="max-w-xs truncate">{incident.recoveryStrategy}</TableCell>
                  <TableCell>{incident.recoveryTime}s</TableCell>
                  <TableCell>{getRecoveryStatusBadge(incident.status)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Resource Monitoring */}
      <div>
        <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
          <Gauge className="h-5 w-5" />
          Resource Monitoring
        </h2>
        <div className="grid gap-4 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Server className="h-4 w-4" />
                Worker Pool
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span className="text-zinc-500">Utilization:</span>
                    <span className="font-semibold">{resourceMetrics.workerPoolUtilization}%</span>
                  </div>
                  <Progress value={resourceMetrics.workerPoolUtilization} />
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-zinc-500">Active Workers:</span>
                  <span className="font-semibold">{resourceMetrics.activeWorkers} / {resourceMetrics.totalWorkers}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-zinc-500">Queue Depth:</span>
                  <span className="font-semibold">{resourceMetrics.queueDepth} tasks</span>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Database className="h-4 w-4" />
                Connection Pool
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span className="text-zinc-500">Utilization:</span>
                    <span className="font-semibold">
                      {Math.round((resourceMetrics.activeConnections / resourceMetrics.connectionPoolSize) * 100)}%
                    </span>
                  </div>
                  <Progress value={(resourceMetrics.activeConnections / resourceMetrics.connectionPoolSize) * 100} />
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-zinc-500">Active Connections:</span>
                  <span className="font-semibold">{resourceMetrics.activeConnections} / {resourceMetrics.connectionPoolSize}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-zinc-500">Available:</span>
                  <span className="font-semibold">{resourceMetrics.connectionPoolSize - resourceMetrics.activeConnections}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="md:col-span-2">
            <CardHeader>
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Activity className="h-4 w-4" />
                Memory Usage
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span className="text-zinc-500">Memory:</span>
                    <span className="font-semibold">
                      {resourceMetrics.memoryUsage.toFixed(2)} GB / {resourceMetrics.memoryLimit.toFixed(2)} GB
                    </span>
                  </div>
                  <Progress value={(resourceMetrics.memoryUsage / resourceMetrics.memoryLimit) * 100} />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* WebSocket Connection Manager */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Wifi className="h-5 w-5" />
                WebSocket Connection Manager
              </CardTitle>
              <CardDescription>Active WebSocket connections and subscriptions</CardDescription>
            </div>
            <Badge variant="secondary">{wsConnections.filter(c => c.status === "CONNECTED").length} Active</Badge>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Connection ID</TableHead>
                <TableHead>Client ID</TableHead>
                <TableHead>Connected At</TableHead>
                <TableHead>Topics</TableHead>
                <TableHead>Messages Sent</TableHead>
                <TableHead>Messages Received</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {wsConnections.map((conn) => (
                <TableRow key={conn.id}>
                  <TableCell className="font-mono">{conn.id}</TableCell>
                  <TableCell className="font-mono">{conn.clientId}</TableCell>
                  <TableCell className="text-sm">
                    {new Date(conn.connectedAt).toLocaleString()}
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1 flex-wrap">
                      {conn.topics.map((topic) => (
                        <Badge key={topic} variant="outline" className="text-xs">
                          {topic}
                        </Badge>
                      ))}
                    </div>
                  </TableCell>
                  <TableCell>{conn.messagesSent}</TableCell>
                  <TableCell>{conn.messagesReceived}</TableCell>
                  <TableCell>
                    {conn.status === "CONNECTED" ? (
                      <Badge className="bg-green-500">CONNECTED</Badge>
                    ) : (
                      <Badge variant="secondary">DISCONNECTED</Badge>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
