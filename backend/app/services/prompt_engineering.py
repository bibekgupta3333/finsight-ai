"""
Prompt Engineering Techniques and Utilities.

Implements few-shot learning, example selection, prompt versioning,
compression, and output format specification.
"""

from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field
from datetime import datetime
import json
import random


class FewShotExample(BaseModel):
    """Represents a single few-shot learning example."""

    input: Dict[str, Any]  # Transaction data
    output: Dict[str, Any]  # Expected fraud decision
    reasoning: str  # Why this example is important
    category: str  # "edge_case", "clear_fraud", "clear_legitimate", etc.
    difficulty: int = 1  # 1=easy, 5=very hard


class PromptVersion(BaseModel):
    """Versioned prompt template for A/B testing."""

    version_id: str
    prompt_text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    performance_metrics: Dict[str, float] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    is_active: bool = True


class OutputSchema(BaseModel):
    """JSON schema specification for LLM output."""

    schema_name: str
    required_fields: List[str]
    field_types: Dict[str, str]
    field_descriptions: Dict[str, str]
    example_output: Dict[str, Any]
    validation_rules: Dict[str, Any] = Field(default_factory=dict)


class FewShotManager:
    """
    Manages few-shot example selection and construction.

    Implements intelligent example selection based on:
    - Diversity (edge cases + clear cases)
    - Relevance to current transaction
    - Difficulty progression
    """

    # Curated fraud detection examples
    EXAMPLE_LIBRARY = [
        FewShotExample(
            input={
                "type": "TRANSFER",
                "amount": 9000000.0,
                "oldbalanceOrg": 9000000.0,
                "newbalanceOrig": 0.0,
                "oldbalanceDest": 0.0,
                "newbalanceDest": 0.0,
            },
            output={
                "is_fraud": True,
                "risk_score": 95,
                "risk_level": "CRITICAL",
                "reasoning": "Large transfer draining entire account with zero destination balance - classic fraud pattern",
            },
            reasoning="Clear high-value fraud case",
            category="clear_fraud",
            difficulty=1,
        ),
        FewShotExample(
            input={
                "type": "PAYMENT",
                "amount": 150.0,
                "oldbalanceOrg": 2000.0,
                "newbalanceOrig": 1850.0,
                "oldbalanceDest": 500.0,
                "newbalanceDest": 650.0,
            },
            output={
                "is_fraud": False,
                "risk_score": 15,
                "risk_level": "LOW",
                "reasoning": "Normal payment amount with proper balance updates on both ends",
            },
            reasoning="Clear legitimate transaction",
            category="clear_legitimate",
            difficulty=1,
        ),
        FewShotExample(
            input={
                "type": "CASH_OUT",
                "amount": 5000.0,
                "oldbalanceOrg": 5000.0,
                "newbalanceOrig": 0.0,
                "oldbalanceDest": 0.0,
                "newbalanceDest": 5000.0,
            },
            output={
                "is_fraud": False,
                "risk_score": 45,
                "risk_level": "MEDIUM",
                "reasoning": "CASH_OUT is inherently risky but balances update correctly. Medium risk for ATM withdrawal.",
            },
            reasoning="Edge case - risky transaction type but legitimate",
            category="edge_case",
            difficulty=3,
        ),
        FewShotExample(
            input={
                "type": "TRANSFER",
                "amount": 200000.0,
                "oldbalanceOrg": 200000.0,
                "newbalanceOrig": 0.0,
                "oldbalanceDest": 0.0,
                "newbalanceDest": 0.0,  # Balance doesn't increase!
            },
            output={
                "is_fraud": True,
                "risk_score": 85,
                "risk_level": "CRITICAL",
                "reasoning": "Money disappears - destination balance doesn't increase despite transfer",
            },
            reasoning="Edge case - balance inconsistency indicates fraud",
            category="edge_case",
            difficulty=4,
        ),
        FewShotExample(
            input={
                "type": "DEBIT",
                "amount": 50.0,
                "oldbalanceOrg": 1000.0,
                "newbalanceOrig": 950.0,
                "oldbalanceDest": 0.0,
                "newbalanceDest": 0.0,
            },
            output={
                "is_fraud": False,
                "risk_score": 10,
                "risk_level": "LOW",
                "reasoning": "Small debit with correct balance update",
            },
            reasoning="Low-risk routine transaction",
            category="clear_legitimate",
            difficulty=1,
        ),
        FewShotExample(
            input={
                "type": "TRANSFER",
                "amount": 1000.0,
                "oldbalanceOrg": 5000.0,
                "newbalanceOrig": 5000.0,  # Balance doesn't change!
                "oldbalanceDest": 2000.0,
                "newbalanceDest": 3000.0,
            },
            output={
                "is_fraud": True,
                "risk_score": 90,
                "risk_level": "CRITICAL",
                "reasoning": "Destination receives money but sender's balance unchanged - impossible unless fraud",
            },
            reasoning="Edge case - sender balance inconsistency",
            category="edge_case",
            difficulty=5,
        ),
        FewShotExample(
            input={
                "type": "PAYMENT",
                "amount": 10000.0,
                "oldbalanceOrg": 15000.0,
                "newbalanceOrig": 5000.0,
                "oldbalanceDest": 8000.0,
                "newbalanceDest": 18000.0,
            },
            output={
                "is_fraud": False,
                "risk_score": 25,
                "risk_level": "LOW",
                "reasoning": "Large payment but balances update correctly on both sides",
            },
            reasoning="High-value legitimate transaction",
            category="clear_legitimate",
            difficulty=2,
        ),
    ]

    def __init__(self, default_count: int = 5):
        """
        Initialize few-shot manager.

        Args:
            default_count: Default number of examples to include
        """
        self.default_count = default_count
        self.examples = self.EXAMPLE_LIBRARY.copy()

    def select_examples(
        self,
        transaction: Optional[Dict[str, Any]] = None,
        count: int = None,
        ensure_diversity: bool = True,
    ) -> List[FewShotExample]:
        """
        Select relevant few-shot examples.

        Args:
            transaction: Current transaction (for relevance scoring)
            count: Number of examples to select
            ensure_diversity: Include mix of easy/hard, fraud/legitimate

        Returns:
            Selected examples
        """
        count = count or self.default_count

        if not ensure_diversity:
            # Random selection
            return random.sample(self.examples, min(count, len(self.examples)))

        # Ensure diversity: mix of categories
        selected = []

        # 1. Include at least one clear fraud case
        fraud_cases = [e for e in self.examples if e.category == "clear_fraud"]
        if fraud_cases:
            selected.append(random.choice(fraud_cases))

        # 2. Include at least one clear legitimate case
        legit_cases = [e for e in self.examples if e.category == "clear_legitimate"]
        if legit_cases:
            selected.append(random.choice(legit_cases))

        # 3. Include edge cases (harder examples)
        edge_cases = [e for e in self.examples if e.category == "edge_case"]
        remaining_count = count - len(selected)

        if edge_cases and remaining_count > 0:
            edge_sample = random.sample(
                edge_cases, min(remaining_count, len(edge_cases))
            )
            selected.extend(edge_sample)

        # 4. Fill remaining with diverse examples
        if len(selected) < count:
            remaining = [e for e in self.examples if e not in selected]
            needed = count - len(selected)
            selected.extend(random.sample(remaining, min(needed, len(remaining))))

        # Sort by difficulty for progressive learning
        selected.sort(key=lambda e: e.difficulty)

        return selected[:count]

    def format_examples(
        self, examples: List[FewShotExample], include_reasoning: bool = True
    ) -> str:
        """
        Format examples as prompt text.

        Args:
            examples: Examples to format
            include_reasoning: Include reasoning for why example is important

        Returns:
            Formatted prompt section
        """
        formatted = "=== FEW-SHOT EXAMPLES ===\n\n"
        formatted += "Learn from these examples before analyzing the new transaction:\n\n"

        for i, ex in enumerate(examples, 1):
            formatted += f"Example {i} ({ex.category}, difficulty: {ex.difficulty}/5):\n"
            formatted += f"INPUT: {json.dumps(ex.input, indent=2)}\n"
            formatted += f"OUTPUT: {json.dumps(ex.output, indent=2)}\n"

            if include_reasoning:
                formatted += f"WHY THIS EXAMPLE: {ex.reasoning}\n"

            formatted += "\n"

        formatted += "Now analyze the NEW transaction using similar reasoning:\n"

        return formatted

    def add_example(self, example: FewShotExample):
        """Add new example to library."""
        self.examples.append(example)

    def get_negative_examples(self) -> str:
        """
        Get examples of what NOT to do.

        Returns:
            Formatted negative examples
        """
        negative = """=== NEGATIVE EXAMPLES (What NOT to do) ===

Example 1: WRONG - Hallucinated data
INPUT: {"type": "TRANSFER", "amount": 5000}
BAD OUTPUT: {
  "is_fraud": true,
  "reasoning": "User has history of fraud" ← NO EVIDENCE in input!
}
CORRECT: Only use data from the transaction. Don't hallucinate user history.

Example 2: WRONG - Ignoring balance inconsistencies
INPUT: {
  "amount": 1000,
  "oldbalanceOrg": 5000,
  "newbalanceOrig": 5000  ← Balance didn't change!
}
BAD OUTPUT: {"is_fraud": false, "reasoning": "Normal transaction"}
CORRECT: Flag balance inconsistencies as high fraud risk.

Example 3: WRONG - Not citing evidence
BAD OUTPUT: {"is_fraud": true, "reasoning": "Looks suspicious"}
CORRECT: Cite specific fields: "newbalanceDest is 0 despite receiving funds"

Example 4: WRONG - Financial advice
BAD OUTPUT: "User should invest this money instead of transferring"
CORRECT: Only analyze fraud risk, never give financial advice.

Example 5: WRONG - Vague risk scores
BAD OUTPUT: {"risk_score": 50, "reasoning": "Medium risk"}
CORRECT: Explain HOW you calculated 50 based on specific features.

"""
        return negative


