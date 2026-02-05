"""
Prompt Engineering Service for Fraud Detection

Implements multiple prompting strategies:
- Zero-shot: Direct instruction
- Few-shot: 5-10 examples
- Chain-of-thought: Step-by-step reasoning
- ReAct: Reasoning + Acting pattern
- Self-consistency: Multiple reasoning paths

With versioning and A/B testing support.
"""

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from enum import Enum


class PromptStrategy(str, Enum):
    """Prompt strategy types"""
    ZERO_SHOT = "zero_shot"
    FEW_SHOT = "few_shot"
    CHAIN_OF_THOUGHT = "chain_of_thought"
    REACT = "react"
    SELF_CONSISTENCY = "self_consistency"


@dataclass
class Example:
    """Few-shot example"""
    transaction: Dict[str, Any]
    analysis: str
    verdict: str  # "fraud" or "legitimate"
    confidence: float


@dataclass
class PromptTemplate:
    """Prompt template with metadata"""
    template_id: str
    name: str
    strategy: PromptStrategy
    version: str
    system_prompt: str
    user_prompt_template: str
    examples: List[Example]
    created_at: str
    performance_metrics: Optional[Dict[str, float]] = None
    active: bool = True


class PromptManager:
    """Manage prompt templates and A/B testing"""

    def __init__(self, prompts_dir: str = "data/prompts"):
        # Use absolute path from project root
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent.parent.parent
        self.prompts_dir = project_root / prompts_dir
        self.prompts_dir.mkdir(exist_ok=True, parents=True)

        # Template registry
        self.registry_file = self.prompts_dir / "prompt_registry.json"
        self.registry: Dict[str, PromptTemplate] = self._load_registry()

        # Initialize default templates if registry is empty
        if not self.registry:
            self._initialize_default_templates()

    def _load_registry(self) -> Dict[str, PromptTemplate]:
        """Load prompt registry from disk"""
        if self.registry_file.exists():
            with open(self.registry_file, 'r') as f:
                data = json.load(f)
                return {
                    k: PromptTemplate(**v) for k, v in data.items()
                }
        return {}

    def _save_registry(self):
        """Save prompt registry to disk"""
        with open(self.registry_file, 'w') as f:
            json.dump(
                {k: asdict(v) for k, v in self.registry.items()},
                f, indent=2
            )

    def _initialize_default_templates(self):
        """Initialize default prompt templates"""

        # Default few-shot examples
        default_examples = [
            Example(
                transaction={
                    "type": "TRANSFER",
                    "amount": 181.00,
                    "oldbalanceOrg": 181.00,
                    "newbalanceOrig": 0.00,
                    "oldbalanceDest": 0.00,
                    "newbalanceDest": 0.00
                },
                analysis="Small transfer that drains the entire origin account balance and goes to a new destination account with zero prior balance. Classic money mule pattern.",
                verdict="fraud",
                confidence=0.95
            ),
            Example(
                transaction={
                    "type": "PAYMENT",
                    "amount": 9644.94,
                    "oldbalanceOrg": 9644.94,
                    "newbalanceOrig": 0.00,
                    "oldbalanceDest": 0.00,
                    "newbalanceDest": 9644.94
                },
                analysis="Normal payment transaction. Amount matches the available balance, and payment type is low-risk. Destination account properly credited.",
                verdict="legitimate",
                confidence=0.90
            ),
            Example(
                transaction={
                    "type": "CASH_OUT",
                    "amount": 229133.94,
                    "oldbalanceOrg": 15325.00,
                    "newbalanceOrig": 0.00,
                    "oldbalanceDest": 5083.00,
                    "newbalanceDest": 51513.44
                },
                analysis="CRITICAL: Cash-out amount exceeds origin balance by 15x. This is mathematically impossible in a legitimate transaction. Clear fraud indicator.",
                verdict="fraud",
                confidence=0.99
            ),
            Example(
                transaction={
                    "type": "DEBIT",
                    "amount": 4098.78,
                    "oldbalanceOrg": 503264.00,
                    "newbalanceOrig": 499165.22,
                    "oldbalanceDest": 0.00,
                    "newbalanceDest": 0.00
                },
                analysis="Regular debit transaction. Amount is small relative to account balance. Balances reconcile correctly (old - amount = new). No fraud indicators.",
                verdict="legitimate",
                confidence=0.92
            ),
            Example(
                transaction={
                    "type": "TRANSFER",
                    "amount": 850002.52,
                    "oldbalanceOrg": 6925650.00,
                    "newbalanceOrig": 0.00,
                    "oldbalanceDest": 3007312.00,
                    "newbalanceDest": 0.00
                },
                analysis="Large transfer with suspicious characteristics: origin balance zeroed out completely, destination also zeroed (possible further transfer). High-value transaction warrants investigation.",
                verdict="fraud",
                confidence=0.87
            )
        ]

        # 1. Zero-Shot Template
        self.register_template(
            name="Zero-Shot Fraud Detection",
            strategy=PromptStrategy.ZERO_SHOT,
            version="1.0",
            system_prompt="""You are an expert fraud detection analyst. Analyze financial transactions and determine if they are fraudulent or legitimate.

Consider these key fraud indicators:
- Balance inconsistencies (amount > available balance)
- Unusual transaction patterns (account drainage, round-trip transfers)
- High-risk transaction types (TRANSFER, CASH_OUT)
- Destination account behavior (new accounts, suspicious patterns)

Provide a clear verdict: FRAUD or LEGITIMATE.""",
            user_prompt_template="""Analyze this transaction:

Type: {type}
Amount: ${amount:,.2f}
Origin Balance: ${oldbalanceOrg:,.2f} → ${newbalanceOrig:,.2f}
Destination Balance: ${oldbalanceDest:,.2f} → ${newbalanceDest:,.2f}

Is this transaction fraudulent? Explain your reasoning and provide a confidence score (0-1).""",
            examples=[]
        )

        # 2. Few-Shot Template
        self.register_template(
            name="Few-Shot Fraud Detection",
            strategy=PromptStrategy.FEW_SHOT,
            version="1.0",
            system_prompt="""You are an expert fraud detection analyst. Learn from these examples and apply the same reasoning to new transactions.""",
            user_prompt_template="""Here are some example analyses:

{examples}

Now analyze this transaction:

Type: {type}
Amount: ${amount:,.2f}
Origin Balance: ${oldbalanceOrg:,.2f} → ${newbalanceOrig:,.2f}
Destination Balance: ${oldbalanceDest:,.2f} → ${newbalanceDest:,.2f}

Provide your analysis, verdict (FRAUD or LEGITIMATE), and confidence score (0-1).""",
            examples=default_examples
        )

        # 3. Chain-of-Thought Template
        self.register_template(
            name="Chain-of-Thought Fraud Detection",
            strategy=PromptStrategy.CHAIN_OF_THOUGHT,
            version="1.0",
            system_prompt="""You are an expert fraud detection analyst. Use step-by-step reasoning to analyze transactions.

Follow this thought process:
1. Verify balance consistency
2. Check transaction type risk
3. Analyze amount patterns
4. Examine destination behavior
5. Synthesize findings
6. Make final verdict""",
            user_prompt_template="""Analyze this transaction step-by-step:

Transaction Details:
- Type: {type}
- Amount: ${amount:,.2f}
- Origin: ${oldbalanceOrg:,.2f} → ${newbalanceOrig:,.2f}
- Destination: ${oldbalanceDest:,.2f} → ${newbalanceDest:,.2f}

Think through each step:

Step 1 - Balance Check:
[Is amount ≤ oldbalanceOrg? Does oldbalanceOrg - amount = newbalanceOrig?]

Step 2 - Transaction Type Risk:
[Is this a high-risk type (TRANSFER, CASH_OUT)?]

Step 3 - Amount Analysis:
[Is the amount unusually large or suspiciously round?]

Step 4 - Destination Behavior:
[Does destination balance make sense? Any red flags?]

Step 5 - Pattern Recognition:
[Does this match known fraud patterns?]

Step 6 - Final Verdict:
[FRAUD or LEGITIMATE with confidence 0-1]""",
            examples=[]
        )

        # 4. ReAct Template
        self.register_template(
            name="ReAct Fraud Detection",
            strategy=PromptStrategy.REACT,
            version="1.0",
            system_prompt="""You are an expert fraud detection agent using the ReAct (Reasoning + Acting) framework.

Available Actions:
- calculate(expression): Perform calculations
- check_balance(old, amount, new): Verify balance consistency
- check_pattern(transaction): Check against fraud patterns
- final_verdict(verdict, confidence, reasoning): Make final decision

Use this format:
Thought: [your reasoning]
Action: [action to take]
Observation: [result of action]
... (repeat Thought/Action/Observation as needed)
Thought: [final reasoning]
Action: final_verdict(verdict="FRAUD|LEGITIMATE", confidence=0.X, reasoning="...")""",
            user_prompt_template="""Analyze this transaction using ReAct:

Type: {type}
Amount: ${amount:,.2f}
Origin Balance: ${oldbalanceOrg:,.2f} → ${newbalanceOrig:,.2f}
Destination Balance: ${oldbalanceDest:,.2f} → ${newbalanceDest:,.2f}

Begin your analysis:""",
            examples=[]
        )

        # 5. Self-Consistency Template
        self.register_template(
            name="Self-Consistency Fraud Detection",
            strategy=PromptStrategy.SELF_CONSISTENCY,
            version="1.0",
            system_prompt="""You are an expert fraud detection analyst. Generate multiple independent reasoning paths and check for consistency.

For each path, analyze the transaction from a different angle:
Path 1: Financial balance perspective
Path 2: Transaction pattern perspective
Path 3: Risk profile perspective

Then reconcile the conclusions.""",
            user_prompt_template="""Analyze this transaction from 3 different perspectives:

Transaction:
- Type: {type}
- Amount: ${amount:,.2f}
- Origin: ${oldbalanceOrg:,.2f} → ${newbalanceOrig:,.2f}
- Destination: ${oldbalanceDest:,.2f} → ${newbalanceDest:,.2f}

Path 1 - Financial Balance Analysis:
[Focus on mathematical consistency of balances]

Path 2 - Pattern Recognition:
[Focus on known fraud patterns]

Path 3 - Risk Assessment:
[Focus on transaction type and amount risk]

Final Reconciliation:
[Do all paths agree? What's the consensus verdict and confidence?]""",
            examples=[]
        )

    def register_template(self,
                         name: str,
                         strategy: PromptStrategy,
                         version: str,
                         system_prompt: str,
                         user_prompt_template: str,
                         examples: List[Example]) -> str:
        """Register a new prompt template"""
        template_id = f"{strategy.value}_v{version}_{datetime.now().strftime('%Y%m%d')}"

        template = PromptTemplate(
            template_id=template_id,
            name=name,
            strategy=strategy,
            version=version,
            system_prompt=system_prompt,
            user_prompt_template=user_prompt_template,
            examples=examples,
            created_at=datetime.now().isoformat()
        )

        self.registry[template_id] = template
        self._save_registry()

        return template_id

    def get_template(self, template_id: str) -> Optional[PromptTemplate]:
        """Get template by ID"""
        return self.registry.get(template_id)

    def get_active_template(self, strategy: PromptStrategy) -> Optional[PromptTemplate]:
        """Get active template for a strategy"""
        templates = [
            t for t in self.registry.values()
            if t.strategy == strategy and t.active
        ]

        # Return latest version
        if templates:
            return sorted(templates, key=lambda x: x.version, reverse=True)[0]
        return None

    def list_templates(self, strategy: Optional[PromptStrategy] = None) -> List[PromptTemplate]:
        """List all templates, optionally filtered by strategy"""
        templates = list(self.registry.values())

        if strategy:
            templates = [t for t in templates if t.strategy == strategy]

        return sorted(templates, key=lambda x: x.created_at, reverse=True)

    def render_prompt(self,
                     template_id: str,
                     transaction: Dict[str, Any]) -> Dict[str, str]:
        """
        Render a prompt template with transaction data

        Returns:
            {"system": "...", "user": "..."}
        """
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")

        # Render examples for few-shot
        examples_text = ""
        if template.examples:
            examples_parts = []
            for i, ex in enumerate(template.examples, 1):
                examples_parts.append(f"""Example {i}:
Type: {ex.transaction['type']}
Amount: ${ex.transaction['amount']:,.2f}
Origin: ${ex.transaction['oldbalanceOrg']:,.2f} → ${ex.transaction['newbalanceOrig']:,.2f}
Destination: ${ex.transaction['oldbalanceDest']:,.2f} → ${ex.transaction['newbalanceDest']:,.2f}

Analysis: {ex.analysis}
Verdict: {ex.verdict.upper()}
Confidence: {ex.confidence}
""")
            examples_text = "\n".join(examples_parts)

        # Render user prompt
        user_prompt = template.user_prompt_template.format(
            type=transaction.get('type', 'UNKNOWN'),
            amount=transaction.get('amount', 0),
            oldbalanceOrg=transaction.get('oldbalanceOrg', 0),
            newbalanceOrig=transaction.get('newbalanceOrig', 0),
            oldbalanceDest=transaction.get('oldbalanceDest', 0),
            newbalanceDest=transaction.get('newbalanceDest', 0),
            examples=examples_text
        )

        return {
            "system": template.system_prompt,
            "user": user_prompt
        }

    def update_performance(self,
                          template_id: str,
                          metrics: Dict[str, float]):
        """Update template performance metrics"""
        if template_id in self.registry:
            self.registry[template_id].performance_metrics = metrics
            self._save_registry()

    def compare_templates(self) -> List[Dict[str, Any]]:
        """Compare all templates by performance"""
        results = []

        for template in self.registry.values():
            result = {
                'template_id': template.template_id,
                'name': template.name,
                'strategy': template.strategy.value,
                'version': template.version,
                'active': template.active,
                'created_at': template.created_at
            }

            if template.performance_metrics:
                result.update(template.performance_metrics)

            results.append(result)

        return results

    def ab_test_config(self,
                      variant_a: str,
                      variant_b: str,
                      traffic_split: float = 0.5) -> Dict[str, Any]:
        """
        Create A/B test configuration

        Args:
            variant_a: Template ID for variant A
            variant_b: Template ID for variant B
            traffic_split: Fraction of traffic to variant A (0.5 = 50/50 split)
        """
        template_a = self.get_template(variant_a)
        template_b = self.get_template(variant_b)

        if not template_a or not template_b:
            raise ValueError("Both template IDs must exist")

        config = {
            'test_id': f"ab_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'variant_a': {
                'template_id': variant_a,
                'name': template_a.name,
                'traffic_weight': traffic_split
            },
            'variant_b': {
                'template_id': variant_b,
                'name': template_b.name,
                'traffic_weight': 1 - traffic_split
            },
            'created_at': datetime.now().isoformat(),
            'status': 'active'
        }

        # Save test config
        test_file = self.prompts_dir / f"{config['test_id']}.json"
        with open(test_file, 'w') as f:
            json.dump(config, f, indent=2)

        return config


# Global instance
prompt_manager = PromptManager()
