"""
Advanced Reasoning Patterns for LLM-based Fraud Detection.

Implements ReAct, Chain-of-Thought (CoT), Tree-of-Thought (ToT),
Debate/Critique, Self-Critique, and Reflection patterns.
"""

from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
import json
import asyncio
import logging

logger = logging.getLogger(__name__)


class ReasoningStep(BaseModel):
    """Represents a single reasoning step."""

    step_number: int
    step_type: str  # "thought", "action", "observation", "decision"
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    confidence: Optional[float] = None
    evidence: List[str] = Field(default_factory=list)


class ReActStep(BaseModel):
    """ReAct pattern step: Thought → Action → Observation."""

    thought: str  # Reasoning about what to do
    action: str  # Tool/function to call
    action_input: Dict[str, Any]  # Parameters for action
    observation: Optional[str] = None  # Result of action
    confidence: float = 0.0


class CoTStep(BaseModel):
    """Chain-of-Thought reasoning step."""

    step_number: int
    reasoning: str
    intermediate_result: Optional[Any] = None
    validation: Optional[str] = None  # Validate this step
    backtrack: bool = False  # Should we backtrack?


class ToTNode(BaseModel):
    """Tree-of-Thought exploration node."""

    node_id: str
    parent_id: Optional[str] = None
    depth: int
    reasoning_path: List[str]
    current_state: Dict[str, Any]
    score: float = 0.0  # Quality of this reasoning path
    children: List[str] = Field(default_factory=list)
    is_terminal: bool = False
    decision: Optional[str] = None


class DebatePosition(str, Enum):
    """Debate agent positions."""

    PROSECUTOR = "prosecutor"  # Argues FOR fraud
    DEFENSE = "defense"  # Argues AGAINST fraud
    JUDGE = "judge"  # Makes final decision


class DebateArgument(BaseModel):
    """Argument in a debate."""

    position: DebatePosition
    argument: str
    evidence: List[str]
    confidence: float
    rebuttal_to: Optional[str] = None  # ID of argument being rebutted