class PromptCompressor:
    """
    Compress prompts while preserving critical information.

    Techniques:
    - Remove redundant whitespace
    - Eliminate verbose examples
    - Abbreviate repetitive instructions
    - Preserve constraints and schemas
    """

    @staticmethod
    def compress(
        prompt: str,
        max_tokens: int = 1500,
        preserve_sections: List[str] = None,
    ) -> str:
        """
        Compress prompt to fit token budget.

        Args:
            prompt: Full prompt text
            max_tokens: Target token count (approximate)
            preserve_sections: Sections that must be kept (e.g., ["CONSTRAINTS"])

        Returns:
            Compressed prompt
        """
        preserve_sections = preserve_sections or [
            "CONSTRAINTS",
            "OUTPUT REQUIREMENTS",
            "BOUNDARIES",
        ]

        # 1. Split into sections
        sections = []
        current_section = []
        current_header = None

        for line in prompt.split("\n"):
            if line.strip().startswith("==="):
                if current_section:
                    sections.append((current_header, "\n".join(current_section)))
                current_header = line.strip()
                current_section = []
            else:
                current_section.append(line)

        if current_section:
            sections.append((current_header, "\n".join(current_section)))

        # 2. Identify critical sections
        critical = []
        optional = []

        for header, content in sections:
            if header and any(p in header for p in preserve_sections):
                critical.append((header, content))
            else:
                optional.append((header, content))

        # 3. Build compressed prompt
        compressed = []

        # Always include critical sections
        for header, content in critical:
            if header:
                compressed.append(header)
            # Remove redundant whitespace
            if content:
                condensed = "\n".join(
                    line.strip() for line in content.split("\n") if line.strip()
                )
                compressed.append(condensed)

        # 4. Add optional sections until token budget
        estimated_tokens = sum(len(c) for c in compressed) // 4

        for header, content in optional:
            section_tokens = len(content) // 4 if content else 0

            if estimated_tokens + section_tokens < max_tokens:
                if header:
                    compressed.append(header)
                if content:
                    compressed.append(content)
                estimated_tokens += section_tokens
            else:
                # Truncate section
                available_chars = (max_tokens - estimated_tokens) * 4
                if available_chars > 100 and content:
                    if header:
                        compressed.append(header)
                    compressed.append(content[:available_chars] + "\n...(truncated)")
                break

        # Filter out None values before joining
        return "\n".join(c for c in compressed if c is not None)

    @staticmethod
    def remove_examples(prompt: str) -> str:
        """Remove all few-shot examples to save tokens."""
        lines = prompt.split("\n")
        filtered = []

        skip_mode = False
        for line in lines:
            if "Example" in line or "EXAMPLES" in line:
                skip_mode = True
            elif line.strip().startswith("==="):
                skip_mode = False

            if not skip_mode:
                filtered.append(line)

        return "\n".join(filtered)


