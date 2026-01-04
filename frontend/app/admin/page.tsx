"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
    Code,
    Download,
    Play,
    Search,
    Settings,
    Terminal,
    Zap
} from "lucide-react";
import { useState } from "react";

type LogLevel = "DEBUG" | "INFO" | "WARN" | "ERROR";

interface LogEntry {
  id: string;
  timestamp: string;
  level: LogLevel;
  service: string;
  message: string;
  metadata?: Record<string, any>;
}

interface ToolTest {
  name: string;
  description: string;
  parameters: { name: string; type: string; required: boolean }[];
}

interface ConfigItem {
  key: string;
  value: string;
  category: "FEATURE_FLAGS" | "API_LIMITS" | "TIMEOUTS" | "RETRY";
  description: string;
}

export default function AdminPage() {
  const [logFilter, setLogFilter] = useState<LogLevel | "ALL">("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTool, setSelectedTool] = useState<string | null>(null);

  // Mock data - Available Tools
  const tools: ToolTest[] = [
    {
      name: "Risk Analyzer",
      description: "Analyzes transaction risk based on amount, type, and historical patterns",
      parameters: [
        { name: "transaction_id", type: "string", required: true },
        { name: "amount", type: "number", required: true },
        { name: "transaction_type", type: "string", required: true },
      ],
    },
    {
      name: "Pattern Detector",
      description: "Detects fraudulent patterns using machine learning models",
      parameters: [
        { name: "transaction_history", type: "array", required: true },
        { name: "lookback_days", type: "number", required: false },
      ],
    },
    {
      name: "Explanation Generator",
      description: "Generates human-readable explanations for fraud decisions",
      parameters: [
        { name: "decision", type: "string", required: true },
        { name: "confidence", type: "number", required: true },
        { name: "reasoning", type: "string", required: true },
      ],
    },
  ];

  // Mock data - System Configuration
  const configItems: ConfigItem[] = [
    {
      key: "ENABLE_MULTI_AGENT",
      value: "true",
      category: "FEATURE_FLAGS",
      description: "Enable multi-agent consensus for fraud detection",
    },
    {
      key: "ENABLE_CIRCUIT_BREAKER",
      value: "true",
      category: "FEATURE_FLAGS",
      description: "Enable circuit breaker pattern for resilience",
    },
    {
      key: "API_RATE_LIMIT_PER_MINUTE",
      value: "100",
      category: "API_LIMITS",
      description: "Maximum API requests per minute per client",
    },
    {
      key: "LLM_TIMEOUT_SECONDS",
      value: "30",
      category: "TIMEOUTS",
      description: "Timeout for LLM inference requests",
    },
    {
      key: "MAX_RETRY_ATTEMPTS",
      value: "3",
      category: "RETRY",
      description: "Maximum number of retry attempts for failed operations",
    },
    {
      key: "RETRY_BACKOFF_MULTIPLIER",
      value: "2.0",
      category: "RETRY",
      description: "Exponential backoff multiplier for retries",
    },
  ];

  // Mock data - Debug Logs
  const logs: LogEntry[] = [
    {
      id: "log-001",
      timestamp: "2026-01-04T12:45:23.456Z",
      level: "INFO",
      service: "fraud-analyzer",
      message: "Transaction analyzed successfully",
      metadata: { transaction_id: "T12345", decision: "APPROVE", confidence: 0.95 },
    },
    {
      id: "log-002",
      timestamp: "2026-01-04T12:45:22.123Z",
      level: "WARN",
      service: "llm-client",
      message: "LLM response time exceeded threshold",
      metadata: { response_time_ms: 3200, threshold_ms: 3000 },
    },
    {
      id: "log-003",
      timestamp: "2026-01-04T12:45:20.789Z",
      level: "ERROR",
      service: "database",
      message: "Connection pool exhausted, waiting for available connection",
      metadata: { pool_size: 20, active_connections: 20, queue_depth: 5 },
    },
    {
      id: "log-004",
      timestamp: "2026-01-04T12:45:18.456Z",
      level: "DEBUG",
      service: "circuit-breaker",
      message: "Circuit breaker state transition: CLOSED -> OPEN",
      metadata: { failure_threshold: 5, failures: 5, timeout_ms: 5000 },
    },
    {
      id: "log-005",
      timestamp: "2026-01-04T12:45:15.123Z",
      level: "INFO",
      service: "websocket-manager",
      message: "New WebSocket connection established",
      metadata: { client_id: "client-abc123", topics: ["fraud_alerts", "agent_updates"] },
    },
  ];

  const getLevelColor = (level: LogLevel) => {
    switch (level) {
      case "DEBUG":
        return "bg-zinc-500";
      case "INFO":
        return "bg-blue-500";
      case "WARN":
        return "bg-yellow-500";
      case "ERROR":
        return "bg-red-500";
    }
  };

  const getCategoryColor = (category: ConfigItem["category"]) => {
    switch (category) {
      case "FEATURE_FLAGS":
        return "bg-purple-500";
      case "API_LIMITS":
        return "bg-blue-500";
      case "TIMEOUTS":
        return "bg-yellow-500";
      case "RETRY":
        return "bg-green-500";
    }
  };

  const filteredLogs = logs.filter((log) => {
    const matchesLevel = logFilter === "ALL" || log.level === logFilter;
    const matchesSearch =
      searchQuery === "" ||
      log.message.toLowerCase().includes(searchQuery.toLowerCase()) ||
      log.service.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesLevel && matchesSearch;
  });

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Admin & Debug Console</h1>
        <p className="text-zinc-500 mt-1">
          Tool testing, agent playground, system configuration, and debug logs
        </p>
      </div>

      {/* Tool Testing Interface */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Zap className="h-5 w-5" />
                Tool Testing Interface
              </CardTitle>
              <CardDescription>Manually execute tools and view responses</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid gap-6 md:grid-cols-2">
            {/* Tool Selection */}
            <div className="space-y-4">
              <div>
                <Label>Select Tool</Label>
                <div className="mt-2 space-y-2">
                  {tools.map((tool) => (
                    <Card
                      key={tool.name}
                      className={`cursor-pointer hover:border-blue-500 ${
                        selectedTool === tool.name ? "border-blue-500 bg-blue-50" : ""
                      }`}
                      onClick={() => setSelectedTool(tool.name)}
                    >
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm">{tool.name}</CardTitle>
                        <CardDescription className="text-xs">{tool.description}</CardDescription>
                      </CardHeader>
                      <CardContent className="pb-3">
                        <div className="flex gap-1 flex-wrap">
                          {tool.parameters.map((param) => (
                            <Badge key={param.name} variant="outline" className="text-xs">
                              {param.name}
                              {param.required && <span className="text-red-500">*</span>}
                            </Badge>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            </div>

            {/* Tool Parameters & Execution */}
            <div className="space-y-4">
              {selectedTool ? (
                <>
                  <div>
                    <Label>Tool Parameters</Label>
                    <div className="mt-2 space-y-3">
                      {tools
                        .find((t) => t.name === selectedTool)
                        ?.parameters.map((param) => (
                          <div key={param.name}>
                            <Label className="text-sm">
                              {param.name}
                              {param.required && <span className="text-red-500">*</span>}
                            </Label>
                            <Input
                              placeholder={`Enter ${param.name} (${param.type})`}
                              className="mt-1"
                            />
                          </div>
                        ))}
                    </div>
                  </div>
                  <Button className="w-full gap-2">
                    <Play className="h-4 w-4" />
                    Execute Tool
                  </Button>
                  <Card className="bg-zinc-50">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm">Response</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <pre className="text-xs font-mono">
                        {JSON.stringify({ status: "Ready to execute" }, null, 2)}
                      </pre>
                    </CardContent>
                  </Card>
                </>
              ) : (
                <div className="flex items-center justify-center h-full text-zinc-500">
                  Select a tool to begin testing
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* System Configuration */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Settings className="h-5 w-5" />
                System Configuration
              </CardTitle>
              <CardDescription>
                Feature flags, API limits, timeouts, and retry settings
              </CardDescription>
            </div>
            <Button variant="outline" size="sm">
              Save Changes
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Key</TableHead>
                <TableHead>Category</TableHead>
                <TableHead>Value</TableHead>
                <TableHead>Description</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {configItems.map((item) => (
                <TableRow key={item.key}>
                  <TableCell className="font-mono text-sm">{item.key}</TableCell>
                  <TableCell>
                    <Badge className={getCategoryColor(item.category)}>{item.category}</Badge>
                  </TableCell>
                  <TableCell>
                    <Input defaultValue={item.value} className="w-32" />
                  </TableCell>
                  <TableCell className="text-sm text-zinc-500">{item.description}</TableCell>
                  <TableCell>
                    <Button variant="outline" size="sm">
                      Reset
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Debug Logs Viewer */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Terminal className="h-5 w-5" />
                Debug Logs Viewer
              </CardTitle>
              <CardDescription>Real-time log streaming with filtering and search</CardDescription>
            </div>
            <Button variant="outline" size="sm" className="gap-2">
              <Download className="h-4 w-4" />
              Export Logs
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* Filters */}
            <div className="flex gap-4">
              <div className="flex-1">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500" />
                  <Input
                    placeholder="Search logs..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-10"
                  />
                </div>
              </div>
              <div className="flex gap-2">
                {(["ALL", "DEBUG", "INFO", "WARN", "ERROR"] as const).map((level) => (
                  <Button
                    key={level}
                    variant={logFilter === level ? "default" : "outline"}
                    size="sm"
                    onClick={() => setLogFilter(level)}
                  >
                    {level}
                  </Button>
                ))}
              </div>
            </div>

            {/* Log Table */}
            <div className="border rounded-lg">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[180px]">Timestamp</TableHead>
                    <TableHead className="w-[80px]">Level</TableHead>
                    <TableHead className="w-[150px]">Service</TableHead>
                    <TableHead>Message</TableHead>
                    <TableHead className="w-[100px]">Metadata</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredLogs.map((log) => (
                    <TableRow key={log.id}>
                      <TableCell className="font-mono text-xs">
                        {new Date(log.timestamp).toLocaleString()}
                      </TableCell>
                      <TableCell>
                        <Badge className={getLevelColor(log.level)}>{log.level}</Badge>
                      </TableCell>
                      <TableCell className="font-mono text-sm">{log.service}</TableCell>
                      <TableCell className="text-sm">{log.message}</TableCell>
                      <TableCell>
                        {log.metadata && (
                          <Button variant="outline" size="sm">
                            <Code className="h-4 w-4" />
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
