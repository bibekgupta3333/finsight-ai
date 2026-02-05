"""
RLAIF Service - Reinforcement Learning from AI Feedback

Uses LLM-as-judge to evaluate agent explanations without human feedback.
Enables scalable quality assessment and self-improvement loops.
"""

import asyncio
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import httpx

from app.core.config import get_settings

settings = get_settings()


class JudgmentCriteria(BaseModel):
    """Criteria for evaluating explanations"""
    clarity: int = Field(ge=1, le=5, description="How clear is the explanation?")
    accuracy: int = Field(ge=1, le=5, description="How accurate is the reasoning?")
    completeness: int = Field(ge=1, le=5, description="Does it address all aspects?")
    coherence: int = Field(ge=1, le=5, description="Is the logic consistent?")
    actionability: int = Field(ge=1, le=5, description="Does it provide useful guidance?")


class AIJudgment(BaseModel):
    """AI judgment of an explanation"""
    explanation_id: str
    overall_score: float = Field(ge=0, le=5, description="Overall quality score")
    criteria: JudgmentCriteria
    feedback: str = Field(description="Detailed feedback from judge")
    improvement_suggestions: List[str] = []
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    judge_model: str = "mistral-7b"


class ComparisonResult(BaseModel):
    """Result of comparing two explanations"""
    winner: str  # "explanation_a" or "explanation_b" or "tie"
    confidence: float = Field(ge=0, le=1)
    reasoning: str
    margin: float = Field(description="Score difference")


