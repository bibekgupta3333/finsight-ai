"""
Task Planning and Decomposition for Autonomous Agents.

Implements DAG-based task planning with dependency tracking,
dynamic replanning, and goal validation.
"""

from typing import Dict, Any, List, Optional, Set, Tuple
from pydantic import BaseModel
from enum import Enum
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
    READY = "ready"  # Dependencies satisfied
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class TaskType(str, Enum):
    """Types of tasks in fraud analysis."""
    OBSERVE = "observe"
    QUERY_POLICY = "query_policy"
    CALCULATE_RISK = "calculate_risk"
    CHECK_HISTORY = "check_history"
    REASON = "reason"
    DECIDE = "decide"
    EXPLAIN = "explain"
    ESCALATE = "escalate"


class Task(BaseModel):
    """Individual task in analysis plan."""

    id: str
    type: TaskType
    description: str
    dependencies: List[str] = []  # Task IDs this task depends on
    estimated_duration: float = 1.0  # seconds
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    class Config:
        arbitrary_types_allowed = True


class TaskDAG(BaseModel):
    """Directed Acyclic Graph of tasks."""

    tasks: Dict[str, Task] = {}
    adjacency_list: Dict[str, List[str]] = {}  # task_id -> dependent task_ids

    def add_task(self, task: Task):
        """Add task to DAG."""
        self.tasks[task.id] = task

        # Build adjacency list for dependency tracking
        for dep_id in task.dependencies:
            if dep_id not in self.adjacency_list:
                self.adjacency_list[dep_id] = []
            self.adjacency_list[dep_id].append(task.id)

    def get_ready_tasks(self) -> List[Task]:
        """
        Get tasks that are ready to execute (all dependencies satisfied).

        Returns:
            List of tasks with status READY
        """
        ready_tasks = []

        for task in self.tasks.values():
            if task.status != TaskStatus.PENDING:
                continue

            # Check if all dependencies are completed
            all_deps_satisfied = all(
                self.tasks[dep_id].status == TaskStatus.COMPLETED
                for dep_id in task.dependencies
            )

            if all_deps_satisfied:
                task.status = TaskStatus.READY
                ready_tasks.append(task)

        return ready_tasks

    def mark_completed(self, task_id: str, result: Any = None):
        """Mark task as completed and update dependent tasks."""
        if task_id not in self.tasks:
            return

        task = self.tasks[task_id]
        task.status = TaskStatus.COMPLETED
        task.result = result
        task.end_time = datetime.now()

        logger.info(f"Task {task_id} completed")

    def mark_failed(self, task_id: str, error: str):
        """Mark task as failed."""
        if task_id not in self.tasks:
            return

        task = self.tasks[task_id]
        task.status = TaskStatus.FAILED
        task.error = error
        task.end_time = datetime.now()

        logger.error(f"Task {task_id} failed: {error}")

    def is_complete(self) -> bool:
        """Check if all tasks are completed or failed."""
        return all(
            task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.SKIPPED]
            for task in self.tasks.values()
        )

    def has_cycle(self) -> bool:
        """Check if DAG has cycles (which would make it invalid)."""
        visited = set()
        rec_stack = set()

        def dfs(task_id: str) -> bool:
            visited.add(task_id)
            rec_stack.add(task_id)

            for dep_task_id in self.adjacency_list.get(task_id, []):
                if dep_task_id not in visited:
                    if dfs(dep_task_id):
                        return True
                elif dep_task_id in rec_stack:
                    return True

            rec_stack.remove(task_id)
            return False

        for task_id in self.tasks:
            if task_id not in visited:
                if dfs(task_id):
                    return True

        return False