class ReActPattern:
    """
    ReAct: Reasoning + Acting pattern.

    Interleaves reasoning (thoughts) with actions (tool calls)
    to solve problems step-by-step.
    """

    def __init__(self, max_steps: int = 10):
        """
        Initialize ReAct pattern.

        Args:
            max_steps: Maximum reasoning steps before forcing decision
        """
        self.max_steps = max_steps
        self.steps: List[ReActStep] = []

    async def execute(
        self,
        initial_context: Dict[str, Any],
        available_tools: Dict[str, callable],
        llm_client: Any,
    ) -> Dict[str, Any]:
        """
        Execute ReAct reasoning loop.

        Args:
            initial_context: Initial transaction data
            available_tools: Dict of tool_name -> function
            llm_client: LLM client for reasoning

        Returns:
            Final decision with reasoning trace
        """
        context = initial_context.copy()

        for step_num in range(self.max_steps):
            # 1. THOUGHT: What should I do next?
            thought_prompt = self._build_thought_prompt(context, step_num)
            thought_response_dict = await llm_client.generate(thought_prompt)
            # Extract text from Ollama response dict
            thought_response = self._extract_response_text(thought_response_dict)

            # Parse thought and action
            thought_data = self._parse_thought(thought_response)

            if thought_data.get("should_decide", False):
                # Agent decided it has enough information
                break

            # 2. ACTION: Call the chosen tool
            action_name = thought_data.get("action")
            action_input = thought_data.get("action_input", {})

            if action_name not in available_tools:
                observation = f"Error: Tool '{action_name}' not available"
            else:
                try:
                    tool_func = available_tools[action_name]
                    observation = await tool_func(**action_input)
                except Exception as e:
                    observation = f"Error executing {action_name}: {str(e)}"

            # 3. OBSERVATION: Record the result
            step = ReActStep(
                thought=thought_data.get("reasoning", ""),
                action=action_name,
                action_input=action_input,
                observation=str(observation),
                confidence=thought_data.get("confidence", 0.5),
            )
            self.steps.append(step)

            # Update context with observation
            context["previous_steps"] = [
                {
                    "thought": s.thought,
                    "action": s.action,
                    "observation": s.observation,
                }
                for s in self.steps
            ]

        # 4. DECISION: Make final decision based on all observations
        decision_prompt = self._build_decision_prompt(context)
        decision_dict = await llm_client.generate(decision_prompt)
        decision = self._extract_response_text(decision_dict)

        return {
            "decision": decision,
            "reasoning_steps": len(self.steps),
            "trace": [s.model_dump() for s in self.steps],
        }

    def _build_thought_prompt(self, context: Dict[str, Any], step: int) -> str:
        """Build prompt for thought generation."""
        previous = context.get("previous_steps", [])

        prompt = f"""You are analyzing a transaction for fraud. Think step-by-step.

TRANSACTION: {context.get('transaction', {})}

PREVIOUS STEPS:
{json.dumps(previous, indent=2) if previous else 'None yet'}

AVAILABLE TOOLS:
- calculate_risk_score: Calculate risk based on features
- query_fraud_policy: Check policy for specific transaction type
- check_history: Look for similar past transactions

STEP {step + 1}/{self.max_steps}

Think: What should I do next to determine if this is fraud?
- What information do I still need?
- Which tool would help me get that information?
- Do I have enough to make a decision?

Respond in JSON:
{{
  "reasoning": "Your thought process...",
  "action": "tool_name or null if ready to decide",
  "action_input": {{"param": "value"}},
  "confidence": 0.0-1.0,
  "should_decide": false or true
}}
"""
        return prompt

    def _extract_response_text(self, response_dict: Dict[str, Any]) -> str:
        """Extract text from Ollama response dictionary."""
        if isinstance(response_dict, str):
            return response_dict
        # Ollama returns dict with 'response' field containing the text
        return response_dict.get("response", str(response_dict))

    def _parse_thought(self, response: str) -> Dict[str, Any]:
        """Parse LLM's thought response."""
        try:
            # Extract text from GenerateResponse if needed
            response_text = response.text if hasattr(response, 'text') else str(response)
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Fallback: extract any JSON-like content
            return {
                "reasoning": str(response),
                "action": None,
                "should_decide": True,
                "confidence": 0.5,
            }

    def _build_decision_prompt(self, context: Dict[str, Any]) -> str:
        """Build prompt for final decision."""
        return f"""Based on all your investigation, make a final fraud decision.

TRANSACTION: {context.get('transaction', {})}

YOUR INVESTIGATION:
{json.dumps(context.get('previous_steps', []), indent=2)}

Make your final decision in JSON:
{{
  "is_fraud": true/false,
  "risk_score": 0-100,
  "reasoning": "Explain your decision based on evidence",
  "confidence": 0.0-1.0,
  "evidence": ["fact1", "fact2", ...]
}}
"""