class RLAIFService:
    """Service for AI-based feedback and evaluation"""
    
    def __init__(self):
        settings = get_settings()
        self.ollama_url = settings.ollama_base_url
        self.judge_model = "mistral:7b"  # Or qwen3:0.6b for speed
        
    async def judge_explanation(
        self,
        explanation: str,
        transaction_context: Dict,
        prediction: str,
        reasoning_steps: List[str]
    ) -> AIJudgment:
        """
        Use LLM to judge the quality of an explanation
        
        Args:
            explanation: The explanation text to evaluate
            transaction_context: Original transaction data
            prediction: fraud/legitimate
            reasoning_steps: Agent's reasoning chain
            
        Returns:
            AI judgment with scores and feedback
        """
        
        # Construct judgment prompt
        judge_prompt = f"""You are an expert fraud analyst evaluating an AI's explanation of a fraud detection decision.

Transaction Details:
{transaction_context}

Prediction: {prediction}

Reasoning Steps:
{chr(10).join(f'{i+1}. {step}' for i, step in enumerate(reasoning_steps))}

Final Explanation:
{explanation}

Please evaluate this explanation on the following criteria (1-5 scale):

1. **Clarity**: Is the explanation easy to understand?
2. **Accuracy**: Is the reasoning logically sound and factually correct?
3. **Completeness**: Does it address all important aspects of the decision?
4. **Coherence**: Is the logic consistent throughout?
5. **Actionability**: Does it provide useful guidance for next steps?

Provide your evaluation in this exact JSON format:
{{
  "clarity": <1-5>,
  "accuracy": <1-5>,
  "completeness": <1-5>,
  "coherence": <1-5>,
  "actionability": <1-5>,
  "overall_score": <average of above>,
  "feedback": "<detailed feedback paragraph>",
  "improvement_suggestions": ["<suggestion 1>", "<suggestion 2>", "<suggestion 3>"]
}}

Be critical but fair. Focus on helping improve the explanation quality.
"""
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.judge_model,
                        "prompt": judge_prompt,
                        "stream": False,
                        "format": "json",
                        "options": {
                            "temperature": 0.3,  # More deterministic
                            "top_p": 0.9
                        }
                    }
                )
                
                result = response.json()
                judgment_data = eval(result["response"])  # Parse JSON from LLM
                
                criteria = JudgmentCriteria(**{
                    k: v for k, v in judgment_data.items() 
                    if k in ["clarity", "accuracy", "completeness", "coherence", "actionability"]
                })
                
                return AIJudgment(
                    explanation_id=f"exp_{datetime.utcnow().timestamp()}",
                    overall_score=judgment_data.get("overall_score", 0.0),
                    criteria=criteria,
                    feedback=judgment_data.get("feedback", ""),
                    improvement_suggestions=judgment_data.get("improvement_suggestions", []),
                    judge_model=self.judge_model
                )
                
        except Exception as e:
            # Fallback: simple heuristic judgment
            return self._heuristic_judgment(explanation, prediction, reasoning_steps)
    
    def _heuristic_judgment(
        self,
        explanation: str,
        prediction: str,
        reasoning_steps: List[str]
    ) -> AIJudgment:
        """Fallback heuristic-based judgment when LLM fails"""
        
        # Simple heuristics
        clarity = min(5, max(1, len(explanation.split()) // 20 + 1))
        accuracy = min(5, len(reasoning_steps))
        completeness = min(5, 3 if len(explanation) > 100 else 2)
        coherence = min(5, 4 if "because" in explanation.lower() else 3)
        actionability = min(5, 4 if any(word in explanation.lower() for word in ["recommend", "should", "suggest"]) else 3)
        
        overall = (clarity + accuracy + completeness + coherence + actionability) / 5
        
        return AIJudgment(
            explanation_id=f"exp_{datetime.utcnow().timestamp()}",
            overall_score=overall,
            criteria=JudgmentCriteria(
                clarity=clarity,
                accuracy=accuracy,
                completeness=completeness,
                coherence=coherence,
                actionability=actionability
            ),
            feedback="Heuristic evaluation (LLM judge unavailable)",
            improvement_suggestions=["Add more specific details", "Provide clear recommendations"],
            judge_model="heuristic-fallback"
        )
    
    async def compare_explanations(
        self,
        explanation_a: str,
        explanation_b: str,
        transaction_context: Dict
    ) -> ComparisonResult:
        """
        Compare two explanations and determine which is better
        
        Useful for selecting best explanation from multiple agents (debate, swarm, etc.)
        """
        
        comparison_prompt = f"""You are an expert fraud analyst comparing two AI explanations for the same transaction.

Transaction: {transaction_context}

Explanation A:
{explanation_a}

Explanation B:
{explanation_b}

Which explanation is better? Consider:
1. Clarity and readability
2. Logical soundness
3. Completeness
4. Actionability

Respond in JSON format:
{{
  "winner": "explanation_a" or "explanation_b" or "tie",
  "confidence": <0.0-1.0>,
  "reasoning": "<brief explanation of your choice>",
  "score_a": <0.0-5.0>,
  "score_b": <0.0-5.0>
}}
"""
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.judge_model,
                        "prompt": comparison_prompt,
                        "stream": False,
                        "format": "json",
                        "options": {"temperature": 0.2}
                    }
                )
                
                result = response.json()
                comparison_data = eval(result["response"])
                
                score_a = comparison_data.get("score_a", 3.0)
                score_b = comparison_data.get("score_b", 3.0)
                
                return ComparisonResult(
                    winner=comparison_data.get("winner", "tie"),
                    confidence=comparison_data.get("confidence", 0.5),
                    reasoning=comparison_data.get("reasoning", ""),
                    margin=abs(score_a - score_b)
                )
                
        except Exception:
            # Fallback: simple length-based comparison
            len_a = len(explanation_a.split())
            len_b = len(explanation_b.split())
            
            if abs(len_a - len_b) < 20:
                winner = "tie"
                confidence = 0.5
            elif len_a > len_b:
                winner = "explanation_a"
                confidence = min(0.8, 0.5 + (len_a - len_b) / 100)
            else:
                winner = "explanation_b"
                confidence = min(0.8, 0.5 + (len_b - len_a) / 100)
            
            return ComparisonResult(
                winner=winner,
                confidence=confidence,
                reasoning="Heuristic comparison (LLM unavailable)",
                margin=abs(len_a - len_b) / max(len_a, len_b)
            )
    
    async def self_improvement_loop(
        self,
        explanation: str,
        max_iterations: int = 3
    ) -> Dict:
        """
        Iteratively improve an explanation using AI feedback
        
        Returns final improved explanation and iteration history
        """
        
        history = []
        current_explanation = explanation
        
        for iteration in range(max_iterations):
            # Get judgment
            judgment = await self.judge_explanation(
                explanation=current_explanation,
                transaction_context={},
                prediction="fraud",
                reasoning_steps=[]
            )
            
            history.append({
                "iteration": iteration + 1,
                "explanation": current_explanation,
                "score": judgment.overall_score,
                "feedback": judgment.feedback
            })
            
            # If score is high enough, stop
            if judgment.overall_score >= 4.5:
                break
            
            # Generate improved version
            improvement_prompt = f"""Improve this fraud detection explanation based on the feedback:

Original Explanation:
{current_explanation}

Feedback:
{judgment.feedback}

Suggestions:
{chr(10).join(f'- {s}' for s in judgment.improvement_suggestions)}

Provide an improved version that addresses the feedback while maintaining accuracy.
Keep it concise (under 200 words).
"""
            
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"{self.ollama_url}/api/generate",
                        json={
                            "model": self.judge_model,
                            "prompt": improvement_prompt,
                            "stream": False,
                            "options": {"temperature": 0.5}
                        }
                    )
                    
                    result = response.json()
                    current_explanation = result["response"].strip()
                    
            except Exception:
                # If improvement fails, keep current version
                break
        
        return {
            "final_explanation": current_explanation,
            "iterations": len(history),
            "improvement_history": history,
            "initial_score": history[0]["score"] if history else 0,
            "final_score": history[-1]["score"] if history else 0
        }


# Global instance
rlaif_service = RLAIFService()
