"""
LLM Knowledge Service
Provides conceptual understanding and decision frameworks for:
- MoE (Mixture of Experts) routing
- Speculative decoding
- Distillation vs prompting tradeoffs
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field


# ==================== Models ====================

class MoEAnalysis(BaseModel):
    """MoE (Mixture of Experts) routing analysis"""
    model_type: str = Field(..., description="Model type (e.g., Mixtral-8x7B)")
    total_parameters: str = Field(..., description="Total parameter count")
    active_parameters: str = Field(..., description="Active parameters per token")
    num_experts: int = Field(..., description="Number of expert modules")
    experts_per_token: int = Field(..., description="Experts activated per token")
    routing_mechanism: str = Field(..., description="How routing works")
    cost_implications: List[str] = Field(default_factory=list, description="Cost considerations")
    efficiency_benefits: List[str] = Field(default_factory=list, description="Efficiency advantages")
    when_experts_activate: List[str] = Field(default_factory=list, description="Activation patterns")
    best_use_cases: List[str] = Field(default_factory=list, description="Ideal applications")


class SpeculativeDecodingAnalysis(BaseModel):
    """Speculative decoding concept analysis"""
    technique: str = Field(default="Speculative Decoding", description="Technique name")
    draft_model: str = Field(..., description="Smaller draft model")
    verification_model: str = Field(..., description="Larger verification model")
    how_it_works: List[str] = Field(default_factory=list, description="Step-by-step process")
    latency_reduction: str = Field(..., description="Expected speedup")
    benefits: List[str] = Field(default_factory=list, description="Advantages")
    limitations: List[str] = Field(default_factory=list, description="Drawbacks")
    when_applicable: List[str] = Field(default_factory=list, description="Best scenarios")
    fraud_detection_fit: str = Field(..., description="Fit for fraud detection")


class DistillationVsPrompting(BaseModel):
    """Decision framework for distillation vs prompting"""
    scenario: str = Field(..., description="Scenario description")
    data_availability: str = Field(..., description="Available training data")
    task_flexibility: str = Field(..., description="How fixed vs flexible the task is")
    recommendation: Literal["distillation", "prompting", "hybrid"] = Field(..., description="Recommended approach")
    reasoning: List[str] = Field(default_factory=list, description="Why this recommendation")
    tradeoffs: Dict[str, str] = Field(default_factory=dict, description="Approach tradeoffs")
    implementation_complexity: str = Field(..., description="Implementation difficulty")
    cost_performance: str = Field(..., description="Cost-performance profile")


class HybridApproach(BaseModel):
    """Hybrid distillation + prompting strategy"""
    approach_name: str = Field(..., description="Hybrid approach name")
    distillation_component: str = Field(..., description="What to distill")
    prompting_component: str = Field(..., description="What to prompt")
    integration_strategy: str = Field(..., description="How to combine them")
    benefits: List[str] = Field(default_factory=list, description="Hybrid benefits")
    example_workflow: List[str] = Field(default_factory=list, description="Step-by-step example")


class KnowledgeQuery(BaseModel):
    """Query for LLM knowledge"""
    query_type: Literal["moe", "speculative_decoding", "distillation_vs_prompting", "hybrid_approach"] = Field(..., description="Knowledge area")
    context: Optional[str] = Field(default=None, description="Additional context")


# ==================== LLM Knowledge Service ====================

class LLMKnowledge:
    """
    LLM conceptual knowledge and decision frameworks
    Provides guidance on MoE, speculative decoding, and distillation vs prompting
    """

    def __init__(self):
        self.data_dir = Path("data/llm_knowledge")
        self.data_dir.mkdir(parents=True, exist_ok=True)


    def analyze_moe(self, model_type: str = "Mixtral-8x7B") -> MoEAnalysis:
        """
        Analyze Mixture-of-Experts (MoE) architecture

        Args:
            model_type: MoE model to analyze

        Returns:
            MoEAnalysis with routing, cost, and efficiency insights
        """
        # Mixtral-8x7B example (most common MoE model)
        if "mixtral" in model_type.lower() or "8x7b" in model_type.lower():
            analysis = MoEAnalysis(
                model_type="Mixtral-8x7B",
                total_parameters="46.7B parameters",
                active_parameters="12.9B parameters per token",
                num_experts=8,
                experts_per_token=2,
                routing_mechanism="Learned router selects top-2 experts per token based on input context",
                cost_implications=[
                    "Inference cost based on ACTIVE params (12.9B), not total (46.7B)",
                    "~3.6x cheaper than dense 46.7B model for same quality",
                    "Memory footprint is full 46.7B (all experts loaded)",
                    "Compute per token is only for 2 active experts",
                    "Routing adds minimal overhead (<1% latency)"
                ],
                efficiency_benefits=[
                    "2-3x faster inference vs dense model of same quality",
                    "Better specialization: each expert learns specific patterns",
                    "Scalability: can add more experts without proportional compute increase",
                    "Quality matches or exceeds dense 70B models",
                    "Efficient fine-tuning: can update specific experts"
                ],
                when_experts_activate=[
                    "Expert 1-2: Common language patterns, general knowledge",
                    "Expert 3-4: Technical/specialized domains (code, math, science)",
                    "Expert 5-6: Reasoning and analysis tasks",
                    "Expert 7-8: Creative and long-form generation",
                    "Router learns patterns during training",
                    "Different tokens activate different expert combinations"
                ],
                best_use_cases=[
                    "Production deployments requiring quality + efficiency",
                    "Multi-domain tasks (fraud detection + explanations)",
                    "Cost-sensitive applications",
                    "Real-time inference with quality requirements",
                    "Tasks benefiting from specialized knowledge"
                ]
            )
        else:
            # Generic MoE analysis
            analysis = MoEAnalysis(
                model_type=model_type,
                total_parameters="Variable (depends on model)",
                active_parameters="Typically 20-30% of total",
                num_experts=8,
                experts_per_token=2,
                routing_mechanism="Learned router network selects top-k experts",
                cost_implications=[
                    "Cost scales with active parameters, not total",
                    "Memory requirement is full model size",
                    "Routing adds minimal compute overhead"
                ],
                efficiency_benefits=[
                    "Faster than dense model of equal quality",
                    "Better specialization through expert modules",
                    "Scalable architecture"
                ],
                when_experts_activate=[
                    "Experts specialize during training",
                    "Activation depends on input patterns",
                    "Router learns optimal expert selection"
                ],
                best_use_cases=[
                    "Quality-sensitive production systems",
                    "Multi-domain applications",
                    "Cost-performance optimization"
                ]
            )

        # Log query
        self._log_query({
            "timestamp": datetime.now().isoformat(),
            "query_type": "moe_analysis",
            "model_type": model_type
        })

        return analysis


    def analyze_speculative_decoding(
        self,
        draft_model: str = "Mistral-7B-Instruct",
        verification_model: str = "Mixtral-8x7B-Instruct"
    ) -> SpeculativeDecodingAnalysis:
        """
        Analyze speculative decoding technique

        Args:
            draft_model: Smaller, faster draft model
            verification_model: Larger, more accurate verification model

        Returns:
            SpeculativeDecodingAnalysis with concepts and applicability
        """
        analysis = SpeculativeDecodingAnalysis(
            draft_model=draft_model,
            verification_model=verification_model,
            how_it_works=[
                "1. Draft model generates K tokens speculatively (fast)",
                "2. Verification model scores all K tokens in parallel",
                "3. Accept tokens where draft and verification agree",
                "4. Reject first disagreement and continue from there",
                "5. Repeat until completion",
                "Speedup comes from parallel verification vs sequential generation"
            ],
            latency_reduction="2-3x faster for long-form generation (>256 tokens)",
            benefits=[
                "Significant speedup for long outputs",
                "No quality loss (verification model ensures correctness)",
                "Memory-efficient (only small draft model does sequential work)",
                "Adaptive: automatically adjusts to draft model quality",
                "Works with any draft-verification model pair"
            ],
            limitations=[
                "Requires running TWO models (draft + verification)",
                "Memory overhead: both models must be loaded",
                "Minimal speedup for short outputs (<100 tokens)",
                "Draft model quality affects speedup (poor draft = more rejections)",
                "Implementation complexity higher than standard decoding",
                "Not beneficial if draft model is too slow or too inaccurate"
            ],
            when_applicable=[
                "Long-form generation (>256 tokens): reports, explanations, stories",
                "Batch processing: can amortize model loading overhead",
                "Memory-rich environments: can load both models",
                "Quality-critical: verification ensures correctness",
                "Latency-sensitive: 2-3x speedup matters"
            ],
            fraud_detection_fit="Limited fit: fraud detection typically needs short outputs (<256 tokens), where speculative decoding provides minimal speedup. Better for fraud report generation or detailed explanations."
        )

        # Log query
        self._log_query({
            "timestamp": datetime.now().isoformat(),
            "query_type": "speculative_decoding",
            "draft_model": draft_model,
            "verification_model": verification_model
        })

        return analysis


    def decide_distillation_vs_prompting(
        self,
        scenario: str,
        data_size: int = 0,
        task_variability: str = "unknown"
    ) -> DistillationVsPrompting:
        """
        Decision framework: distillation vs prompting

        Args:
            scenario: Task description
            data_size: Number of labeled examples available
            task_variability: "fixed", "variable", "unknown"

        Returns:
            DistillationVsPrompting with recommendation and reasoning
        """
        # Decision logic
        if data_size >= 10000 and task_variability == "fixed":
            recommendation = "distillation"
            reasoning = [
                f"Large dataset ({data_size} examples) enables effective distillation",
                "Fixed task allows specialized student model",
                "Distilled model will be faster and cheaper than prompting",
                "One-time training cost amortized over many inferences"
            ]
            tradeoffs = {
                "cost": "High upfront (training), low ongoing (inference)",
                "flexibility": "Low - hard to change task after distillation",
                "quality": "High - specialized model for this exact task",
                "latency": "Low - small distilled model is fast"
            }
            complexity = "High - requires training pipeline, evaluation, deployment"
            cost_performance = "Best long-term: expensive to set up, cheap to run"

        elif data_size < 100 or task_variability == "variable":
            recommendation = "prompting"
            reasoning = [
                f"Limited data ({data_size} examples) insufficient for distillation",
                "Variable task benefits from prompt flexibility",
                "No training infrastructure needed",
                "Can iterate quickly on prompts"
            ]
            tradeoffs = {
                "cost": "Low upfront, high ongoing (per-inference API costs)",
                "flexibility": "High - change prompts anytime",
                "quality": "Good - large model is capable",
                "latency": "Medium-High - large model is slower"
            }
            complexity = "Low - just write prompts"
            cost_performance = "Good short-term: quick to start, expensive at scale"

        else:
            # Hybrid recommendation
            recommendation = "hybrid"
            reasoning = [
                f"Moderate dataset ({data_size} examples) enables partial distillation",
                "Combine distilled model for core task + prompting for variations",
                "Best of both: efficiency + flexibility",
                "Distill frequent patterns, prompt for edge cases"
            ]
            tradeoffs = {
                "cost": "Medium upfront, medium ongoing",
                "flexibility": "Medium - can handle some variations",
                "quality": "High - specialized core + flexible edge handling",
                "latency": "Low-Medium - fast for common cases"
            }
            complexity = "Medium - requires both approaches"
            cost_performance = "Optimal: balances setup cost and runtime efficiency"

        # Data availability description
        if data_size >= 10000:
            data_availability = f"Large dataset: {data_size} labeled examples"
        elif data_size >= 1000:
            data_availability = f"Moderate dataset: {data_size} labeled examples"
        elif data_size >= 100:
            data_availability = f"Small dataset: {data_size} labeled examples"
        else:
            data_availability = f"Minimal data: {data_size} examples (insufficient for distillation)"

        # Task flexibility
        if task_variability == "fixed":
            task_flexibility = "Fixed task: same inputs/outputs repeatedly"
        elif task_variability == "variable":
            task_flexibility = "Variable task: requirements change frequently"
        else:
            task_flexibility = "Unknown variability: analyze task patterns first"

        decision = DistillationVsPrompting(
            scenario=scenario,
            data_availability=data_availability,
            task_flexibility=task_flexibility,
            recommendation=recommendation,
            reasoning=reasoning,
            tradeoffs=tradeoffs,
            implementation_complexity=complexity,
            cost_performance=cost_performance
        )

        # Log query
        self._log_query({
            "timestamp": datetime.now().isoformat(),
            "query_type": "distillation_vs_prompting",
            "scenario": scenario,
            "data_size": data_size,
            "recommendation": recommendation
        })

        return decision


    def create_hybrid_approach(
        self,
        approach_name: str = "Fraud Detection Hybrid"
    ) -> HybridApproach:
        """
        Create hybrid distillation + prompting strategy

        Args:
            approach_name: Name for the hybrid approach

        Returns:
            HybridApproach with integration strategy
        """
        if "fraud" in approach_name.lower():
            # Fraud detection specific hybrid
            hybrid = HybridApproach(
                approach_name=approach_name,
                distillation_component="Distill classification model (FRAUD/LEGITIMATE) from large model using 10k+ labeled transactions",
                prompting_component="Use prompting for explanations, edge cases, and novel fraud patterns",
                integration_strategy="Route based on confidence: High confidence (>0.9) → distilled model only. Medium (0.7-0.9) → distilled + prompt for explanation. Low (<0.7) → full prompted analysis",
                benefits=[
                    "Fast classification (distilled) for 90% of cases",
                    "Detailed reasoning (prompted) when needed",
                    "Cost-efficient: cheap inference for common cases",
                    "Flexible: can handle new fraud patterns via prompts",
                    "Best quality: distilled for speed, prompted for edge cases"
                ],
                example_workflow=[
                    "1. Run transaction through distilled classifier (fast)",
                    "2. Get prediction + confidence score",
                    "3. If confidence > 0.9: return classification (done)",
                    "4. If confidence 0.7-0.9: get explanation via prompt",
                    "5. If confidence < 0.7: full prompted analysis",
                    "6. Log low-confidence cases for model retraining"
                ]
            )
        else:
            # Generic hybrid approach
            hybrid = HybridApproach(
                approach_name=approach_name,
                distillation_component="Distill core task (classification, extraction, etc.) for frequent patterns",
                prompting_component="Use prompting for variations, explanations, and edge cases",
                integration_strategy="Confidence-based routing: distilled for high confidence, prompted for low confidence",
                benefits=[
                    "Efficiency: fast distilled model for common cases",
                    "Flexibility: prompting handles variations",
                    "Cost optimization: expensive prompts only when needed",
                    "Quality: specialized distilled + capable prompted"
                ],
                example_workflow=[
                    "1. Run input through distilled model",
                    "2. Check confidence score",
                    "3. High confidence: use distilled output",
                    "4. Low confidence: fallback to prompted analysis",
                    "5. Collect low-confidence cases for retraining"
                ]
            )

        # Log query
        self._log_query({
            "timestamp": datetime.now().isoformat(),
            "query_type": "hybrid_approach",
            "approach_name": approach_name
        })

        return hybrid


    # ==================== Logging ====================

    def _log_query(self, data: Dict[str, Any]):
        """Log knowledge query"""
        log_file = self.data_dir / "knowledge_queries.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps(data) + "\n")


# ==================== Service Instance ====================

llm_knowledge = LLMKnowledge()