class ChainOfThoughtPattern:
    """
    Chain-of-Thought (CoT) reasoning.

    Forces LLM to show intermediate reasoning steps before final answer.
    Validates each step for consistency.
    """

    def __init__(self, steps_required: int = 5):
        """
        Initialize CoT pattern.

        Args:
            steps_required: Minimum reasoning steps required
        """
        self.steps_required = steps_required
        self.reasoning_chain: List[CoTStep] = []

    def _extract_response_text(self, response_dict: Dict[str, Any]) -> str:
        """Extract text from Ollama response dictionary."""
        if isinstance(response_dict, str):
            return response_dict
        return response_dict.get("response", str(response_dict))

    async def execute(
        self, transaction: Dict[str, Any], llm_client: Any
    ) -> Dict[str, Any]:
        """
        Execute chain-of-thought reasoning.

        Args:
            transaction: Transaction to analyze
            llm_client: LLM client

        Returns:
            Decision with validated reasoning chain
        """
        prompt = f"""Analyze this transaction for fraud using EXPLICIT step-by-step reasoning.

TRANSACTION: {json.dumps(transaction, indent=2)}

Show your reasoning in {self.steps_required} clear steps:

Step 1: Analyze transaction type and amount
- What type is this? (TRANSFER, CASH_OUT, etc.)
- Is the amount unusual? Compare to typical ranges.
- Intermediate conclusion: ...

Step 2: Evaluate sender and receiver behavior
- Are there red flags in account patterns?
- Is this a known fraud pattern?
- Intermediate conclusion: ...

Step 3: Check timing and frequency
- Is the timestamp suspicious?
- Are there rapid successive transactions?
- Intermediate conclusion: ...

Step 4: Apply fraud detection policies
- Which policies apply to this transaction type?
- Are any policy thresholds exceeded?
- Intermediate conclusion: ...

Step 5: Calculate final risk score
- Combine all indicators
- Weight each factor
- Final risk score: ...

FINAL DECISION:
- Is fraud: true/false
- Risk score: 0-100
- Confidence: 0.0-1.0
- Summary: ...

Respond in JSON with each step clearly labeled.
"""

        response_dict = await llm_client.generate(prompt)
        response = self._extract_response_text(response_dict)

        # Parse and validate reasoning chain
        parsed = self._parse_cot_response(response)

        # Validate consistency across steps
        is_valid, error = self._validate_chain(parsed)

        if not is_valid:
            # Backtrack and regenerate
            return await self._backtrack_and_retry(transaction, llm_client, error)

        return parsed

    def _parse_cot_response(self, response: str) -> Dict[str, Any]:
        """Parse CoT response into structured steps."""
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Extract steps from text
            steps = []
            lines = response.split("\n")
            current_step = None

            for line in lines:
                if line.startswith("Step "):
                    if current_step:
                        steps.append(current_step)
                    current_step = {"reasoning": line}
                elif current_step:
                    current_step["reasoning"] += "\n" + line

            if current_step:
                steps.append(current_step)

            return {"steps": steps, "decision": "parsed from text"}

    def _validate_chain(
        self, parsed: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Validate reasoning chain for consistency."""
        steps = parsed.get("steps", [])

        if len(steps) < self.steps_required:
            return False, f"Insufficient reasoning steps: {len(steps)} < {self.steps_required}"

        # Check for contradictions
        conclusions = [s.get("intermediate_conclusion", "") for s in steps]

        # Simple contradiction check: look for opposing terms
        positive_terms = ["legitimate", "safe", "normal", "low risk"]
        negative_terms = ["fraud", "suspicious", "abnormal", "high risk"]

        has_positive = any(
            any(term in conc.lower() for term in positive_terms) for conc in conclusions
        )
        has_negative = any(
            any(term in conc.lower() for term in negative_terms) for conc in conclusions
        )

        if has_positive and has_negative:
            # Mixed signals - require explicit reconciliation
            final_decision = parsed.get("decision", {})
            if "reconcile" not in str(final_decision).lower():
                return False, "Contradictory intermediate conclusions without reconciliation"

        return True, None

    async def _backtrack_and_retry(
        self, transaction: Dict[str, Any], llm_client: Any, error: str
    ) -> Dict[str, Any]:
        """Backtrack on validation failure and retry."""
        retry_prompt = f"""Your previous reasoning had an issue: {error}

Rethink the analysis for this transaction:
{json.dumps(transaction, indent=2)}

This time, ensure:
1. All steps are consistent with each other
2. If you find conflicting signals, explicitly reconcile them
3. Show your reasoning for resolving any contradictions

Provide updated reasoning in JSON format.
"""

        response_dict = await llm_client.generate(retry_prompt)
        response = self._extract_response_text(response_dict)
        return self._parse_cot_response(response)


class TreeOfThoughtPattern:
    """
    Tree-of-Thought (ToT) exploration.

    Explores multiple reasoning paths simultaneously and selects the best one.
    """

    def __init__(self, branching_factor: int = 3, max_depth: int = 4):
        """
        Initialize ToT pattern.

        Args:
            branching_factor: How many alternative paths to explore per node
            max_depth: Maximum depth of reasoning tree
        """
        self.branching_factor = branching_factor
        self.max_depth = max_depth
        self.tree: Dict[str, ToTNode] = {}
        self.node_counter = 0

    def _extract_response_text(self, response_dict: Dict[str, Any]) -> str:
        """Extract text from Ollama response dictionary."""
        if isinstance(response_dict, str):
            return response_dict
        return response_dict.get("response", str(response_dict))

    async def execute(
        self, transaction: Dict[str, Any], llm_client: Any
    ) -> Dict[str, Any]:
        """
        Explore reasoning tree and select best path.

        Args:
            transaction: Transaction to analyze
            llm_client: LLM client

        Returns:
            Best decision path with alternatives explored
        """
        # Create root node
        root = ToTNode(
            node_id="node_0",
            depth=0,
            reasoning_path=[],
            current_state={"transaction": transaction, "analysis": {}},
        )
        self.tree["node_0"] = root
        self.node_counter = 1

        # Explore tree breadth-first
        await self._explore_node(root, llm_client)

        # Find best terminal node
        best_node = self._select_best_path()

        return {
            "decision": best_node.decision,
            "reasoning_path": best_node.reasoning_path,
            "score": best_node.score,
            "alternatives_explored": len(self.tree),
            "tree_depth": best_node.depth,
        }

    async def _explore_node(self, node: ToTNode, llm_client: Any):
        """Explore a single node by generating alternative continuations."""
        if node.depth >= self.max_depth:
            # Terminal node - make decision
            node.is_terminal = True
            node.decision = await self._make_decision(node, llm_client)
            node.score = await self._score_path(node, llm_client)
            return

        # Generate alternative reasoning steps
        alternatives = await self._generate_alternatives(node, llm_client)

        # Create child nodes for each alternative
        for alt in alternatives[:self.branching_factor]:
            child_id = f"node_{self.node_counter}"
            self.node_counter += 1

            child = ToTNode(
                node_id=child_id,
                parent_id=node.node_id,
                depth=node.depth + 1,
                reasoning_path=node.reasoning_path + [alt["step"]],
                current_state={
                    **node.current_state,
                    "analysis": {
                        **node.current_state.get("analysis", {}),
                        **alt.get("new_state", {}),
                    },
                },
            )

            self.tree[child_id] = child
            node.children.append(child_id)

            # Recursively explore child
            await self._explore_node(child, llm_client)

    async def _generate_alternatives(
        self, node: ToTNode, llm_client: Any
    ) -> List[Dict[str, Any]]:
        """Generate alternative reasoning steps from current node."""
        prompt = f"""You're analyzing a transaction for fraud. Generate {self.branching_factor} DIFFERENT reasoning approaches.

TRANSACTION: {node.current_state.get('transaction', {})}

REASONING SO FAR:
{json.dumps(node.reasoning_path, indent=2) if node.reasoning_path else 'Starting analysis'}

Generate {self.branching_factor} alternative next steps. Each should:
1. Focus on a different aspect (amount, timing, pattern, etc.)
2. Lead to potentially different conclusions
3. Be based on actual transaction data

Respond in JSON:
{{
  "alternatives": [
    {{
      "step": "Focus on X aspect: ...",
      "new_state": {{"key": "value"}},
      "rationale": "Why this approach..."
    }},
    ...
  ]
}}
"""

        response_dict = await llm_client.generate(prompt)
        response = self._extract_response_text(response_dict)

        try:
            data = json.loads(response)
            return data.get("alternatives", [])
        except json.JSONDecodeError:
            # Fallback: create single default alternative
            return [
                {
                    "step": f"Continue analysis at depth {node.depth}",
                    "new_state": {},
                    "rationale": "Default continuation",
                }
            ]

    async def _make_decision(self, node: ToTNode, llm_client: Any) -> str:
        """Make final decision at terminal node."""
        prompt = f"""Based on this reasoning path, make a final fraud decision.

TRANSACTION: {node.current_state.get('transaction', {})}

REASONING PATH:
{json.dumps(node.reasoning_path, indent=2)}

Decide in JSON:
{{
  "is_fraud": true/false,
  "risk_score": 0-100,
  "confidence": 0.0-1.0,
  "reasoning": "..."
}}
"""

        response_dict = await llm_client.generate(prompt)
        return self._extract_response_text(response_dict)

    async def _score_path(self, node: ToTNode, llm_client: Any) -> float:
        """Score the quality of a reasoning path."""
        # Simple scoring: longer paths with more evidence = better
        path_length_score = min(len(node.reasoning_path) / self.max_depth, 1.0)

        # Could add LLM-based scoring here
        return path_length_score

    def _select_best_path(self) -> ToTNode:
        """Select terminal node with highest score."""
        terminal_nodes = [n for n in self.tree.values() if n.is_terminal]

        if not terminal_nodes:
            # Return root if no terminal nodes
            return self.tree["node_0"]

        return max(terminal_nodes, key=lambda n: n.score)


class DebatePattern:
    """
    Debate/Critique pattern.

    Multiple agents argue different positions, then a judge decides.
    """

    def __init__(self, rounds: int = 3):
        """
        Initialize debate pattern.

        Args:
            rounds: Number of back-and-forth debate rounds
        """
        self.rounds = rounds
        self.arguments: List[DebateArgument] = []

    def _extract_response_text(self, response_dict: Dict[str, Any]) -> str:
        """Extract text from Ollama response dictionary."""
        if isinstance(response_dict, str):
            return response_dict
        return response_dict.get("response", str(response_dict))

    async def execute(
        self, transaction: Dict[str, Any], llm_client: Any
    ) -> Dict[str, Any]:
        """
        Run debate between prosecutor and defense agents.

        Args:
            transaction: Transaction to analyze
            llm_client: LLM client

        Returns:
            Judge's final decision with debate history
        """
        for round_num in range(self.rounds):
            # Prosecutor argues FOR fraud
            prosecutor_arg = await self._generate_argument(
                position=DebatePosition.PROSECUTOR,
                transaction=transaction,
                previous_arguments=self.arguments,
                llm_client=llm_client,
            )
            self.arguments.append(prosecutor_arg)

            # Defense argues AGAINST fraud
            defense_arg = await self._generate_argument(
                position=DebatePosition.DEFENSE,
                transaction=transaction,
                previous_arguments=self.arguments,
                llm_client=llm_client,
            )
            self.arguments.append(defense_arg)

        # Judge makes final decision
        judgment = await self._judge_debate(transaction, llm_client)

        return {
            "decision": judgment,
            "debate_rounds": self.rounds,
            "arguments": [a.model_dump() for a in self.arguments],
        }

    async def _generate_argument(
        self,
        position: DebatePosition,
        transaction: Dict[str, Any],
        previous_arguments: List[DebateArgument],
        llm_client: Any,
    ) -> DebateArgument:
        """Generate argument for given position."""
        if position == DebatePosition.PROSECUTOR:
            role = "You are a PROSECUTOR arguing this transaction IS fraud."
            goal = "Find evidence that suggests fraud."
        else:
            role = "You are a DEFENSE attorney arguing this transaction is LEGITIMATE."
            goal = "Find evidence that suggests it's a normal transaction."

        previous_text = "\n\n".join(
            f"{arg.position.value.upper()}: {arg.argument}" for arg in previous_arguments
        )

        prompt = f"""{role}

TRANSACTION: {json.dumps(transaction, indent=2)}

PREVIOUS ARGUMENTS:
{previous_text if previous_text else "No previous arguments"}

YOUR GOAL: {goal}

Build your argument:
1. Cite specific evidence from transaction data
2. Address opponent's previous points if any
3. Provide confidence level

Respond in JSON:
{{
  "argument": "Your main argument...",
  "evidence": ["fact1", "fact2", ...],
  "confidence": 0.0-1.0,
  "rebuttal": "Response to opponent's last point (if any)"
}}
"""

        response_dict = await llm_client.generate(prompt)
        response = self._extract_response_text(response_dict)

        try:
            data = json.loads(response)
            return DebateArgument(
                position=position,
                argument=data.get("argument", ""),
                evidence=data.get("evidence", []),
                confidence=data.get("confidence", 0.5),
                rebuttal_to=None,  # Could track which arg is being rebutted
            )
        except json.JSONDecodeError:
            return DebateArgument(
                position=position,
                argument=response,
                evidence=[],
                confidence=0.5,
            )

    async def _judge_debate(
        self, transaction: Dict[str, Any], llm_client: Any
    ) -> str:
        """Judge weighs both sides and makes decision."""
        arguments_summary = "\n\n".join(
            f"{arg.position.value.upper()} (confidence: {arg.confidence}):\n"
            f"Argument: {arg.argument}\n"
            f"Evidence: {', '.join(arg.evidence)}"
            for arg in self.arguments
        )

        prompt = f"""You are a JUDGE in a fraud detection case.

TRANSACTION: {json.dumps(transaction, indent=2)}

ARGUMENTS PRESENTED:
{arguments_summary}

Weigh both sides and make your final decision:
1. Which side presented stronger evidence?
2. Are there any unaddressed points?
3. What's the overall weight of evidence?

Decide in JSON:
{{
  "is_fraud": true/false,
  "risk_score": 0-100,
  "confidence": 0.0-1.0,
  "reasoning": "Explanation of your judgment",
  "winning_arguments": ["prosecutor point 1", "defense point 2", ...]
}}
"""

        response_dict = await llm_client.generate(prompt)
        return self._extract_response_text(response_dict)


class SelfCritiquePattern:
    """
    Self-Critique pattern.

    LLM generates explanation, then critiques and revises its own output.
    """

    def _extract_response_text(self, response_dict: Dict[str, Any]) -> str:
        """Extract text from Ollama response dictionary."""
        if isinstance(response_dict, str):
            return response_dict
        return response_dict.get("response", str(response_dict))

    async def execute(
        self, transaction: Dict[str, Any], llm_client: Any, max_iterations: int = 3
    ) -> Dict[str, Any]:
        """
        Generate → Critique → Revise loop.

        Args:
            transaction: Transaction to analyze
            llm_client: LLM client
            max_iterations: Maximum critique-revise cycles

        Returns:
            Final revised decision
        """
        # 1. Initial generation
        current_analysis = await self._generate_initial(transaction, llm_client)

        revisions = []

        for iteration in range(max_iterations):
            # 2. Self-critique
            critique = await self._critique_analysis(
                transaction, current_analysis, llm_client
            )

            # 3. Check if revision needed
            if not critique.get("needs_revision", False):
                break

            # 4. Revise based on critique
            revised = await self._revise_analysis(
                transaction, current_analysis, critique, llm_client
            )

            revisions.append(
                {
                    "iteration": iteration + 1,
                    "critique": critique,
                    "revised": revised,
                }
            )

            current_analysis = revised

        return {
            "final_analysis": current_analysis,
            "revision_count": len(revisions),
            "revisions": revisions,
        }

    async def _generate_initial(
        self, transaction: Dict[str, Any], llm_client: Any
    ) -> str:
        """Generate initial fraud analysis."""
        prompt = f"""Analyze this transaction for fraud:

{json.dumps(transaction, indent=2)}

Provide your analysis in JSON:
{{
  "is_fraud": true/false,
  "risk_score": 0-100,
  "reasoning": "Your explanation",
  "evidence": ["fact1", "fact2", ...]
}}
"""
        response_dict = await llm_client.generate(prompt)
        return self._extract_response_text(response_dict)

    async def _critique_analysis(
        self, transaction: Dict[str, Any], analysis: str, llm_client: Any
    ) -> Dict[str, Any]:
        """Critique your own analysis."""
        prompt = f"""Review your own fraud analysis for errors or weak reasoning.

TRANSACTION: {json.dumps(transaction, indent=2)}

YOUR ANALYSIS:
{analysis}

Critique your work:
1. Are there logical inconsistencies?
2. Did you cite actual evidence or make assumptions?
3. Is the risk score justified by the evidence?
4. Did you miss any important factors?

Respond in JSON:
{{
  "needs_revision": true/false,
  "issues_found": ["issue1", "issue2", ...],
  "suggestions": "How to improve the analysis"
}}
"""

        response = await llm_client.generate(prompt)
        try:
            # Extract text from GenerateResponse if needed
            response_text = response.text if hasattr(response, 'text') else str(response)
            return json.loads(response_text)
        except json.JSONDecodeError:
            return {"needs_revision": False, "issues_found": [], "suggestions": ""}

    async def _revise_analysis(
        self,
        transaction: Dict[str, Any],
        original: str,
        critique: Dict[str, Any],
        llm_client: Any,
    ) -> str:
        """Revise analysis based on self-critique."""
        prompt = f"""Revise your fraud analysis based on your own critique.

TRANSACTION: {json.dumps(transaction, indent=2)}

ORIGINAL ANALYSIS:
{original}

YOUR CRITIQUE:
{json.dumps(critique, indent=2)}

Provide REVISED analysis addressing the issues:
"""

        response_dict = await llm_client.generate(prompt)
        return self._extract_response_text(response_dict)


class ReflectionPattern:
    """
    Reflection loop: Check decision against policy, validate reasoning, escalate if uncertain.
    """

    def _extract_response_text(self, response_dict: Dict[str, Any]) -> str:
        """Extract text from Ollama response dictionary."""
        if isinstance(response_dict, str):
            return response_dict
        return response_dict.get("response", str(response_dict))

    async def execute(
        self,
        decision: Dict[str, Any],
        transaction: Dict[str, Any],
        policies: List[str],
        llm_client: Any,
    ) -> Dict[str, Any]:
        """
        Reflect on decision and validate against policies.

        Args:
            decision: Initial fraud decision
            transaction: Original transaction
            policies: List of fraud detection policies
            llm_client: LLM client

        Returns:
            Validated decision or escalation recommendation
        """
        # 1. Policy alignment check
        policy_check = await self._check_policy_alignment(
            decision, policies, llm_client
        )

        # 2. Reasoning chain validation
        reasoning_check = await self._validate_reasoning_chain(decision, llm_client)

        # 3. Uncertainty check
        uncertainty = decision.get("confidence", 1.0)

        # 4. Determine if escalation needed
        should_escalate = (
            not policy_check.get("aligned", True)
            or not reasoning_check.get("valid", True)
            or uncertainty < 0.7
        )

        return {
            "original_decision": decision,
            "policy_alignment": policy_check,
            "reasoning_validation": reasoning_check,
            "should_escalate": should_escalate,
            "escalation_reason": self._get_escalation_reason(
                policy_check, reasoning_check, uncertainty
            ),
        }

    async def _check_policy_alignment(
        self, decision: Dict[str, Any], policies: List[str], llm_client: Any
    ) -> Dict[str, Any]:
        """Check if decision aligns with policies."""
        prompt = f"""Check if this fraud decision aligns with policies.

DECISION:
{json.dumps(decision, indent=2)}

POLICIES:
{chr(10).join(f"{i+1}. {p}" for i, p in enumerate(policies))}

Validate:
1. Does the decision cite relevant policies?
2. Are policy thresholds correctly applied?
3. Any policy violations?

Respond in JSON:
{{
  "aligned": true/false,
  "issues": ["issue1", ...],
  "policy_citations": ["policy1", ...]
}}
"""

        response = await llm_client.generate(prompt)
        try:
            # Extract text from GenerateResponse if needed
            response_text = response.text if hasattr(response, 'text') else str(response)
            return json.loads(response_text)
        except json.JSONDecodeError:
            return {"aligned": True, "issues": [], "policy_citations": []}

    async def _validate_reasoning_chain(
        self, decision: Dict[str, Any], llm_client: Any
    ) -> Dict[str, Any]:
        """Validate logical consistency of reasoning."""
        prompt = f"""Validate the logical consistency of this reasoning.

DECISION:
{json.dumps(decision, indent=2)}

Check for:
1. Logical contradictions
2. Unjustified leaps in logic
3. Missing evidence for claims

Respond in JSON:
{{
  "valid": true/false,
  "issues": ["issue1", ...],
  "confidence": 0.0-1.0
}}
"""

        response = await llm_client.generate(prompt)
        try:
            # Extract text from GenerateResponse if needed
            response_text = response.text if hasattr(response, 'text') else str(response)
            return json.loads(response_text)
        except json.JSONDecodeError:
            return {"valid": True, "issues": [], "confidence": 1.0}

    def _get_escalation_reason(
        self,
        policy_check: Dict[str, Any],
        reasoning_check: Dict[str, Any],
        uncertainty: float,
    ) -> str:
        """Determine reason for escalation."""
        reasons = []

        if not policy_check.get("aligned", True):
            reasons.append(f"Policy misalignment: {policy_check.get('issues', [])}")

        if not reasoning_check.get("valid", True):
            reasons.append(
                f"Reasoning issues: {reasoning_check.get('issues', [])}"
            )

        if uncertainty < 0.7:
            reasons.append(f"Low confidence: {uncertainty:.2f}")

        return " | ".join(reasons) if reasons else "No escalation needed"