class TaskPlanner:
    """
    Task planner for fraud detection agents.

    Creates execution plans, tracks dependencies, and enables
    dynamic replanning based on new information.

    Example:
        ```python
        planner = TaskPlanner()

        plan = planner.create_plan(
            transaction=transaction,
            goal="determine_fraud",
            constraints={"max_duration": 30.0}
        )

        # Execute ready tasks
        ready_tasks = plan.get_ready_tasks()
        for task in ready_tasks:
            result = await execute_task(task)
            plan.mark_completed(task.id, result)
        ```
    """

    def create_plan(
        self,
        transaction: Dict[str, Any],
        goal: str = "determine_fraud",
        constraints: Optional[Dict[str, Any]] = None,
    ) -> TaskDAG:
        """
        Create task execution plan for fraud analysis.

        Args:
            transaction: Transaction data
            goal: Analysis goal
            constraints: Constraints (max_duration, required_tools, etc.)

        Returns:
            TaskDAG with execution plan
        """
        logger.info(f"Creating plan for goal: {goal}")

        constraints = constraints or {}
        dag = TaskDAG()

        # Task 1: Observe transaction
        observe_task = Task(
            id="observe",
            type=TaskType.OBSERVE,
            description="Parse transaction features and identify anomalies",
            dependencies=[],
            estimated_duration=0.5,
        )
        dag.add_task(observe_task)

        # Task 2: Query fraud policy (depends on observe)
        policy_task = Task(
            id="query_policy",
            type=TaskType.QUERY_POLICY,
            description="Query fraud policies for transaction type",
            dependencies=["observe"],
            estimated_duration=1.0,
        )
        dag.add_task(policy_task)

        # Task 3: Calculate risk score (depends on observe)
        risk_task = Task(
            id="calculate_risk",
            type=TaskType.CALCULATE_RISK,
            description="Calculate heuristic risk score",
            dependencies=["observe"],
            estimated_duration=1.0,
        )
        dag.add_task(risk_task)

        # Task 4: Check account history (depends on observe)
        history_task = Task(
            id="check_history",
            type=TaskType.CHECK_HISTORY,
            description="Retrieve account history and fraud incidents",
            dependencies=["observe"],
            estimated_duration=1.5,
        )
        dag.add_task(history_task)

        # Task 5: Reason about fraud (depends on policy, risk, history)
        reason_task = Task(
            id="reason",
            type=TaskType.REASON,
            description="Chain-of-thought reasoning about fraud indicators",
            dependencies=["query_policy", "calculate_risk", "check_history"],
            estimated_duration=2.0,
        )
        dag.add_task(reason_task)

        # Task 6: Make decision (depends on reason)
        decide_task = Task(
            id="decide",
            type=TaskType.DECIDE,
            description="Make final fraud determination",
            dependencies=["reason"],
            estimated_duration=0.5,
        )
        dag.add_task(decide_task)

        # Task 7: Generate explanation (depends on decide)
        explain_task = Task(
            id="explain",
            type=TaskType.EXPLAIN,
            description="Generate human-readable explanation",
            dependencies=["decide"],
            estimated_duration=1.0,
        )
        dag.add_task(explain_task)

        # Validate plan
        if dag.has_cycle():
            logger.error("Task plan has cycles!")
            raise ValueError("Invalid task plan: contains cycles")

        # Validate goal is achievable
        self._validate_goal(dag, goal, constraints)

        logger.info(f"Created plan with {len(dag.tasks)} tasks")
        return dag

    def _validate_goal(
        self,
        dag: TaskDAG,
        goal: str,
        constraints: Dict[str, Any]
    ):
        """
        Validate that goal is achievable with current plan.

        Args:
            dag: Task DAG
            goal: Analysis goal
            constraints: Constraints

        Raises:
            ValueError: If goal is not achievable
        """
        # Check if we have necessary tasks for goal
        required_tasks = {
            "determine_fraud": {TaskType.OBSERVE, TaskType.REASON, TaskType.DECIDE},
            "explain_decision": {TaskType.EXPLAIN},
            "risk_assessment": {TaskType.CALCULATE_RISK},
        }

        if goal in required_tasks:
            required = required_tasks[goal]
            available = {task.type for task in dag.tasks.values()}

            if not required.issubset(available):
                missing = required - available
                raise ValueError(f"Goal '{goal}' requires tasks: {missing}")

        # Check duration constraint
        max_duration = constraints.get("max_duration")
        if max_duration:
            total_duration = sum(task.estimated_duration for task in dag.tasks.values())
            if total_duration > max_duration:
                logger.warning(
                    f"Plan duration ({total_duration}s) exceeds constraint ({max_duration}s)"
                )

    def replan(
        self,
        dag: TaskDAG,
        new_info: Dict[str, Any],
        transaction: Dict[str, Any],
    ) -> TaskDAG:
        """
        Create new plan based on new information.

        Dynamic replanning when:
        - Tool fails (add fallback task)
        - New evidence emerges (add verification task)
        - Early decision possible (skip remaining tasks)

        Args:
            dag: Current task DAG
            new_info: New information (tool_failed, high_confidence, etc.)
            transaction: Transaction data

        Returns:
            Updated or new TaskDAG
        """
        logger.info(f"Replanning based on: {new_info}")

        # Early termination if high confidence decision
        if new_info.get("high_confidence"):
            logger.info("High confidence - skipping remaining tasks")
            for task in dag.tasks.values():
                if task.status == TaskStatus.PENDING:
                    task.status = TaskStatus.SKIPPED
            return dag

        # Add escalation task if uncertainty detected
        if new_info.get("uncertain"):
            escalate_task = Task(
                id="escalate",
                type=TaskType.ESCALATE,
                description="Escalate to human reviewer",
                dependencies=["decide"],
                estimated_duration=0.5,
            )
            dag.add_task(escalate_task)
            logger.info("Added escalation task due to uncertainty")

        # Tool failure - add fallback
        failed_tool = new_info.get("failed_tool")
        if failed_tool:
            logger.warning(f"Tool {failed_tool} failed - adding fallback")
            # In production, add fallback task
            # For now, mark as failed and continue

        return dag

    def get_execution_order(self, dag: TaskDAG) -> List[List[str]]:
        """
        Get tasks grouped by execution level (for parallel execution).

        Returns:
            List of levels, where each level is a list of task IDs
            that can be executed in parallel
        """
        levels = []
        completed = set()
        all_task_ids = set(dag.tasks.keys())

        while len(completed) < len(all_task_ids):
            # Get tasks ready at this level
            ready = []
            for task_id, task in dag.tasks.items():
                if task_id in completed:
                    continue

                # Check dependencies
                deps_satisfied = all(
                    dep_id in completed for dep_id in task.dependencies
                )

                if deps_satisfied:
                    ready.append(task_id)

            if not ready:
                break

            levels.append(ready)

            # Mark as completed for next iteration
            completed.update(ready)

        return levels

    def estimate_duration(self, dag: TaskDAG, parallel: bool = True) -> float:
        """
        Estimate total execution time.

        Args:
            dag: Task DAG
            parallel: Whether tasks can execute in parallel

        Returns:
            Estimated duration in seconds
        """
        if not parallel:
            # Sequential execution
            return sum(task.estimated_duration for task in dag.tasks.values())

        # Parallel execution - sum of longest path
        levels = self.get_execution_order(dag)
        total = 0.0

        for level in levels:
            # Duration is the max of tasks at this level
            level_duration = max(
                dag.tasks[task_id].estimated_duration for task_id in level
            )
            total += level_duration

        return total
