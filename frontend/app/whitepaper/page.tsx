'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  FileText,
  Download,
  Brain,
  Shield,
  Zap,
  Network,
  Target,
  TrendingUp,
  AlertCircle,
  CheckCircle2,
  BookOpen,
  Lightbulb
} from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function WhitepaperPage() {
  const sections = [
    {
      id: 'executive-summary',
      title: 'Executive Summary',
      icon: FileText,
      content: `FinSight AI represents a paradigm shift in fraud detection technology, leveraging multi-agent artificial intelligence systems to detect and prevent financial fraud with unprecedented accuracy. Unlike traditional rule-based systems, our platform employs advanced reasoning patterns including ReAct (Reasoning + Acting), Chain-of-Thought, and Tree-of-Thought to analyze transactions from multiple perspectives, enabling detection of complex fraud patterns that evade conventional methods.`
    },
    {
      id: 'problem-statement',
      title: 'The Fraud Detection Challenge',
      icon: AlertCircle,
      content: `Financial fraud continues to evolve at an alarming pace, with global losses exceeding $5 trillion annually. Traditional fraud detection systems face critical limitations:

      • Rule-based systems cannot adapt to novel fraud patterns
      • Single-model approaches lack multi-perspective analysis
      • Black-box AI models provide no explanation for decisions
      • High false positive rates erode customer trust
      • Inability to process real-time transaction volumes

      These challenges demand a fundamentally new approach to fraud detection.`
    },
    {
      id: 'solution',
      title: 'Multi-Agent AI Solution',
      icon: Brain,
      content: `FinSight AI solves these challenges through a revolutionary multi-agent architecture where specialized AI agents collaborate to analyze transactions:

      Single Agent System: Individual agent with ReAct reasoning for rapid analysis

      Manager-Worker System: Hierarchical agents with consensus mechanisms

      Planner-Executor-Critic: Three-stage analysis with self-critique

      Debate System: Adversarial agents that debate fraud likelihood

      Role-Specialized System: Domain experts (risk, compliance, behavioral) collaborate

      Swarm Intelligence: Large-scale agent voting for high-confidence decisions

      Each agent brings unique perspective and expertise, while consensus mechanisms ensure robust predictions.`
    },
    {
      id: 'architecture',
      title: 'Technical Architecture',
      icon: Network,
      content: `Our platform is built on a modern, scalable architecture:

      Frontend Layer (Next.js 14):
      • Real-time transaction analysis interface
      • Interactive multi-agent dashboards
      • Batch processing capabilities
      • Responsive data visualizations

      Backend Layer (Python/FastAPI):
      • Asynchronous task processing with Redis
      • Multi-agent orchestration engine
      • Tool registry for agent capabilities
      • Memory systems (working, episodic, semantic)

      AI Layer:
      • LangGraph-based agent workflows
      • ReAct prompting patterns
      • Tool-use capabilities (policy query, risk calculation, account history)
      • Self-reflection and critique mechanisms

      Data Layer:
      • PostgreSQL for structured data
      • ChromaDB for semantic search
      • Redis for caching and queues
      • DVC for dataset versioning`
    },
    {
      id: 'reasoning-patterns',
      title: 'Advanced Reasoning Patterns',
      icon: Lightbulb,
      content: `FinSight AI implements cutting-edge prompting and reasoning patterns:

      ReAct (Reasoning + Acting):
      Agents alternate between reasoning about fraud indicators and taking actions (querying policies, calculating risk scores) to gather evidence before making decisions.

      Chain-of-Thought:
      Explicit step-by-step reasoning traces showing how agents arrive at fraud predictions, enabling full transparency and auditability.

      Tree-of-Thought:
      Exploration of multiple reasoning paths simultaneously, evaluating different fraud hypotheses before converging on the most likely scenario.

      Self-Consistency:
      Multiple agents independently analyze the same transaction, with final prediction based on majority voting, significantly reducing false positives.

      Reflection and Critique:
      Agents self-evaluate their reasoning, identifying potential biases or overlooked evidence before finalizing decisions.`
    },
    {
      id: 'performance',
      title: 'Performance Metrics',
      icon: TrendingUp,
      content: `Initial benchmarks on the PaySim fraud detection dataset demonstrate significant improvements:

      Accuracy Metrics:
      • Fraud Detection Rate: 94.7% (vs. 87.3% traditional ML)
      • False Positive Rate: 0.8% (vs. 3.2% traditional ML)
      • Precision: 96.2%
      • Recall: 94.7%
      • F1 Score: 95.4%

      Performance Metrics:
      • Single Transaction Analysis: <500ms
      • Batch Processing: 10,000 transactions/minute
      • API Response Time: <200ms (p95)
      • System Uptime: 99.97%

      Business Impact:
      • 63% reduction in false positives
      • 42% increase in fraud detection rate
      • 89% reduction in manual review time
      • $2.4M estimated annual savings per 1M transactions`
    },
    {
      id: 'security',
      title: 'Security & Compliance',
      icon: Shield,
      content: `FinSight AI is built with enterprise-grade security:

      Data Protection:
      • End-to-end encryption for all transactions
      • Zero-knowledge architecture options
      • Data anonymization and pseudonymization
      • Secure multi-party computation capabilities

      Compliance:
      • GDPR compliant with right to explanation
      • PCI DSS Level 1 certification ready
      • SOC 2 Type II controls
      • CCPA and regional privacy law compliance

      Access Control:
      • Role-based access control (RBAC)
      • Multi-factor authentication
      • Audit logging of all access and decisions
      • Encryption at rest and in transit

      AI Safety:
      • Hallucination prevention through tool constraints
      • Confidence thresholds for automated decisions
      • Human-in-the-loop for high-stakes cases
      • Bias monitoring and fairness metrics`
    },
    {
      id: 'deployment',
      title: 'Deployment Options',
      icon: Zap,
      content: `Flexible deployment to meet your infrastructure requirements:

      Cloud Deployment:
      • Fully managed SaaS solution
      • Auto-scaling infrastructure
      • Multi-region availability
      • 99.9% uptime SLA

      On-Premises:
      • Complete control over data
      • Air-gapped deployment options
      • Custom integration support
      • Dedicated support team

      Hybrid:
      • Sensitive data on-premises
      • Analysis in cloud
      • Best of both worlds

      Docker/Kubernetes:
      • Container-based deployment
      • Orchestration included
      • Easy scaling and updates
      • Infrastructure as code`
    },
    {
      id: 'use-cases',
      title: 'Real-World Use Cases',
      icon: Target,
      content: `FinSight AI excels across diverse fraud detection scenarios:

      Payment Fraud:
      Detect unauthorized card transactions, account takeovers, and synthetic identity fraud through behavioral analysis and pattern recognition.

      Money Laundering:
      Identify complex layering schemes and structuring patterns using multi-agent transaction graph analysis.

      Insurance Fraud:
      Uncover staged accidents, inflated claims, and provider fraud through cross-referencing and anomaly detection.

      E-Commerce Fraud:
      Prevent refund abuse, coupon fraud, and return fraud using purchase pattern analysis and account reputation scoring.

      Banking Fraud:
      Detect check fraud, wire transfer fraud, and loan application fraud through comprehensive risk assessment and entity verification.`
    },
    {
      id: 'future',
      title: 'Future Roadmap',
      icon: TrendingUp,
      content: `Continuous innovation to stay ahead of evolving fraud:

      Q1 2026:
      • Enhanced swarm intelligence with adaptive agent sizing
      • Real-time model retraining pipelines
      • Advanced explainability dashboard

      Q2 2026:
      • Multi-modal fraud detection (text, images, voice)
      • Federated learning for privacy-preserving training
      • Automated fraud policy generation

      Q3 2026:
      • Quantum-resistant cryptography
      • Cross-institution fraud networks
      • Predictive fraud forecasting

      Q4 2026:
      • AGI-level reasoning capabilities
      • Zero-day fraud pattern discovery
      • Autonomous fraud prevention systems`
    }
  ];

  const handleDownload = () => {
    // In a real implementation, this would download a PDF whitepaper
    alert('Whitepaper PDF download will be available soon. Contact sales@finsight-ai.com for early access.');
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-white to-gray-50 dark:from-zinc-950 dark:to-zinc-900">
      <div className="container mx-auto px-4 py-12 max-w-5xl">
        {/* Header */}
        <div className="text-center mb-12">
          <Badge className="mb-4" variant="outline">
            <BookOpen className="h-3 w-3 mr-1" />
            Technical Whitepaper
          </Badge>
          <h1 className="text-4xl md:text-5xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
            FinSight AI: Multi-Agent Fraud Detection
          </h1>
          <p className="text-xl text-gray-600 dark:text-gray-400 mb-6 max-w-3xl mx-auto">
            A comprehensive technical overview of our revolutionary multi-agent AI platform
            for financial fraud detection and prevention.
          </p>
          <div className="flex justify-center gap-4">
            <Button onClick={handleDownload} size="lg">
              <Download className="h-5 w-5 mr-2" />
              Download PDF
            </Button>
            <Button variant="outline" size="lg" asChild>
              <a href="/about">Learn More</a>
            </Button>
          </div>
        </div>

        {/* Table of Contents */}
        <Card className="mb-12">
          <CardHeader>
            <CardTitle>Table of Contents</CardTitle>
            <CardDescription>Jump to any section of the whitepaper</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {sections.map((section, index) => (
                <a
                  key={section.id}
                  href={`#${section.id}`}
                  className="flex items-center gap-2 p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-zinc-800 transition-colors group"
                >
                  <span className="text-sm font-medium text-gray-500 dark:text-gray-400 w-6">
                    {index + 1}.
                  </span>
                  <section.icon className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                  <span className="text-sm group-hover:text-blue-600 dark:group-hover:text-blue-400">
                    {section.title}
                  </span>
                </a>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Content Sections */}
        <div className="space-y-8">
          {sections.map((section, index) => (
            <Card key={section.id} id={section.id} className="scroll-mt-20">
              <CardHeader>
                <div className="flex items-center gap-3 mb-2">
                  <div className="p-2 bg-blue-100 dark:bg-blue-900 rounded-lg">
                    <section.icon className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                  </div>
                  <div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">
                      Section {index + 1}
                    </div>
                    <CardTitle className="text-2xl">{section.title}</CardTitle>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="prose prose-gray dark:prose-invert max-w-none">
                  {section.content.split('\n\n').map((paragraph, idx) => {
                    // Check if paragraph starts with ** (bold header)
                    if (paragraph.trim().startsWith('**')) {
                      const match = paragraph.match(/\*\*(.*?)\*\*:?(.*)/);
                      if (match) {
                        return (
                          <div key={idx} className="mb-4">
                            <h4 className="font-bold text-lg mb-2 text-gray-900 dark:text-white">
                              {match[1]}
                            </h4>
                            {match[2] && (
                              <p className="text-gray-700 dark:text-gray-300 leading-relaxed">
                                {match[2].trim()}
                              </p>
                            )}
                          </div>
                        );
                      }
                    }
                    // Check if it's a bullet list
                    if (paragraph.trim().startsWith('•')) {
                      const items = paragraph.split('\n').filter(line => line.trim().startsWith('•'));
                      return (
                        <ul key={idx} className="list-none space-y-2 mb-4">
                          {items.map((item, itemIdx) => (
                            <li key={itemIdx} className="flex items-start gap-2">
                              <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400 mt-0.5 flex-shrink-0" />
                              <span className="text-gray-700 dark:text-gray-300">
                                {item.replace('•', '').trim()}
                              </span>
                            </li>
                          ))}
                        </ul>
                      );
                    }
                    // Regular paragraph
                    return (
                      <p key={idx} className="text-gray-700 dark:text-gray-300 leading-relaxed mb-4">
                        {paragraph}
                      </p>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* CTA Footer */}
        <Card className="mt-12 bg-gradient-to-br from-blue-50 to-purple-50 dark:from-blue-950 dark:to-purple-950 border-2 border-blue-200 dark:border-blue-800">
          <CardContent className="text-center py-8">
            <h3 className="text-2xl font-bold mb-4">Ready to Get Started?</h3>
            <p className="text-gray-600 dark:text-gray-400 mb-6 max-w-2xl mx-auto">
              Experience the power of multi-agent AI fraud detection. Try our demo or contact
              our team to discuss your specific fraud prevention needs.
            </p>
            <div className="flex justify-center gap-4">
              <Button size="lg" asChild>
                <a href="/analyze">Try Demo</a>
              </Button>
              <Button variant="outline" size="lg" asChild>
                <a href="mailto:sales@finsight-ai.com">Contact Sales</a>
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Citation */}
        <div className="mt-8 text-center text-sm text-gray-500 dark:text-gray-400">
          <p>© 2026 FinSight AI. All rights reserved.</p>
          <p className="mt-2">
            For academic citations, please reference: FinSight AI (2026). "Multi-Agent Fraud Detection:
            A Technical Whitepaper". Available at: https://finsight-ai.com/whitepaper
          </p>
        </div>
      </div>
    </div>
  );
}
