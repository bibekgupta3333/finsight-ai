"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  Bell,
  BellRing,
  Check,
  Mail,
  MessageSquare,
  Shield,
  X,
} from "lucide-react";
import { useState } from "react";

type AlertSeverity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
type NotificationChannel = "EMAIL" | "SMS" | "SLACK" | "WEBHOOK";

interface AlertRule {
  id: string;
  name: string;
  description: string;
  severity: AlertSeverity;
  condition: string;
  channels: NotificationChannel[];
  enabled: boolean;
}

interface Notification {
  id: string;
  timestamp: string;
  title: string;
  message: string;
  severity: AlertSeverity;
  read: boolean;
  acknowledged: boolean;
}

export default function AlertsPage() {
  const [unreadCount, setUnreadCount] = useState(3);

  // Mock data - Alert Rules
  const alertRules: AlertRule[] = [
    {
      id: "rule-001",
      name: "High-Risk Transaction Detected",
      description: "Alert when transaction risk score exceeds 80",
      severity: "CRITICAL",
      condition: "risk_score > 80",
      channels: ["EMAIL", "SLACK"],
      enabled: true,
    },
    {
      id: "rule-002",
      name: "Circuit Breaker Opened",
      description: "Alert when circuit breaker pattern is triggered",
      severity: "HIGH",
      condition: "circuit_breaker_state = 'OPEN'",
      channels: ["SLACK", "WEBHOOK"],
      enabled: true,
    },
    {
      id: "rule-003",
      name: "Worker Pool Exhausted",
      description: "Alert when worker pool utilization exceeds 90%",
      severity: "MEDIUM",
      condition: "worker_pool_utilization > 90",
      channels: ["EMAIL"],
      enabled: true,
    },
    {
      id: "rule-004",
      name: "Tool Performance Degradation",
      description: "Alert when tool response time exceeds threshold",
      severity: "LOW",
      condition: "avg_response_time > 5000",
      channels: ["SLACK"],
      enabled: false,
    },
  ];

  // Mock data - Recent Notifications
  const notifications: Notification[] = [
    {
      id: "notif-001",
      timestamp: "2026-01-04T12:45:00Z",
      title: "High-Risk Transaction Detected",
      message: "Transaction T12345 flagged with risk score 92. Requires immediate review.",
      severity: "CRITICAL",
      read: false,
      acknowledged: false,
    },
    {
      id: "notif-002",
      timestamp: "2026-01-04T12:30:00Z",
      title: "Circuit Breaker Opened",
      message: "Consensus Voter service circuit breaker opened after 5 consecutive failures.",
      severity: "HIGH",
      read: false,
      acknowledged: false,
    },
    {
      id: "notif-003",
      timestamp: "2026-01-04T12:15:00Z",
      title: "Worker Pool High Utilization",
      message: "Worker pool utilization at 92%. Consider scaling up workers.",
      severity: "MEDIUM",
      read: false,
      acknowledged: true,
    },
    {
      id: "notif-004",
      timestamp: "2026-01-04T12:00:00Z",
      title: "Batch Job Completed",
      message: "Batch job batch-002 completed successfully. 58 frauds detected out of 4850 transactions.",
      severity: "LOW",
      read: true,
      acknowledged: true,
    },
  ];

  const getSeverityBadge = (severity: AlertSeverity) => {
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

  const getChannelIcon = (channel: NotificationChannel) => {
    switch (channel) {
      case "EMAIL":
        return <Mail className="h-3 w-3" />;
      case "SMS":
        return <MessageSquare className="h-3 w-3" />;
      case "SLACK":
        return <MessageSquare className="h-3 w-3" />;
      case "WEBHOOK":
        return <Shield className="h-3 w-3" />;
    }
  };

  const markAsRead = (id: string) => {
    setUnreadCount((prev) => Math.max(0, prev - 1));
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Notifications & Alerts</h1>
          <p className="text-zinc-500 mt-1">
            Configure alert rules and manage notifications
          </p>
        </div>
        <Badge variant="destructive" className="h-8 px-4 text-base">
          {unreadCount} Unread
        </Badge>
      </div>

      {/* Alert Configuration */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <BellRing className="h-5 w-5" />
                Alert Configuration
              </CardTitle>
              <CardDescription>Configure alert rules and notification channels</CardDescription>
            </div>
            <Button className="gap-2">
              <Bell className="h-4 w-4" />
              Create Alert Rule
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Alert Name</TableHead>
                <TableHead>Severity</TableHead>
                <TableHead>Condition</TableHead>
                <TableHead>Channels</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {alertRules.map((rule) => (
                <TableRow key={rule.id}>
                  <TableCell>
                    <div>
                      <div className="font-medium">{rule.name}</div>
                      <div className="text-xs text-zinc-500">{rule.description}</div>
                    </div>
                  </TableCell>
                  <TableCell>{getSeverityBadge(rule.severity)}</TableCell>
                  <TableCell>
                    <code className="text-xs bg-zinc-100 px-2 py-1 rounded">{rule.condition}</code>
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      {rule.channels.map((channel) => (
                        <Badge key={channel} variant="outline" className="gap-1">
                          {getChannelIcon(channel)}
                          {channel}
                        </Badge>
                      ))}
                    </div>
                  </TableCell>
                  <TableCell>
                    {rule.enabled ? (
                      <Badge className="bg-green-500">ENABLED</Badge>
                    ) : (
                      <Badge variant="secondary">DISABLED</Badge>
                    )}
                  </TableCell>
                  <TableCell>
                    <Button variant="outline" size="sm">
                      Edit
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Notification Center */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Bell className="h-5 w-5" />
                Notification Center
              </CardTitle>
              <CardDescription>Recent alerts and notifications</CardDescription>
            </div>
            <Button variant="outline" size="sm">
              Mark All as Read
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {notifications.map((notification) => (
              <Card
                key={notification.id}
                className={`${!notification.read ? "border-blue-500 bg-blue-50" : ""}`}
              >
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <CardTitle className="text-sm">{notification.title}</CardTitle>
                        {getSeverityBadge(notification.severity)}
                        {!notification.read && <Badge className="bg-blue-500">NEW</Badge>}
                      </div>
                      <CardDescription className="text-xs mt-1">
                        {new Date(notification.timestamp).toLocaleString()}
                      </CardDescription>
                    </div>
                    <div className="flex gap-2">
                      {!notification.read && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => markAsRead(notification.id)}
                        >
                          <Check className="h-4 w-4" />
                        </Button>
                      )}
                      <Button variant="outline" size="sm">
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="pb-3">
                  <p className="text-sm text-zinc-700">{notification.message}</p>
                  {notification.acknowledged && (
                    <Badge variant="outline" className="mt-2">
                      Acknowledged
                    </Badge>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Real-Time Alert Stream */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell className="h-5 w-5 animate-pulse" />
            Real-Time Alert Stream
          </CardTitle>
          <CardDescription>Live fraud detection and system health alerts</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="flex items-center gap-3 p-3 bg-red-50 border border-red-200 rounded">
              <Shield className="h-5 w-5 text-red-500" />
              <div className="flex-1">
                <div className="text-sm font-medium text-red-700">
                  CRITICAL: Fraud Pattern Detected
                </div>
                <div className="text-xs text-red-600">
                  Multiple high-risk transactions from same IP address
                </div>
              </div>
              <Badge variant="destructive">LIVE</Badge>
            </div>
            <div className="flex items-center gap-3 p-3 bg-yellow-50 border border-yellow-200 rounded">
              <Shield className="h-5 w-5 text-yellow-500" />
              <div className="flex-1">
                <div className="text-sm font-medium text-yellow-700">
                  MEDIUM: High API Usage Detected
                </div>
                <div className="text-xs text-yellow-600">
                  API rate limit threshold reached: 95/100 requests
                </div>
              </div>
              <Badge className="bg-yellow-500">LIVE</Badge>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