class OutputFormatter:
    """
    Specify and enforce output format schemas.
    """

    # Pre-defined schemas for common tasks
    FRAUD_DECISION_SCHEMA = OutputSchema(
        schema_name="FraudDecision",
        required_fields=["is_fraud", "risk_score", "risk_level", "reasoning"],
        field_types={
            "is_fraud": "boolean",
            "risk_score": "float (0-100)",
            "risk_level": "string (LOW|MEDIUM|HIGH|CRITICAL)",
            "reasoning": "string",
            "confidence": "float (0.0-1.0)",
            "evidence": "array of strings",
        },
        field_descriptions={
            "is_fraud": "Boolean indicating if transaction is fraudulent",
            "risk_score": "Numeric risk score from 0 (safe) to 100 (definitely fraud)",
            "risk_level": "Categorical risk level: LOW, MEDIUM, HIGH, or CRITICAL",
            "reasoning": "Step-by-step explanation of the decision",
            "confidence": "How confident you are in this decision (0.0 = guessing, 1.0 = certain)",
            "evidence": "List of specific transaction fields that support your decision",
        },
        example_output={
            "is_fraud": True,
            "risk_score": 85.0,
            "risk_level": "CRITICAL",
            "reasoning": "Large transfer (amount=1000000) drains entire account (newbalanceOrig=0) with destination balance unchanged (newbalanceDest=0), indicating money disappeared.",
            "confidence": 0.95,
            "evidence": [
                "amount > 100000 (high-value transaction)",
                "newbalanceOrig == 0 (account drained)",
                "newbalanceDest == 0 (money didn't arrive)",
                "type == TRANSFER (risky transaction type)",
            ],
        },
        validation_rules={
            "risk_score": "Must match risk_level: LOW<40, MEDIUM 40-60, HIGH 60-80, CRITICAL>=80",
            "evidence": "Must cite actual transaction fields, not hallucinate data",
        },
    )

    @staticmethod
    def format_schema_prompt(schema: OutputSchema) -> str:
        """
        Format schema as prompt instruction.

        Args:
            schema: Output schema specification

        Returns:
            Formatted prompt section
        """
        prompt = f"=== OUTPUT FORMAT: {schema.schema_name} ===\n\n"
        prompt += "You MUST respond with valid JSON matching this exact schema:\n\n"

        # Field specifications
        prompt += "REQUIRED FIELDS:\n"
        for field in schema.required_fields:
            field_type = schema.field_types.get(field, "any")
            description = schema.field_descriptions.get(field, "")
            prompt += f"- {field} ({field_type}): {description}\n"

        # Validation rules
        if schema.validation_rules:
            prompt += "\nVALIDATION RULES:\n"
            for rule_name, rule_desc in schema.validation_rules.items():
                prompt += f"- {rule_name}: {rule_desc}\n"

        # Example output
        prompt += "\nEXAMPLE OUTPUT:\n"
        prompt += json.dumps(schema.example_output, indent=2)
        prompt += "\n\nIMPORTANT: Your response must be ONLY the JSON object, no additional text.\n"

        return prompt

    @staticmethod
    def validate_output(
        output_json: str, schema: OutputSchema
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate LLM output against schema.

        Args:
            output_json: LLM's JSON response
            schema: Expected schema

        Returns:
            (is_valid, error_message)
        """
        try:
            parsed = json.loads(output_json)
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {str(e)}"

        # Check required fields
        for field in schema.required_fields:
            if field not in parsed:
                return False, f"Missing required field: {field}"

        # Check types (basic validation)
        for field, expected_type in schema.field_types.items():
            if field in parsed:
                value = parsed[field]

                if "boolean" in expected_type.lower() and not isinstance(value, bool):
                    return False, f"Field {field} should be boolean, got {type(value)}"

                if "float" in expected_type.lower() and not isinstance(
                    value, (int, float)
                ):
                    return False, f"Field {field} should be number, got {type(value)}"

                if "string" in expected_type.lower() and not isinstance(value, str):
                    return False, f"Field {field} should be string, got {type(value)}"

                # Special handling for array types
                if "array" in expected_type.lower() and not isinstance(value, (list, str)):
                    return False, f"Field {field} should be array or string, got {type(value)}"

        # Custom validation rules
        if "risk_score" in schema.validation_rules:
            score = parsed.get("risk_score", 0)
            level = parsed.get("risk_level", "")

            if score < 40 and level != "LOW":
                return False, f"risk_score {score} doesn't match risk_level {level}"
            elif 40 <= score < 60 and level != "MEDIUM":
                return False, f"risk_score {score} doesn't match risk_level {level}"
            elif 60 <= score < 80 and level != "HIGH":
                return False, f"risk_score {score} doesn't match risk_level {level}"
            elif score >= 80 and level != "CRITICAL":
                return False, f"risk_score {score} doesn't match risk_level {level}"

        return True, None


class RolePlayingInstructor:
    """
    Generates role-playing instructions for better LLM alignment.
    """

    @staticmethod
    def fraud_specialist_role() -> str:
        """Generate fraud specialist role prompt."""
        return """You are an EXPERT FRAUD DETECTION SPECIALIST with:

BACKGROUND:
- 15 years experience in financial fraud investigation
- Certified Fraud Examiner (CFE)
- Expertise in pattern recognition and risk assessment
- Deep knowledge of fraud schemes (account takeover, money laundering, etc.)

WORKING PRINCIPLES:
1. Evidence-based reasoning - every claim must cite transaction data
2. Systematic analysis - check all fraud indicators methodically
3. Conservative approach - flag suspicious patterns for review
4. Clear communication - explain technical findings in simple terms

ANALYTICAL PROCESS:
1. Review transaction basics (type, amount, accounts)
2. Check balance consistency (math must add up)
3. Identify anomalies (unusual patterns, suspicious timing)
4. Consult fraud policies for this transaction type
5. Calculate risk score using weighted factors
6. Provide clear verdict with supporting evidence

CONSTRAINTS:
- Never make assumptions beyond transaction data
- Always show your calculation for risk scores
- If uncertain, err on the side of flagging for review
- Provide actionable recommendations

Now analyze the transaction with this expertise:
"""


# Global instances
_few_shot_manager: Optional[FewShotManager] = None


def get_few_shot_manager() -> FewShotManager:
    """Get global few-shot manager instance."""
    global _few_shot_manager
    if _few_shot_manager is None:
        _few_shot_manager = FewShotManager()
    return _few_shot_manager
