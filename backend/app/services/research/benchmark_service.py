"""
Agent Benchmarking Service

Creates benchmark suite for evaluating agent performance against standard test cases.
Tracks metrics across different agent types and reasoning patterns.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum


class BenchmarkCategory(str, Enum):
    """Benchmark test categories"""
    EDGE_CASES = "edge_cases"
    HIGH_AMOUNT = "high_amount"
    ACCOUNT_DRAINED = "account_drained"
    RAPID_SUCCESSION = "rapid_succession"
    CROSS_BORDER = "cross_border"
    BASIC = "basic"


class BenchmarkTestCase(BaseModel):
    """Single benchmark test case"""
    test_id: str
    category: BenchmarkCategory
    transaction: Dict
    expected_prediction: str  # "fraud" or "legitimate"
    expected_confidence_min: float = 0.7
    difficulty: int = Field(ge=1, le=5, description="1=easy, 5=hard")
    description: str
    key_indicators: List[str] = []


class BenchmarkResult(BaseModel):
    """Result of running a benchmark test"""
    test_id: str
    agent_type: str
    prediction: str
    confidence: float
    correct: bool
    latency_ms: float
    reasoning_steps: List[str]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Error analysis
    error_type: Optional[str] = None  # false_positive, false_negative, correct
    explanation_quality: Optional[float] = None


class BenchmarkReport(BaseModel):
    """Aggregated benchmark results"""
    total_tests: int
    passed: int
    failed: int
    accuracy: float
    average_latency_ms: float
    average_confidence: float
    
    # By category
    results_by_category: Dict[str, Dict[str, float]] = {}
    
    # By difficulty
    easy_accuracy: float = 0.0  # difficulty 1-2
    medium_accuracy: float = 0.0  # difficulty 3
    hard_accuracy: float = 0.0  # difficulty 4-5
    
    # Error analysis
    false_positives: int = 0
    false_negatives: int = 0
    
    # Performance comparison
    best_agent_type: Optional[str] = None
    agent_rankings: List[Dict[str, Any]] = []


class BenchmarkService:
    """Service for benchmarking agent performance"""
    
    def __init__(self, storage_path: str = "data/benchmarks"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.tests_file = self.storage_path / "test_suite.json"
        self.results_file = self.storage_path / "benchmark_results.jsonl"
        
        # Initialize test suite if not exists
        if not self.tests_file.exists():
            self._create_default_test_suite()
    
    def _create_default_test_suite(self):
        """Create default benchmark test cases"""
        
        test_cases = [
            # Basic cases (Easy)
            BenchmarkTestCase(
                test_id="basic_fraud_001",
                category=BenchmarkCategory.BASIC,
                transaction={
                    "type": "CASH_OUT",
                    "amount": 500000.0,
                    "oldbalanceOrg": 1000000.0,
                    "newbalanceOrig": 500000.0,
                    "oldbalanceDest": 0.0,
                    "newbalanceDest": 500000.0
                },
                expected_prediction="fraud",
                expected_confidence_min=0.8,
                difficulty=1,
                description="Clear fraud: Large CASH_OUT with balance mismatch",
                key_indicators=["large_amount", "cash_out", "balance_mismatch"]
            ),
            
            BenchmarkTestCase(
                test_id="basic_legit_001",
                category=BenchmarkCategory.BASIC,
                transaction={
                    "type": "PAYMENT",
                    "amount": 50.0,
                    "oldbalanceOrg": 1000.0,
                    "newbalanceOrig": 950.0,
                    "oldbalanceDest": 500.0,
                    "newbalanceDest": 550.0
                },
                expected_prediction="legitimate",
                expected_confidence_min=0.8,
                difficulty=1,
                description="Clear legitimate: Small PAYMENT with correct balances",
                key_indicators=["small_amount", "payment", "balance_match"]
            ),
            
            # Edge cases (Hard)
            BenchmarkTestCase(
                test_id="edge_tiny_fraud_001",
                category=BenchmarkCategory.EDGE_CASES,
                transaction={
                    "type": "TRANSFER",
                    "amount": 1.0,
                    "oldbalanceOrg": 100.0,
                    "newbalanceOrig": 0.0,  # Entire account drained for $1
                    "oldbalanceDest": 0.0,
                    "newbalanceDest": 0.0  # Money disappeared
                },
                expected_prediction="fraud",
                expected_confidence_min=0.6,
                difficulty=5,
                description="Tiny amount but suspicious: entire account drained, money disappeared",
                key_indicators=["account_drained", "disappeared_money", "unusual_pattern"]
            ),
            
            BenchmarkTestCase(
                test_id="edge_high_legit_001",
                category=BenchmarkCategory.HIGH_AMOUNT,
                transaction={
                    "type": "PAYMENT",
                    "amount": 900000.0,
                    "oldbalanceOrg": 1000000.0,
                    "newbalanceOrig": 100000.0,
                    "oldbalanceDest": 500000.0,
                    "newbalanceDest": 1400000.0
                },
                expected_prediction="legitimate",
                expected_confidence_min=0.6,
                difficulty=4,
                description="High amount but balances match perfectly - legitimate large payment",
                key_indicators=["high_amount", "balance_match", "payment_type"]
            ),
            
            # Account drained (Medium)
            BenchmarkTestCase(
                test_id="drained_fraud_001",
                category=BenchmarkCategory.ACCOUNT_DRAINED,
                transaction={
                    "type": "CASH_OUT",
                    "amount": 750000.0,
                    "oldbalanceOrg": 750000.0,
                    "newbalanceOrig": 0.0,
                    "oldbalanceDest": 0.0,
                    "newbalanceDest": 0.0
                },
                expected_prediction="fraud",
                expected_confidence_min=0.7,
                difficulty=3,
                description="Complete account drain with money disappearing",
                key_indicators=["account_drained", "disappeared_money", "cash_out"]
            ),
            
            # Rapid succession (Medium-Hard)
            BenchmarkTestCase(
                test_id="rapid_fraud_001",
                category=BenchmarkCategory.RAPID_SUCCESSION,
                transaction={
                    "type": "TRANSFER",
                    "amount": 200000.0,
                    "oldbalanceOrg": 250000.0,
                    "newbalanceOrig": 50000.0,
                    "oldbalanceDest": 0.0,
                    "newbalanceDest": 0.0,
                    "step": 100  # Could indicate rapid transactions
                },
                expected_prediction="fraud",
                expected_confidence_min=0.65,
                difficulty=4,
                description="Large transfer with money disappearing - possible rapid succession fraud",
                key_indicators=["large_transfer", "disappeared_money", "suspicious_pattern"]
            ),
        ]
        
        # Save test suite
        with open(self.tests_file, "w") as f:
            json.dump(
                [test.model_dump() for test in test_cases],
                f,
                indent=2,
                default=str
            )
    
    def get_test_suite(self) -> List[BenchmarkTestCase]:
        """Load all benchmark test cases"""
        with open(self.tests_file, "r") as f:
            test_data = json.load(f)
        
        return [BenchmarkTestCase(**test) for test in test_data]
    
    def record_result(self, result: BenchmarkResult):
        """Record a benchmark test result"""
        with open(self.results_file, "a") as f:
            f.write(result.model_dump_json() + "\n")
    
    def generate_report(
        self,
        agent_type: Optional[str] = None,
        start_date: Optional[datetime] = None
    ) -> BenchmarkReport:
        """Generate benchmark report"""
        
        if not self.results_file.exists():
            return BenchmarkReport(
                total_tests=0,
                passed=0,
                failed=0,
                accuracy=0.0,
                average_latency_ms=0.0,
                average_confidence=0.0
            )
        
        # Load results
        results = []
        with open(self.results_file, "r") as f:
            for line in f:
                result = BenchmarkResult.model_validate_json(line)
                
                # Filter by agent_type and date if specified
                if agent_type and result.agent_type != agent_type:
                    continue
                if start_date and result.timestamp < start_date:
                    continue
                
                results.append(result)
        
        if not results:
            return BenchmarkReport(
                total_tests=0,
                passed=0,
                failed=0,
                accuracy=0.0,
                average_latency_ms=0.0,
                average_confidence=0.0
            )
        
        # Calculate metrics
        total = len(results)
        passed = sum(1 for r in results if r.correct)
        failed = total - passed
        accuracy = passed / total if total > 0 else 0.0
        avg_latency = sum(r.latency_ms for r in results) / total
        avg_confidence = sum(r.confidence for r in results) / total
        
        # Error analysis
        false_positives = sum(
            1 for r in results 
            if r.error_type == "false_positive"
        )
        false_negatives = sum(
            1 for r in results 
            if r.error_type == "false_negative"
        )
        
        # Load test cases for category analysis
        test_cases = {t.test_id: t for t in self.get_test_suite()}
        
        # Results by category
        results_by_category = {}
        category_counts = {}
        
        for result in results:
            test_case = test_cases.get(result.test_id)
            if not test_case:
                continue
            
            category = test_case.category
            if category not in results_by_category:
                results_by_category[category] = {"correct": 0, "total": 0}
            
            results_by_category[category]["total"] += 1
            if result.correct:
                results_by_category[category]["correct"] += 1
        
        # Calculate accuracy by category
        for category, stats in results_by_category.items():
            stats["accuracy"] = stats["correct"] / stats["total"]
        
        # Accuracy by difficulty
        easy_results = [
            r for r in results
            if test_cases.get(r.test_id) and test_cases[r.test_id].difficulty <= 2
        ]
        medium_results = [
            r for r in results
            if test_cases.get(r.test_id) and test_cases[r.test_id].difficulty == 3
        ]
        hard_results = [
            r for r in results
            if test_cases.get(r.test_id) and test_cases[r.test_id].difficulty >= 4
        ]
        
        easy_accuracy = sum(1 for r in easy_results if r.correct) / len(easy_results) if easy_results else 0.0
        medium_accuracy = sum(1 for r in medium_results if r.correct) / len(medium_results) if medium_results else 0.0
        hard_accuracy = sum(1 for r in hard_results if r.correct) / len(hard_results) if hard_results else 0.0
        
        return BenchmarkReport(
            total_tests=total,
            passed=passed,
            failed=failed,
            accuracy=accuracy,
            average_latency_ms=avg_latency,
            average_confidence=avg_confidence,
            results_by_category=results_by_category,
            easy_accuracy=easy_accuracy,
            medium_accuracy=medium_accuracy,
            hard_accuracy=hard_accuracy,
            false_positives=false_positives,
            false_negatives=false_negatives
        )
    
    def compare_agents(self) -> List[Dict]:
        """Compare performance across different agent types"""
        
        if not self.results_file.exists():
            return []
        
        # Get all agent types
        agent_types = set()
        with open(self.results_file, "r") as f:
            for line in f:
                result = BenchmarkResult.model_validate_json(line)
                agent_types.add(result.agent_type)
        
        # Generate report for each agent
        rankings = []
        for agent_type in agent_types:
            report = self.generate_report(agent_type=agent_type)
            rankings.append({
                "agent_type": agent_type,
                "accuracy": report.accuracy,
                "average_latency_ms": report.average_latency_ms,
                "average_confidence": report.average_confidence,
                "passed": report.passed,
                "failed": report.failed
            })
        
        # Sort by accuracy (descending)
        rankings.sort(key=lambda x: x["accuracy"], reverse=True)
        
        return rankings


# Global instance
benchmark_service = BenchmarkService()
