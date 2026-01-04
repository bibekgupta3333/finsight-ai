"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Layout,
    Maximize,
    Monitor,
    Moon,
    Palette,
    Sun,
    Type,
    User
} from "lucide-react";
import { useState } from "react";

type ThemeMode = "LIGHT" | "DARK" | "SYSTEM";
type ViewDensity = "COMPACT" | "COMFORTABLE" | "SPACIOUS";

interface UserProfile {
  name: string;
  email: string;
  role: string;
  avatar: string;
}

export default function SettingsPage() {
  const [themeMode, setThemeMode] = useState<ThemeMode>("SYSTEM");
  const [viewDensity, setViewDensity] = useState<ViewDensity>("COMFORTABLE");

  const userProfile: UserProfile = {
    name: "John Analyst",
    email: "john.analyst@finsight.ai",
    role: "Senior Fraud Analyst",
    avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=John",
  };

  const widgets = [
    { id: "widget-001", name: "Transaction Overview", enabled: true },
    { id: "widget-002", name: "Fraud Trends Chart", enabled: true },
    { id: "widget-003", name: "Agent Performance", enabled: true },
    { id: "widget-004", name: "Recent Alerts", enabled: false },
    { id: "widget-005", name: "Risk Score Distribution", enabled: true },
    { id: "widget-006", name: "Policy Effectiveness", enabled: false },
  ];

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">User Settings</h1>
        <p className="text-zinc-500 mt-1">
          Manage your profile, preferences, and appearance
        </p>
      </div>

      {/* User Profile Management */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <User className="h-5 w-5" />
            User Profile
          </CardTitle>
          <CardDescription>Update your personal information</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-4">
            <img
              src={userProfile.avatar}
              alt="Avatar"
              className="h-20 w-20 rounded-full border-2 border-zinc-200"
            />
            <Button variant="outline" size="sm">
              Change Avatar
            </Button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="name">Full Name</Label>
              <Input id="name" defaultValue={userProfile.name} className="mt-1" />
            </div>
            <div>
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" defaultValue={userProfile.email} className="mt-1" />
            </div>
            <div>
              <Label htmlFor="role">Role</Label>
              <Input id="role" defaultValue={userProfile.role} className="mt-1" disabled />
            </div>
          </div>

          <div className="space-y-2">
            <Label>Email Notifications</Label>
            <div className="space-y-2">
              <div className="flex items-center justify-between p-3 border rounded">
                <div>
                  <div className="text-sm font-medium">Fraud Alerts</div>
                  <div className="text-xs text-zinc-500">
                    Receive email when high-risk transactions are detected
                  </div>
                </div>
                <Badge className="bg-green-500">ENABLED</Badge>
              </div>
              <div className="flex items-center justify-between p-3 border rounded">
                <div>
                  <div className="text-sm font-medium">System Notifications</div>
                  <div className="text-xs text-zinc-500">
                    Receive email for system health alerts
                  </div>
                </div>
                <Badge className="bg-green-500">ENABLED</Badge>
              </div>
              <div className="flex items-center justify-between p-3 border rounded">
                <div>
                  <div className="text-sm font-medium">Weekly Reports</div>
                  <div className="text-xs text-zinc-500">
                    Receive weekly fraud detection summary
                  </div>
                </div>
                <Badge variant="secondary">DISABLED</Badge>
              </div>
            </div>
          </div>

          <Button>Save Profile Changes</Button>
        </CardContent>
      </Card>

      {/* Dashboard Customization */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Layout className="h-5 w-5" />
            Dashboard Customization
          </CardTitle>
          <CardDescription>Customize your dashboard widgets and views</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label className="mb-2 block">Enabled Widgets</Label>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {widgets.map((widget) => (
                <div
                  key={widget.id}
                  className={`flex items-center justify-between p-3 border rounded ${
                    widget.enabled ? "bg-blue-50 border-blue-200" : ""
                  }`}
                >
                  <div className="text-sm font-medium">{widget.name}</div>
                  {widget.enabled ? (
                    <Badge className="bg-green-500">ENABLED</Badge>
                  ) : (
                    <Badge variant="secondary">DISABLED</Badge>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div>
            <Label className="mb-2 block">Saved Searches</Label>
            <div className="space-y-2">
              <div className="flex items-center justify-between p-3 border rounded">
                <div>
                  <div className="text-sm font-medium">High-Risk Transactions</div>
                  <code className="text-xs bg-zinc-100 px-2 py-0.5 rounded">
                    risk_score &gt; 80 AND amount &gt; 10000
                  </code>
                </div>
                <Button variant="outline" size="sm">
                  Load
                </Button>
              </div>
              <div className="flex items-center justify-between p-3 border rounded">
                <div>
                  <div className="text-sm font-medium">Recent Flagged Cases</div>
                  <code className="text-xs bg-zinc-100 px-2 py-0.5 rounded">
                    status = FLAGGED AND created_at &gt; -7d
                  </code>
                </div>
                <Button variant="outline" size="sm">
                  Load
                </Button>
              </div>
            </div>
          </div>

          <Button>Save Dashboard Settings</Button>
        </CardContent>
      </Card>

      {/* Theme & Appearance */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Palette className="h-5 w-5" />
            Theme & Appearance
          </CardTitle>
          <CardDescription>Customize the look and feel of the application</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label className="mb-2 block">Theme Mode</Label>
            <div className="grid grid-cols-3 gap-3">
              <button
                onClick={() => setThemeMode("LIGHT")}
                className={`flex flex-col items-center gap-2 p-4 border rounded ${
                  themeMode === "LIGHT" ? "border-blue-500 bg-blue-50" : ""
                }`}
              >
                <Sun className="h-6 w-6" />
                <span className="text-sm font-medium">Light</span>
              </button>
              <button
                onClick={() => setThemeMode("DARK")}
                className={`flex flex-col items-center gap-2 p-4 border rounded ${
                  themeMode === "DARK" ? "border-blue-500 bg-blue-50" : ""
                }`}
              >
                <Moon className="h-6 w-6" />
                <span className="text-sm font-medium">Dark</span>
              </button>
              <button
                onClick={() => setThemeMode("SYSTEM")}
                className={`flex flex-col items-center gap-2 p-4 border rounded ${
                  themeMode === "SYSTEM" ? "border-blue-500 bg-blue-50" : ""
                }`}
              >
                <Monitor className="h-6 w-6" />
                <span className="text-sm font-medium">System</span>
              </button>
            </div>
          </div>

          <div>
            <Label className="mb-2 block">View Density</Label>
            <div className="grid grid-cols-3 gap-3">
              <button
                onClick={() => setViewDensity("COMPACT")}
                className={`flex flex-col items-center gap-2 p-4 border rounded ${
                  viewDensity === "COMPACT" ? "border-blue-500 bg-blue-50" : ""
                }`}
              >
                <Maximize className="h-5 w-5" />
                <span className="text-sm font-medium">Compact</span>
              </button>
              <button
                onClick={() => setViewDensity("COMFORTABLE")}
                className={`flex flex-col items-center gap-2 p-4 border rounded ${
                  viewDensity === "COMFORTABLE" ? "border-blue-500 bg-blue-50" : ""
                }`}
              >
                <Maximize className="h-6 w-6" />
                <span className="text-sm font-medium">Comfortable</span>
              </button>
              <button
                onClick={() => setViewDensity("SPACIOUS")}
                className={`flex flex-col items-center gap-2 p-4 border rounded ${
                  viewDensity === "SPACIOUS" ? "border-blue-500 bg-blue-50" : ""
                }`}
              >
                <Maximize className="h-7 w-7" />
                <span className="text-sm font-medium">Spacious</span>
              </button>
            </div>
          </div>

          <div>
            <Label className="mb-2 block">Font Size</Label>
            <div className="flex gap-3">
              <Button variant="outline" size="sm">
                <Type className="h-3 w-3" /> Small
              </Button>
              <Button variant="default" size="sm">
                <Type className="h-4 w-4" /> Medium
              </Button>
              <Button variant="outline" size="sm">
                <Type className="h-5 w-5" /> Large
              </Button>
            </div>
          </div>

          <Button>Apply Appearance Settings</Button>
        </CardContent>
      </Card>
    </div>
  );
}
