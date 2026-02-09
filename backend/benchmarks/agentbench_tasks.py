"""
AgentBench-Compatible Fraud Detection Tasks.

Creates fraud detection tasks following AgentBench's JSON format and evaluation
methodology. Since AgentBench doesn't have fraud detection tasks, we create
custom tasks that follow their structure.

AgentBench Task Format:
{
    "task_id": "fraud_001",
    "task_type": "fraud_detection",
    "difficulty": "hard",
    "instruction": "Analyze this transaction...",
    "initial_state": {...},
    "ground_truth": {...},
    "success_criteria": {...}
}

Reference: https://github.com/THUDM/AgentBench (ICLR 2024)
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Task difficulty levels
DIFFICULTY_LEVELS = ["easy", "medium", "hard", "expert"]


class AgentBenchFraudTasks:
    """Generate AgentBench-format fraud detection tasks."""

    def __init__(self, output_dir: str = "data/benchmarks/agentbench"):
        """
        Initialize task generator.

        Args:
            output_dir: Directory to save task JSONs
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_all_tasks(self) -> List[Dict[str, Any]]:
        """
        Generate all fraud detection tasks.

        Returns:
            List of task dicts in AgentBench format
        """
        tasks = []

        # Easy tasks: Clear fraud patterns
        tasks.extend(self._generate_easy_tasks())

        # Medium tasks: Ambiguous cases
        tasks.extend(self._generate_medium_tasks())

        # Hard tasks: Edge cases and adversarial
        tasks.extend(self._generate_hard_tasks())

        # Expert tasks: Multi-step reasoning required
        tasks.extend(self._generate_expert_tasks())

        return tasks

    def _generate_easy_tasks(self) -> List[Dict]:
        """Generate easy fraud detection tasks."""
        return [
            {
                "task_id": "fraud_easy_001",
                "task_type": "fraud_detection",
                "difficulty": "easy",
                "instruction": (
                    "You are a fraud detection agent. Analyze the following financial transaction "
                    "and determine if it is fraudulent. You have access to fraud detection tools.\n\n"
                    "Transaction details:\n"
                    "- Type: CASH_OUT\n"
                    "- Amount: $500,000\n"
                    "- Origin Account Balance Before: $1,000,000\n"
                    "- Origin Account Balance After: $500,000\n"
                    "- Destination Account Balance Before: $0\n"
                    "- Destination Account Balance After: $0\n\n"
                    "Provide your assessment with confidence level."
                ),
                "initial_state": {
                    "transaction": {
                        "type": "CASH_OUT",
                        "amount": 500000.0,
                        "oldbalanceOrg": 1000000.0,
                        "newbalanceOrig": 500000.0,
                        "oldbalanceDest": 0.0,
                        "newbalanceDest": 0.0,
                        "nameOrig": "C1234567890",
                        "nameDest": "M1234567890",
                    },
                    "available_tools": [
                        "calculate_risk_score",
                        "query_fraud_policy",
                        "fetch_account_history",
                    ],
                },
                "ground_truth": {
                    "is_fraud": True,
                    "risk_score_min": 70.0,
                    "confidence_min": 0.7,
                    "reasoning": [
                        "Large CASH_OUT transaction",
                        "Destination account balance remains zero (money disappeared)",
                        "High amount ($500k)",
                    ],
                },
                "success_criteria": {
                    "correct_classification": True,  # Must classify as fraud
                    "min_confidence": 0.7,
                    "required_reasoning_elements": 2,  # At least 2 of 3 reasoning points
                    "tool_usage": True,  # Must use at least one tool
                },
                "max_turns": 5,
            },
            {
                "task_id": "fraud_easy_002",
                "task_type": "fraud_detection",
                "difficulty": "easy",
                "instruction": (
                    "You are a fraud detection agent. Analyze the following financial transaction "
                    "and determine if it is fraudulent.\n\n"
                    "Transaction details:\n"
                    "- Type: PAYMENT\n"
                    "- Amount: $50\n"
                    "- Origin Account Balance Before: $1,000\n"
                    "- Origin Account Balance After: $950\n"
                    "- Destination Account Balance Before: $500\n"
                    "- Destination Account Balance After: $550\n\n"
                    "Provide your assessment with confidence level."
                ),
                "initial_state": {
                    "transaction": {
                        "type": "PAYMENT",
                        "amount": 50.0,
                        "oldbalanceOrg": 1000.0,
                        "newbalanceOrig": 950.0,
                        "oldbalanceDest": 500.0,
                        "newbalanceDest": 550.0,
                        "nameOrig": "C9876543210",
                        "nameDest": "M9876543210",
                    },
                    "available_tools": [
                        "calculate_risk_score",
                        "query_fraud_policy",
                    ],
                },
                "ground_truth": {
                    "is_fraud": False,
                    "risk_score_max": 30.0,
                    "confidence_min": 0.8,
                    "reasoning": [
                        "Small payment amount",
                        "Balance changes are consistent",
                        "Standard PAYMENT transaction type",
                    ],
                },
                "success_criteria": {
                    "correct_classification": True,  # Must classify as legitimate
                    "min_confidence": 0.8,
                    "required_reasoning_elements": 2,
                    "tool_usage": True,
                },
                "max_turns": 5,
            },
        ]

    def _generate_medium_tasks(self) -> List[Dict]:
        """Generate medium difficulty fraud detection tasks."""
        return [
            {
                "task_id": "fraud_medium_001",
                "task_type": "fraud_detection",
                "difficulty": "medium",
                "instruction": (
                    "You are a fraud detection agent. Analyze this transaction that has some "
                    "ambiguous signals.\n\n"
                    "Transaction details:\n"
                    "- Type: TRANSFER\n"
                    "- Amount: $250,000\n"
                    "- Origin Account Balance Before: $300,000\n"
                    "- Origin Account Balance After: $50,000\n"
                    "- Destination Account Balance Before: $100,000\n"
                    "- Destination Account Balance After: $350,000\n\n"
                    "Carefully analyze all indicators before making your decision."
                ),
                "initial_state": {
                    "transaction": {
                        "type": "TRANSFER",
                        "amount": 250000.0,
                        "oldbalanceOrg": 300000.0,
                        "newbalanceOrig": 50000.0,
                        "oldbalanceDest": 100000.0,
                        "newbalanceDest": 350000.0,
                        "nameOrig": "C5555555555",
                        "nameDest": "C6666666666",
                    },
                    "available_tools": [
                        "calculate_risk_score",
                        "query_fraud_policy",
                        "fetch_account_history",
                    ],
                },
                "ground_truth": {
                    "is_fraud": False,  # Large but legitimate transfer
                    "risk_score_max": 50.0,
                    "confidence_min": 0.6,
                    "reasoning": [
                        "Large transfer but balances are consistent",
                        "Both accounts are customer accounts (C prefix)",
                        "Destination received exact amount",
                    ],
                },
                "success_criteria": {
                    "correct_classification": True,
                    "min_confidence": 0.6,
                    "required_reasoning_elements": 2,
                    "tool_usage": True,
                    "max_false_confidence": 0.9,  # Should not be overconfident
                },
                "max_turns": 8,
            },
            {
                "task_id": "fraud_medium_002",
                "task_type": "fraud_detection",
                "difficulty": "medium",
                "instruction": (
                    "You are a fraud detection agent. This transaction has mixed signals - "
                    "analyze carefully.\n\n"
                    "Transaction details:\n"
                    "- Type: CASH_OUT\n"
                    "- Amount: $150,000\n"
                    "- Origin Account Balance Before: $150,000\n"
                    "- Origin Account Balance After: $0\n"
                    "- Destination Account Balance Before: $50,000\n"
                    "- Destination Account Balance After: $200,000\n\n"
                    "Use multiple tools to build a comprehensive analysis."
                ),
                "initial_state": {
                    "transaction": {
                        "type": "CASH_OUT",
                        "amount": 150000.0,
                        "oldbalanceOrg": 150000.0,
                        "newbalanceOrig": 0.0,
                        "oldbalanceDest": 50000.0,
                        "newbalanceDest": 200000.0,
                        "nameOrig": "C7777777777",
                        "nameDest": "M8888888888",
                    },
                    "available_tools": [
                        "calculate_risk_score",
                        "query_fraud_policy",
                        "fetch_account_history",
                    ],
                },
                "ground_truth": {
                    "is_fraud": True,
                    "risk_score_min": 60.0,
                    "confidence_min": 0.65,
                    "reasoning": [
                        "Account completely drained",
                        "Large CASH_OUT amount",
                        "To merchant account",
                    ],
                },
                "success_criteria": {
                    "correct_classification": True,
                    "min_confidence": 0.65,
                    "required_reasoning_elements": 2,
                    "tool_usage": True,
                    "min_tools_used": 2,  # Must use at least 2 tools
                },
                "max_turns": 8,
            },
        ]

    def _generate_hard_tasks(self) -> List[Dict]:
        """Generate hard fraud detection tasks (edge cases)."""
        return [
            {
                "task_id": "fraud_hard_001",
                "task_type": "fraud_detection",
                "difficulty": "hard",
                "instruction": (
                    "You are a fraud detection agent. This is a challenging edge case with "
                    "contradictory signals.\n\n"
                    "Transaction details:\n"
                    "- Type: TRANSFER\n"
                    "- Amount: $1 (very small)\n"
                    "- Origin Account Balance Before: $100\n"
                    "- Origin Account Balance After: $0 (entire account drained)\n"
                    "- Destination Account Balance Before: $0\n"
                    "- Destination Account Balance After: $0 (money disappeared)\n\n"
                    "Small amount but suspicious patterns. Analyze carefully."
                ),
                "initial_state": {
                    "transaction": {
                        "type": "TRANSFER",
                        "amount": 1.0,
                        "oldbalanceOrg": 100.0,
                        "newbalanceOrig": 0.0,
                        "oldbalanceDest": 0.0,
                        "newbalanceDest": 0.0,
                        "nameOrig": "C1111111111",
                        "nameDest": "C2222222222",
                    },
                    "available_tools": [
                        "calculate_risk_score",
                        "query_fraud_policy",
                        "fetch_account_history",
                    ],
                },
                "ground_truth": {
                    "is_fraud": True,
                    "risk_score_min": 55.0,
                    "confidence_min": 0.55,
                    "reasoning": [
                        "Entire account drained for just $1",
                        "Money disappeared (destination balance unchanged)",
                        "Suspicious despite small amount",
                    ],
                },
                "success_criteria": {
                    "correct_classification": True,
                    "min_confidence": 0.55,  # Lower threshold for edge case
                    "required_reasoning_elements": 2,
                    "tool_usage": True,
                    "min_tools_used": 2,
                    "requires_explanation": True,  # Must explain edge case reasoning
                },
                "max_turns": 10,
            },
            {
                "task_id": "fraud_hard_002",
                "task_type": "fraud_detection",
                "difficulty": "hard",
                "instruction": (
                    "You are a fraud detection agent. This transaction appears legitimate but "
                    "has subtle fraud indicators that are easy to miss.\n\n"
                    "Transaction details:\n"
                    "- Type: PAYMENT\n"
                    "- Amount: $900,000 (very large payment)\n"
                    "- Origin Account Balance Before: $1,000,000\n"
                    "- Origin Account Balance After: $100,000\n"
                    "- Destination Account Balance Before: $500,000\n"
                    "- Destination Account Balance After: $1,400,000\n\n"
                    "Large payment but balances seem consistent. Look deeper."
                ),
                "initial_state": {
                    "transaction": {
                        "type": "PAYMENT",
                        "amount": 900000.0,
                        "oldbalanceOrg": 1000000.0,
                        "newbalanceOrig": 100000.0,
                        "oldbalanceDest": 500000.0,
                        "newbalanceDest": 1400000.0,
                        "nameOrig": "C3333333333",
                        "nameDest": "M4444444444",
                    },
                    "available_tools": [
                        "calculate_risk_score",
                        "query_fraud_policy",
                        "fetch_account_history",
                    ],
                },
                "ground_truth": {
                    "is_fraud": False,  # Legitimate despite large amount
                    "risk_score_max": 40.0,
                    "confidence_min": 0.7,
                    "reasoning": [
                        "Balances are mathematically consistent",
                        "PAYMENT type (not inherently suspicious)",
                        "Large amount alone doesn't indicate fraud",
                    ],
                },
                "success_criteria": {
                    "correct_classification": True,
                    "min_confidence": 0.7,
                    "required_reasoning_elements": 2,
                    "tool_usage": True,
                    "min_tools_used": 2,
                    "avoid_false_positive": True,  # Critical: Don't flag legitimate high-value
                },
                "max_turns": 10,
            },
        ]

    def _generate_expert_tasks(self) -> List[Dict]:
        """Generate expert-level tasks requiring multi-step reasoning."""
        return [
            {
                "task_id": "fraud_expert_001",
                "task_type": "fraud_detection",
                "difficulty": "expert",
                "instruction": (
                    "You are a fraud detection agent. This is a multi-step investigation task.\n\n"
                    "You receive an alert about a potentially fraudulent transaction:\n"
                    "- Type: TRANSFER\n"
                    "- Amount: $300,000\n"
                    "- Origin Account: C9999999999\n"
                    "- Destination Account: C0000000000\n\n"
                    "You must:\n"
                    "1. Fetch account history for both accounts\n"
                    "2. Query relevant fraud policies\n"
                    "3. Calculate risk scores\n"
                    "4. Make a final determination with detailed reasoning\n\n"
                    "Use at least 3 different tools in your investigation."
                ),
                "initial_state": {
                    "transaction": {
                        "type": "TRANSFER",
                        "amount": 300000.0,
                        "oldbalanceOrg": 350000.0,
                        "newbalanceOrig": 50000.0,
                        "oldbalanceDest": 0.0,
                        "newbalanceDest": 300000.0,
                        "nameOrig": "C9999999999",
                        "nameDest": "C0000000000",
                    },
                    "available_tools": [
                        "calculate_risk_score",
                        "query_fraud_policy",
                        "fetch_account_history",
                    ],
                },
                "ground_truth": {
                    "is_fraud": True,
                    "risk_score_min": 70.0,
                    "confidence_min": 0.75,
                    "reasoning": [
                        "New destination account (previously $0)",
                        "Large transfer to new account",
                        "Origin account significantly depleted",
                        "Matches policy for fraudulent transfers",
                    ],
                },
                "success_criteria": {
                    "correct_classification": True,
                    "min_confidence": 0.75,
                    "required_reasoning_elements": 3,
                    "tool_usage": True,
                    "min_tools_used": 3,  # Must use all 3 tools
                    "requires_detailed_explanation": True,
                    "multi_step_reasoning": True,
                },
                "max_turns": 15,
            },
        ]

    def save_tasks(self, tasks: List[Dict]) -> Path:
        """
        Save tasks to JSON file.

        Args:
            tasks: List of task dicts

        Returns:
            Path to saved file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"fraud_detection_tasks_{timestamp}.json"

        # Create AgentBench-format dataset
        dataset = {
            "dataset_name": "fraud_detection",
            "version": "1.0",
            "created_at": timestamp,
            "description": "Fraud detection tasks in AgentBench format for evaluating LLM agents",
            "num_tasks": len(tasks),
            "difficulty_distribution": {
                level: sum(1 for t in tasks if t["difficulty"] == level)
                for level in DIFFICULTY_LEVELS
            },
            "tasks": tasks,
        }

        with open(output_file, "w") as f:
            json.dump(dataset, f, indent=2)

        print(f"✅ Saved {len(tasks)} tasks to: {output_file}")
        return output_file


def main():
    """Generate and save AgentBench fraud detection tasks."""
    generator = AgentBenchFraudTasks()

    # Generate all tasks
    tasks = generator.generate_all_tasks()

    # Print summary
    print(f"\n{'=' * 70}")
    print("AGENTBENCH FRAUD DETECTION TASKS GENERATED")
    print(f"{'=' * 70}\n")

    print(f"Total Tasks: {len(tasks)}")
    print("\nDifficulty Distribution:")
    for level in DIFFICULTY_LEVELS:
        count = sum(1 for t in tasks if t["difficulty"] == level)
        print(f"  {level.capitalize()}: {count}")

    # Save to file
    output_file = generator.save_tasks(tasks)

    print(f"\n✅ Task generation complete!")
    print(f"   Output: {output_file}")


if __name__ == "__main__":
    main()
