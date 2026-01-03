"""
Tool & Failure Recovery System.

Implements comprehensive retry logic, health checks, fallback chains,
partial result aggregation, root cause analysis, and incident reporting.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ToolHealth(str, Enum):
    """Tool health status."""

    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    UNKNOWN = "UNKNOWN"


class FailureCategory(str, Enum):
    """Failure categorization for root cause analysis."""

    TIMEOUT = "TIMEOUT"
    NETWORK = "NETWORK"
    AUTHENTICATION = "AUTHENTICATION"
    RATE_LIMIT = "RATE_LIMIT"
    INVALID_INPUT = "INVALID_INPUT"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    DEPENDENCY_FAILURE = "DEPENDENCY_FAILURE"
    UNKNOWN = "UNKNOWN"


class RecoveryStrategy(str, Enum):
    """Recovery strategy selection."""

    RETRY = "RETRY"
    FALLBACK = "FALLBACK"
    PARTIAL_RESULT = "PARTIAL_RESULT"
    CACHE = "CACHE"
    ESCALATE = "ESCALATE"
    ABORT = "ABORT"


class ToolHealthCheck(BaseModel):
    """Health check result for a tool."""

    tool_name: str
    status: ToolHealth
    last_check: datetime
    response_time: float  # seconds
    success_rate: float  # 0.0 to 1.0
    recent_failures: int
    error_message: Optional[str] = None


class FailureRootCause(BaseModel):
    """Root cause analysis of a failure."""

    category: FailureCategory
    primary_cause: str
    contributing_factors: List[str] = Field(default_factory=list)
    affected_tools: List[str] = Field(default_factory=list)
    confidence: float  # 0.0 to 1.0
    recommended_strategy: RecoveryStrategy


class Incident(BaseModel):
    """Incident report for failures."""

    id: str
    timestamp: datetime
    severity: str  # "CRITICAL", "HIGH", "MEDIUM", "LOW"
    tool_name: str
    failure_category: FailureCategory
    root_cause: FailureRootCause
    recovery_attempted: bool
    recovery_successful: bool
    impact: str
    resolution: Optional[str] = None


class FallbackChain(BaseModel):
    """Fallback chain configuration."""

    primary: str  # Primary tool name
    secondary: Optional[str] = None  # Secondary tool
    tertiary: Optional[str] = None  # Tertiary tool
    cache_fallback: bool = True  # Use cache as last resort
    partial_result_acceptable: bool = False  # Accept partial results


class PartialResult(BaseModel):
    """Partial result aggregation."""

    tool_name: str
    completed_parts: List[Any]
    failed_parts: List[str]
    completion_rate: float  # 0.0 to 1.0
    usable: bool
    warnings: List[str] = Field(default_factory=list)


class ToolRecoveryManager:
    """
    Tool recovery manager.

    Manages tool health checks, retry logic, fallback chains, partial results,
    root cause analysis, and incident reporting.
    """

    def __init__(
        self,
        health_check_interval: float = 60.0,
        max_recent_failures: int = 5,
    ):
        """
        Initialize recovery manager.

        Args:
            health_check_interval: Seconds between health checks
            max_recent_failures: Max failures to track per tool
        """
        self.health_check_interval = health_check_interval
        self.max_recent_failures = max_recent_failures

        # Health tracking
        self._health_status: Dict[str, ToolHealthCheck] = {}
        self._failure_history: Dict[str, List[Tuple[datetime, Exception]]] = {}
        self._success_counts: Dict[str, int] = {}
        self._failure_counts: Dict[str, int] = {}

        # Fallback chains
        self._fallback_chains: Dict[str, FallbackChain] = {}

        # Incident tracking
        self._incidents: List[Incident] = []
        self._incident_counter = 0

        # Cache for partial results
        self._partial_results: Dict[str, PartialResult] = {}

        logger.info("ToolRecoveryManager initialized")

    def register_fallback_chain(self, chain: FallbackChain) -> None:
        """
        Register a fallback chain for a tool.

        Args:
            chain: Fallback chain configuration
        """
        self._fallback_chains[chain.primary] = chain
        logger.info(
            f"Registered fallback chain: {chain.primary} -> "
            f"{chain.secondary} -> {chain.tertiary}"
        )

    async def check_tool_health(
        self,
        tool_name: str,
        check_func: Callable,
    ) -> ToolHealthCheck:
        """
        Check health of a tool.

        Args:
            tool_name: Tool name
            check_func: Async function to check health

        Returns:
            Health check result
        """
        start_time = time.time()
        error_message = None

        try:
            await asyncio.wait_for(check_func(), timeout=5.0)
            success = True
        except asyncio.TimeoutError:
            success = False
            error_message = "Health check timeout"
        except Exception as e:
            success = False
            error_message = str(e)

        response_time = time.time() - start_time

        # Update success/failure counts
        if success:
            self._success_counts[tool_name] = self._success_counts.get(tool_name, 0) + 1
        else:
            self._failure_counts[tool_name] = self._failure_counts.get(tool_name, 0) + 1

        # Calculate success rate
        total = self._success_counts.get(tool_name, 0) + self._failure_counts.get(
            tool_name, 0
        )
        success_rate = self._success_counts.get(tool_name, 0) / total if total > 0 else 0.0

        # Determine health status
        recent_failures = self._failure_counts.get(tool_name, 0)
        if success_rate >= 0.95 and recent_failures < 2:
            status = ToolHealth.HEALTHY
        elif success_rate >= 0.80:
            status = ToolHealth.DEGRADED
        else:
            status = ToolHealth.UNHEALTHY

        health_check = ToolHealthCheck(
            tool_name=tool_name,
            status=status,
            last_check=datetime.now(),
            response_time=response_time,
            success_rate=success_rate,
            recent_failures=recent_failures,
            error_message=error_message,
        )

        self._health_status[tool_name] = health_check
        return health_check

    def analyze_failure_root_cause(
        self,
        tool_name: str,
        exception: Exception,
        context: Dict[str, Any],
    ) -> FailureRootCause:
        """
        Analyze root cause of a failure.

        Args:
            tool_name: Failed tool name
            exception: Exception that occurred
            context: Additional context

        Returns:
            Root cause analysis
        """
        error_message = str(exception).lower()
        category = FailureCategory.UNKNOWN
        primary_cause = str(exception)
        contributing_factors = []
        confidence = 0.5
        recommended_strategy = RecoveryStrategy.RETRY

        # Categorize failure
        if "timeout" in error_message or isinstance(exception, asyncio.TimeoutError):
            category = FailureCategory.TIMEOUT
            primary_cause = "Operation exceeded time limit"
            contributing_factors.append("Slow network or overloaded service")
            recommended_strategy = RecoveryStrategy.FALLBACK
            confidence = 0.9

        elif (
            "connection" in error_message
            or "network" in error_message
            or "unreachable" in error_message
        ):
            category = FailureCategory.NETWORK
            primary_cause = "Network connectivity issue"
            contributing_factors.append("Service unreachable or DNS failure")
            recommended_strategy = RecoveryStrategy.RETRY
            confidence = 0.85

        elif "auth" in error_message or "permission" in error_message or "403" in error_message:
            category = FailureCategory.AUTHENTICATION
            primary_cause = "Authentication or authorization failure"
            contributing_factors.append("Invalid credentials or expired token")
            recommended_strategy = RecoveryStrategy.ESCALATE
            confidence = 0.95

        elif "rate limit" in error_message or "429" in error_message or "quota" in error_message:
            category = FailureCategory.RATE_LIMIT
            primary_cause = "Rate limit exceeded"
            contributing_factors.append("Too many requests in time window")
            recommended_strategy = RecoveryStrategy.CACHE
            confidence = 0.9

        elif "invalid" in error_message or "validation" in error_message or "400" in error_message:
            category = FailureCategory.INVALID_INPUT
            primary_cause = "Invalid input parameters"
            contributing_factors.append("Incorrect parameter format or missing required fields")
            recommended_strategy = RecoveryStrategy.ABORT
            confidence = 0.85

        elif "500" in error_message or "internal" in error_message:
            category = FailureCategory.INTERNAL_ERROR
            primary_cause = "Internal service error"
            contributing_factors.append("Service bug or resource exhaustion")
            recommended_strategy = RecoveryStrategy.FALLBACK
            confidence = 0.8

        # Check for dependency failures
        if context.get("dependencies_failed"):
            category = FailureCategory.DEPENDENCY_FAILURE
            contributing_factors.append("Upstream dependency failures")

        # Check health history
        health = self._health_status.get(tool_name)
        if health and health.status == ToolHealth.UNHEALTHY:
            contributing_factors.append(f"Tool unhealthy (success rate: {health.success_rate:.1%})")

        return FailureRootCause(
            category=category,
            primary_cause=primary_cause,
            contributing_factors=contributing_factors,
            affected_tools=[tool_name],
            confidence=confidence,
            recommended_strategy=recommended_strategy,
        )

    async def execute_with_fallback(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        execute_func: Callable,
    ) -> Tuple[bool, Any, Optional[str]]:
        """
        Execute tool with fallback chain.

        Args:
            tool_name: Primary tool name
            parameters: Tool parameters
            execute_func: Function to execute tool (takes tool_name, parameters)

        Returns:
            Tuple of (success, result, tool_used)
        """
        # Get fallback chain
        chain = self._fallback_chains.get(tool_name)
        if not chain:
            # No fallback chain, execute normally
            try:
                result = await execute_func(tool_name, parameters)
                return True, result, tool_name
            except Exception as e:
                logger.error(f"Tool {tool_name} failed with no fallback: {e}")
                return False, None, None

        # Try primary tool
        tools_to_try = [chain.primary]
        if chain.secondary:
            tools_to_try.append(chain.secondary)
        if chain.tertiary:
            tools_to_try.append(chain.tertiary)

        last_error = None
        for current_tool in tools_to_try:
            try:
                logger.info(f"Trying tool: {current_tool}")
                result = await execute_func(current_tool, parameters)
                if current_tool != chain.primary:
                    logger.warning(f"Fallback successful: {current_tool} (primary {chain.primary} failed)")
                return True, result, current_tool

            except Exception as e:
                last_error = e
                logger.warning(f"Tool {current_tool} failed: {e}")
                continue

        # All tools failed, try cache if enabled
        if chain.cache_fallback:
            cached_result = self._get_cached_result(tool_name, parameters)
            if cached_result is not None:
                logger.warning(f"Using cached result for {tool_name}")
                return True, cached_result, "cache"

        # Check for partial results
        if chain.partial_result_acceptable:
            partial = self._partial_results.get(tool_name)
            if partial and partial.usable:
                logger.warning(f"Using partial result for {tool_name}")
                return True, partial.completed_parts, "partial"

        logger.error(f"All fallbacks exhausted for {tool_name}: {last_error}")
        return False, None, None

    def aggregate_partial_results(
        self,
        tool_name: str,
        completed_parts: List[Any],
        failed_parts: List[str],
        total_parts: int,
    ) -> PartialResult:
        """
        Aggregate partial results.

        Args:
            tool_name: Tool name
            completed_parts: Successfully completed parts
            failed_parts: Failed parts
            total_parts: Total expected parts

        Returns:
            Partial result
        """
        completion_rate = len(completed_parts) / total_parts if total_parts > 0 else 0.0
        usable = completion_rate >= 0.5  # Consider usable if >50% complete

        warnings = []
        if completion_rate < 0.8:
            warnings.append(f"Only {completion_rate:.0%} of results available")
        if failed_parts:
            warnings.append(f"Failed parts: {', '.join(failed_parts[:3])}")

        partial = PartialResult(
            tool_name=tool_name,
            completed_parts=completed_parts,
            failed_parts=failed_parts,
            completion_rate=completion_rate,
            usable=usable,
            warnings=warnings,
        )

        self._partial_results[tool_name] = partial
        return partial

    def create_incident(
        self,
        tool_name: str,
        exception: Exception,
        context: Dict[str, Any],
        recovery_attempted: bool,
        recovery_successful: bool,
    ) -> Incident:
        """
        Create incident report.

        Args:
            tool_name: Failed tool
            exception: Exception
            context: Additional context
            recovery_attempted: Whether recovery was tried
            recovery_successful: Whether recovery succeeded

        Returns:
            Incident report
        """
        # Analyze root cause
        root_cause = self.analyze_failure_root_cause(tool_name, exception, context)

        # Determine severity
        if root_cause.category in [
            FailureCategory.AUTHENTICATION,
            FailureCategory.DEPENDENCY_FAILURE,
        ]:
            severity = "CRITICAL"
        elif root_cause.category in [FailureCategory.INTERNAL_ERROR, FailureCategory.TIMEOUT]:
            severity = "HIGH"
        elif root_cause.category in [FailureCategory.RATE_LIMIT, FailureCategory.NETWORK]:
            severity = "MEDIUM"
        else:
            severity = "LOW"

        # Assess impact
        health = self._health_status.get(tool_name)
        if health and health.status == ToolHealth.UNHEALTHY:
            impact = f"Tool {tool_name} degraded (success rate: {health.success_rate:.1%})"
        else:
            impact = f"Single failure in {tool_name}"

        # Resolution
        resolution = None
        if recovery_successful:
            resolution = "Recovered automatically via fallback chain"
        elif recovery_attempted:
            resolution = "Recovery attempted but failed"

        self._incident_counter += 1
        incident = Incident(
            id=f"INC-{self._incident_counter:04d}",
            timestamp=datetime.now(),
            severity=severity,
            tool_name=tool_name,
            failure_category=root_cause.category,
            root_cause=root_cause,
            recovery_attempted=recovery_attempted,
            recovery_successful=recovery_successful,
            impact=impact,
            resolution=resolution,
        )

        self._incidents.append(incident)
        logger.warning(
            f"Incident created: {incident.id} - {severity} - {tool_name} - {root_cause.category}"
        )

        return incident

    def get_health_status(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get health status for tool(s).

        Args:
            tool_name: Specific tool or None for all

        Returns:
            Health status
        """
        if tool_name:
            health = self._health_status.get(tool_name)
            return {
                "tool": tool_name,
                "status": health.status if health else ToolHealth.UNKNOWN,
                "health": health.dict() if health else None,
            }

        return {
            "tools": {
                name: health.dict() for name, health in self._health_status.items()
            },
            "summary": {
                "total_tools": len(self._health_status),
                "healthy": sum(
                    1 for h in self._health_status.values() if h.status == ToolHealth.HEALTHY
                ),
                "degraded": sum(
                    1 for h in self._health_status.values() if h.status == ToolHealth.DEGRADED
                ),
                "unhealthy": sum(
                    1 for h in self._health_status.values() if h.status == ToolHealth.UNHEALTHY
                ),
            },
        }

    def get_incidents(
        self,
        severity: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> List[Incident]:
        """
        Get incident reports.

        Args:
            severity: Filter by severity
            since: Filter by time

        Returns:
            List of incidents
        """
        incidents = self._incidents

        if severity:
            incidents = [i for i in incidents if i.severity == severity]

        if since:
            incidents = [i for i in incidents if i.timestamp >= since]

        return incidents

    def get_recovery_statistics(self) -> Dict[str, Any]:
        """
        Get recovery statistics.

        Returns:
            Recovery stats
        """
        total_incidents = len(self._incidents)
        recovery_attempted = sum(1 for i in self._incidents if i.recovery_attempted)
        recovery_successful = sum(1 for i in self._incidents if i.recovery_successful)

        category_breakdown = {}
        for incident in self._incidents:
            category = incident.failure_category
            if category not in category_breakdown:
                category_breakdown[category] = 0
            category_breakdown[category] += 1

        return {
            "total_incidents": total_incidents,
            "recovery_attempted": recovery_attempted,
            "recovery_successful": recovery_successful,
            "recovery_rate": recovery_successful / recovery_attempted
            if recovery_attempted > 0
            else 0.0,
            "category_breakdown": category_breakdown,
            "recent_incidents": [i.dict() for i in self._incidents[-5:]],
        }

    def _get_cached_result(self, tool_name: str, parameters: Dict[str, Any]) -> Optional[Any]:
        """
        Get cached result (placeholder).

        Args:
            tool_name: Tool name
            parameters: Parameters

        Returns:
            Cached result or None
        """
        # TODO: Implement actual caching with Redis
        return None
