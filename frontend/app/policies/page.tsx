"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  BookOpen,
  Database,
  Edit,
  FileText,
  Plus,
  Target,
  Trash2,
  TrendingUp,
  Upload
} from "lucide-react";
import { useState } from "react";

interface FraudPolicy {
  id: string;
  name: string;
  version: string;
  description: string;
  enabled: boolean;
  effectiveness: number;
  falsePositiveRate: number;
  lastUpdated: string;
  createdBy: string;
}

interface RAGDocument {
  id: string;
  filename: string;
  uploadedAt: string;
  size: number;
  chunks: number;
  embeddings: number;
  avgSimilarity: number;
}

interface RuleConfig {
  id: string;
  name: string;
  type: "THRESHOLD" | "PATTERN" | "VELOCITY" | "BEHAVIOR";
  enabled: boolean;
  priority: number;
  conditions: string;
  action: string;
}

export default function PolicyPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedPolicy, setSelectedPolicy] = useState<string | null>(null);

  // Mock data - Fraud Policies
  const policies: FraudPolicy[] = [
    {
      id: "policy-001",
      name: "High-Value Transfer Policy",
      version: "2.1.0",
      description: "Flags transfers above $10,000 for manual review",
      enabled: true,
      effectiveness: 94.5,
      falsePositiveRate: 2.3,
      lastUpdated: "2026-01-03T14:30:00Z",
      createdBy: "admin@finsight.ai",
    },
    {
      id: "policy-002",
      name: "Unusual Cashout Pattern",
      version: "1.8.2",
      description: "Detects rapid consecutive cashout transactions",
      enabled: true,
      effectiveness: 89.2,
      falsePositiveRate: 5.1,
      lastUpdated: "2025-12-28T10:15:00Z",
      createdBy: "fraud-team@finsight.ai",
    },
    {
      id: "policy-003",
      name: "Account Velocity Anomaly",
      version: "3.0.0",
      description: "Identifies sudden spikes in transaction frequency",
      enabled: false,
      effectiveness: 76.8,
      falsePositiveRate: 12.4,
      lastUpdated: "2025-12-15T08:00:00Z",
      createdBy: "ml-team@finsight.ai",
    },
  ];

  // Mock data - RAG Documents
  const ragDocuments: RAGDocument[] = [
    {
      id: "doc-001",
      filename: "fraud_detection_guidelines_2026.pdf",
      uploadedAt: "2026-01-02T09:00:00Z",
      size: 2.4,
      chunks: 48,
      embeddings: 384,
      avgSimilarity: 0.87,
    },
    {
      id: "doc-002",
      filename: "regulatory_compliance_framework.pdf",
      uploadedAt: "2025-12-20T14:30:00Z",
      size: 3.1,
      chunks: 62,
      embeddings: 384,
      avgSimilarity: 0.82,
    },
    {
      id: "doc-003",
      filename: "transaction_monitoring_best_practices.md",
      uploadedAt: "2025-12-15T11:00:00Z",
      size: 0.8,
      chunks: 24,
      embeddings: 384,
      avgSimilarity: 0.91,
    },
  ];

  // Mock data - Rule Engine
  const rules: RuleConfig[] = [
    {
      id: "rule-001",
      name: "High Amount Threshold",
      type: "THRESHOLD",
      enabled: true,
      priority: 1,
      conditions: "amount > 10000 AND type IN ['TRANSFER', 'CASH_OUT']",
      action: "FLAG_FOR_REVIEW",
    },
    {
      id: "rule-002",
      name: "Rapid Transaction Pattern",
      type: "VELOCITY",
      enabled: true,
      priority: 2,
      conditions: "transaction_count > 5 IN last_10_minutes",
      action: "BLOCK_TEMPORARY",
    },
    {
      id: "rule-003",
      name: "Suspicious Balance Change",
      type: "BEHAVIOR",
      enabled: true,
      priority: 3,
      conditions: "balance_change_ratio > 0.8 AND new_balance < 100",
      action: "REQUIRE_VERIFICATION",
    },
  ];

  const getRuleTypeBadge = (type: RuleConfig["type"]) => {
    const colors = {
      THRESHOLD: "bg-blue-500",
      PATTERN: "bg-purple-500",
      VELOCITY: "bg-orange-500",
      BEHAVIOR: "bg-green-500",
    };
    return <Badge className={colors[type]}>{type}</Badge>;
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Policy & Knowledge Management</h1>
        <p className="text-zinc-500 mt-1">
          Manage fraud policies, RAG knowledge base, and rule engine
        </p>
      </div>

      {/* Fraud Policy CRUD Interface */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Fraud Policies
          </h2>
          <Button className="gap-2">
            <Plus className="h-4 w-4" />
            Create Policy
          </Button>
        </div>

        <div className="grid gap-4">
          {policies.map((policy) => (
            <Card key={policy.id} className={selectedPolicy === policy.id ? "border-blue-500" : ""}>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <CardTitle className="text-lg">{policy.name}</CardTitle>
                      <Badge variant="outline">v{policy.version}</Badge>
                      {policy.enabled ? (
                        <Badge className="bg-green-500">ENABLED</Badge>
                      ) : (
                        <Badge variant="secondary">DISABLED</Badge>
                      )}
                    </div>
                    <CardDescription className="mt-1">{policy.description}</CardDescription>
                  </div>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" className="gap-2">
                      <Edit className="h-4 w-4" />
                      Edit
                    </Button>
                    <Button variant="outline" size="sm" className="gap-2">
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 md:grid-cols-3">
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <Target className="h-4 w-4 text-zinc-500" />
                      <span className="text-sm text-zinc-500">Effectiveness</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Progress value={policy.effectiveness} className="flex-1" />
                      <span className="text-sm font-semibold">{policy.effectiveness}%</span>
                    </div>
                  </div>
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <TrendingUp className="h-4 w-4 text-zinc-500" />
                      <span className="text-sm text-zinc-500">False Positive Rate</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Progress value={policy.falsePositiveRate} className="flex-1" />
                      <span className="text-sm font-semibold">{policy.falsePositiveRate}%</span>
                    </div>
                  </div>
                  <div className="space-y-1">
                    <div className="text-sm">
                      <span className="text-zinc-500">Last Updated:</span>{" "}
                      <span className="font-semibold">
                        {new Date(policy.lastUpdated).toLocaleDateString()}
                      </span>
                    </div>
                    <div className="text-sm">
                      <span className="text-zinc-500">Created By:</span>{" "}
                      <span className="font-semibold">{policy.createdBy}</span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* RAG Knowledge Base Manager */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <BookOpen className="h-5 w-5" />
                RAG Knowledge Base Manager
              </CardTitle>
              <CardDescription>Manage policy documents and vector embeddings</CardDescription>
            </div>
            <Button className="gap-2">
              <Upload className="h-4 w-4" />
              Upload Document
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* Vector Store Statistics */}
            <div className="grid gap-4 md:grid-cols-4">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-zinc-500">Total Documents</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{ragDocuments.length}</div>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-zinc-500">Total Chunks</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {ragDocuments.reduce((sum, doc) => sum + doc.chunks, 0)}
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-zinc-500">Embedding Dimension</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">384</div>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-zinc-500">Avg Similarity</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {(ragDocuments.reduce((sum, doc) => sum + doc.avgSimilarity, 0) / ragDocuments.length).toFixed(2)}
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Document List */}
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Filename</TableHead>
                  <TableHead>Uploaded</TableHead>
                  <TableHead>Size</TableHead>
                  <TableHead>Chunks</TableHead>
                  <TableHead>Embeddings</TableHead>
                  <TableHead>Avg Similarity</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {ragDocuments.map((doc) => (
                  <TableRow key={doc.id}>
                    <TableCell className="font-medium">{doc.filename}</TableCell>
                    <TableCell className="text-sm">
                      {new Date(doc.uploadedAt).toLocaleDateString()}
                    </TableCell>
                    <TableCell>{doc.size} MB</TableCell>
                    <TableCell>{doc.chunks}</TableCell>
                    <TableCell>{doc.embeddings}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Progress value={doc.avgSimilarity * 100} className="w-20" />
                        <span className="text-sm">{doc.avgSimilarity.toFixed(2)}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button variant="outline" size="sm">
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button variant="outline" size="sm">
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* Rule Engine Editor */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Database className="h-5 w-5" />
                Rule Engine Editor
              </CardTitle>
              <CardDescription>Configure fraud detection rules and thresholds</CardDescription>
            </div>
            <Button className="gap-2">
              <Plus className="h-4 w-4" />
              Create Rule
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Rule Name</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Priority</TableHead>
                <TableHead>Conditions</TableHead>
                <TableHead>Action</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rules.map((rule) => (
                <TableRow key={rule.id}>
                  <TableCell className="font-medium">{rule.name}</TableCell>
                  <TableCell>{getRuleTypeBadge(rule.type)}</TableCell>
                  <TableCell>
                    <Badge variant="outline">P{rule.priority}</Badge>
                  </TableCell>
                  <TableCell className="max-w-xs">
                    <code className="text-xs bg-zinc-100 px-2 py-1 rounded">{rule.conditions}</code>
                  </TableCell>
                  <TableCell>
                    <Badge variant="secondary">{rule.action}</Badge>
                  </TableCell>
                  <TableCell>
                    {rule.enabled ? (
                      <Badge className="bg-green-500">ENABLED</Badge>
                    ) : (
                      <Badge variant="secondary">DISABLED</Badge>
                    )}
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-2">
                      <Button variant="outline" size="sm">
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button variant="outline" size="sm">
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
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
