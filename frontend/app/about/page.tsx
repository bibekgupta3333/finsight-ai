'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Brain,
  Shield,
  Zap,
  TrendingUp,
  Users,
  Award,
  Target,
  Lightbulb,
  CheckCircle2
} from 'lucide-react';

export default function AboutPage() {
  const features = [
    {
      icon: Brain,
      title: 'Multi-Agent Intelligence',
      description: 'Leverage multiple AI agents working collaboratively to detect fraud patterns with unprecedented accuracy.'
    },
    {
      icon: Shield,
      title: 'Advanced Security',
      description: 'Bank-grade security protocols ensuring your financial data remains protected at all times.'
    },
    {
      icon: Zap,
      title: 'Real-Time Detection',
      description: 'Instant fraud detection and alerting system that responds to threats in milliseconds.'
    },
    {
      icon: TrendingUp,
      title: 'Continuous Learning',
      description: 'AI models that evolve and improve with every transaction analyzed, staying ahead of emerging threats.'
    }
  ];

  const capabilities = [
    'ReAct (Reasoning + Acting) patterns for intelligent decision-making',
    'Chain-of-Thought reasoning for transparent analysis',
    'Tree-of-Thought exploration for complex fraud scenarios',
    'Multi-agent consensus for high-confidence predictions',
    'Real-time transaction monitoring and alerting',
    'Batch processing for large-scale fraud analysis',
    'Explainable AI with detailed reasoning traces',
    'Integration with existing financial systems'
  ];

  const team = [
    {
      role: 'AI Research',
      description: 'Expert team specializing in multi-agent systems and fraud detection algorithms.'
    },
    {
      role: 'Security Engineering',
      description: 'Dedicated security professionals ensuring robust protection of financial data.'
    },
    {
      role: 'Financial Analysis',
      description: 'Experienced analysts with deep domain knowledge in fraud patterns and prevention.'
    }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-b from-white to-gray-50 dark:from-zinc-950 dark:to-zinc-900">
      <div className="container mx-auto px-4 py-12">
        {/* Hero Section */}
        <div className="text-center mb-16">
          <Badge className="mb-4" variant="outline">
            <Award className="h-3 w-3 mr-1" />
            About FinSight AI
          </Badge>
          <h1 className="text-4xl md:text-5xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
            Next-Generation Fraud Detection
          </h1>
          <p className="text-xl text-gray-600 dark:text-gray-400 max-w-3xl mx-auto">
            FinSight AI combines cutting-edge artificial intelligence with advanced reasoning patterns
            to protect financial institutions from fraud with unparalleled accuracy and speed.
          </p>
        </div>

        {/* Mission Section */}
        <Card className="mb-12 border-2 border-blue-200 dark:border-blue-900">
          <CardHeader>
            <div className="flex items-center gap-2 mb-2">
              <Target className="h-6 w-6 text-blue-600" />
              <CardTitle className="text-2xl">Our Mission</CardTitle>
            </div>
            <CardDescription className="text-base">
              To revolutionize fraud detection by harnessing the power of multi-agent AI systems
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-gray-700 dark:text-gray-300 leading-relaxed">
              At FinSight AI, we believe that fighting financial fraud requires more than traditional
              rule-based systems. Our mission is to leverage the latest advances in artificial intelligence,
              particularly multi-agent reasoning systems, to create a fraud detection platform that thinks
              and reasons like expert fraud analysts - but at machine speed and scale.
            </p>
            <p className="text-gray-700 dark:text-gray-300 leading-relaxed mt-4">
              We're building the future of financial security, where AI agents collaborate to analyze
              transactions from multiple perspectives, debate findings, and reach consensus on fraud
              predictions with transparent, explainable reasoning.
            </p>
          </CardContent>
        </Card>

        {/* Core Features Grid */}
        <div className="mb-12">
          <h2 className="text-3xl font-bold mb-8 text-center">Core Features</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {features.map((feature, index) => (
              <Card key={index} className="hover:shadow-lg transition-shadow">
                <CardHeader>
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-blue-100 dark:bg-blue-900 rounded-lg">
                      <feature.icon className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                    </div>
                    <CardTitle>{feature.title}</CardTitle>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-600 dark:text-gray-400">{feature.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>

        {/* Technical Capabilities */}
        <Card className="mb-12">
          <CardHeader>
            <div className="flex items-center gap-2 mb-2">
              <Lightbulb className="h-6 w-6 text-blue-600" />
              <CardTitle className="text-2xl">Technical Capabilities</CardTitle>
            </div>
            <CardDescription>
              Advanced AI patterns and techniques powering our fraud detection system
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {capabilities.map((capability, index) => (
                <div key={index} className="flex items-start gap-2">
                  <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400 mt-0.5 flex-shrink-0" />
                  <span className="text-gray-700 dark:text-gray-300">{capability}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Team Expertise */}
        <div className="mb-12">
          <h2 className="text-3xl font-bold mb-8 text-center">Team Expertise</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {team.map((member, index) => (
              <Card key={index} className="text-center hover:shadow-lg transition-shadow">
                <CardHeader>
                  <div className="flex justify-center mb-3">
                    <div className="p-3 bg-purple-100 dark:bg-purple-900 rounded-full">
                      <Users className="h-8 w-8 text-purple-600 dark:text-purple-400" />
                    </div>
                  </div>
                  <CardTitle>{member.role}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-600 dark:text-gray-400">{member.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>

        {/* CTA Section */}
        <div className="mt-16 text-center">
          <h2 className="text-3xl font-bold mb-4">Ready to Transform Your Fraud Detection?</h2>
          <p className="text-xl text-gray-600 dark:text-gray-400 mb-8 max-w-2xl mx-auto">
            Experience the power of multi-agent AI in protecting your financial operations.
          </p>
          <div className="flex justify-center gap-4">
            <a
              href="/analyze"
              className="px-8 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold transition-colors"
            >
              Try Demo
            </a>
            <a
              href="/whitepaper"
              className="px-8 py-3 bg-white dark:bg-zinc-800 hover:bg-gray-100 dark:hover:bg-zinc-700 text-gray-900 dark:text-white border-2 border-gray-300 dark:border-zinc-600 rounded-lg font-semibold transition-colors"
            >
              Read Whitepaper
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
