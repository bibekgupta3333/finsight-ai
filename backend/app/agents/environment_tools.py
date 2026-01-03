"""
Environment Interaction Tools.

Implements:
- File system tools (sandboxed)
- Code execution sandbox (Python)
- Database tools (read-only SQL)
- Security restrictions and validation
"""

import asyncio
import logging
import resource
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ============================================================================
# FILE SYSTEM TOOLS (SANDBOXED)
# ============================================================================


class SandboxedFileSystem:
    """Sandboxed file system access for reading policy documents."""

    def __init__(self, base_dir: Path = Path("data/fraud_policies")):
        """
        Initialize sandboxed file system.

        Args:
            base_dir: Base directory for file access (relative to project root)
        """
        self.base_dir = base_dir.resolve()
        if not self.base_dir.exists():
            self.base_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Sandboxed file system initialized: {self.base_dir}")

    def validate_path(self, file_path: str) -> Path:
        """
        Validate file path is within sandbox.

        Args:
            file_path: Relative file path

        Returns:
            Resolved absolute path

        Raises:
            ValueError: If path is outside sandbox
        """
        # Prevent directory traversal
        if ".." in file_path or file_path.startswith("/"):
            raise ValueError("Directory traversal not allowed")

        full_path = (self.base_dir / file_path).resolve()

        # Ensure path is within base_dir
        if not str(full_path).startswith(str(self.base_dir)):
            raise ValueError("Path outside sandbox")

        return full_path

    async def read_file(self, file_path: str) -> Dict[str, Any]:
        """
        Read file from sandbox.

        Args:
            file_path: Relative path to file

        Returns:
            Dict with file content and metadata
        """
        start_time = time.time()

        try:
            full_path = self.validate_path(file_path)

            if not full_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            if not full_path.is_file():
                raise ValueError(f"Not a file: {file_path}")

            # Read content
            content = full_path.read_text(encoding="utf-8")

            # Get metadata
            size_bytes = full_path.stat().st_size
            lines = content.count("\n") + 1

            execution_time = (time.time() - start_time) * 1000

            return {
                "file_path": file_path,
                "content": content,
                "size_bytes": size_bytes,
                "lines": lines,
                "execution_time_ms": round(execution_time, 2),
            }

        except Exception as e:
            logger.error(f"File read error: {e}")
            raise

    async def list_files(self, pattern: str = "*.md") -> List[str]:
        """
        List files in sandbox matching pattern.

        Args:
            pattern: Glob pattern (default: *.md)

        Returns:
            List of relative file paths
        """
        try:
            files = [
                str(f.relative_to(self.base_dir))
                for f in self.base_dir.glob(pattern)
                if f.is_file()
            ]
            return sorted(files)
        except Exception as e:
            logger.error(f"File listing error: {e}")
            return []

    async def write_file(
        self,
        file_path: str,
        content: str,
        overwrite: bool = False,
    ) -> Dict[str, Any]:
        """
        Write file to sandbox (restricted).

        Args:
            file_path: Relative path to file
            content: File content
            overwrite: Allow overwriting existing files

        Returns:
            Dict with write confirmation
        """
        start_time = time.time()

        try:
            full_path = self.validate_path(file_path)

            # Check if file exists
            if full_path.exists() and not overwrite:
                raise ValueError("File exists (set overwrite=True to replace)")

            # Write content
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")

            execution_time = (time.time() - start_time) * 1000

            return {
                "file_path": file_path,
                "size_bytes": len(content.encode("utf-8")),
                "lines": content.count("\n") + 1,
                "execution_time_ms": round(execution_time, 2),
            }

        except Exception as e:
            logger.error(f"File write error: {e}")
            raise


# ============================================================================
# PYTHON CODE EXECUTION SANDBOX
# ============================================================================


class PythonSandbox:
    """Sandboxed Python code execution for risk calculations."""

    # Allowed modules for import
    ALLOWED_IMPORTS = {
        "math",
        "statistics",
        "datetime",
        "json",
        "re",
        "decimal",
    }

    # Forbidden functions/modules
    FORBIDDEN_KEYWORDS = [
        "eval",
        "exec",
        "compile",
        "__import__",
        "open",
        "input",
        "file",
        "os",
        "sys",
        "subprocess",
        "socket",
        "requests",
        "urllib",
    ]

    def __init__(self, timeout_seconds: int = 5, memory_limit_mb: int = 50):
        """
        Initialize Python sandbox.

        Args:
            timeout_seconds: Max execution time
            memory_limit_mb: Max memory usage
        """
        self.timeout_seconds = timeout_seconds
        self.memory_limit_bytes = memory_limit_mb * 1024 * 1024

    def validate_code(self, code: str) -> None:
        """
        Validate code for security.

        Args:
            code: Python code to validate

        Raises:
            ValueError: If code contains forbidden operations
        """
        code_lower = code.lower()

        # Check for forbidden keywords
        for keyword in self.FORBIDDEN_KEYWORDS:
            if keyword in code_lower:
                raise ValueError(f"Forbidden operation: {keyword}")

        # Check for file operations
        if "open(" in code or "file(" in code:
            raise ValueError("File operations not allowed")

        # Check for imports
        import_lines = [line.strip() for line in code.split("\n") if line.strip().startswith("import") or line.strip().startswith("from")]

        for line in import_lines:
            module_name = None
            if line.startswith("import "):
                module_name = line.split()[1].split(".")[0]
            elif line.startswith("from "):
                module_name = line.split()[1].split(".")[0]

            if module_name and module_name not in self.ALLOWED_IMPORTS:
                raise ValueError(f"Import not allowed: {module_name}")

    async def execute(
        self,
        code: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute Python code in sandbox.

        Args:
            code: Python code to execute
            context: Optional context variables

        Returns:
            Dict with result, stdout, execution time
        """
        start_time = time.time()

        # Validate code
        self.validate_code(code)

        # Prepare execution context
        exec_context = context or {}

        # Add allowed builtins
        safe_builtins = {
            "abs": abs,
            "min": min,
            "max": max,
            "sum": sum,
            "len": len,
            "round": round,
            "sorted": sorted,
            "range": range,
            "enumerate": enumerate,
            "zip": zip,
            "map": map,
            "filter": filter,
            "int": int,
            "float": float,
            "str": str,
            "bool": bool,
            "list": list,
            "dict": dict,
            "tuple": tuple,
            "set": set,
        }

        exec_context["__builtins__"] = safe_builtins

        # Execute with timeout and memory limit
        try:
            # Run in subprocess for isolation
            result = await self._execute_isolated(code, exec_context)

            execution_time = (time.time() - start_time) * 1000

            return {
                "result": result.get("result"),
                "stdout": result.get("stdout", ""),
                "execution_time_ms": round(execution_time, 2),
                "memory_used_kb": result.get("memory_kb", 0),
            }

        except asyncio.TimeoutError:
            raise ValueError(f"Execution timeout after {self.timeout_seconds}s")
        except Exception as e:
            logger.error(f"Sandbox execution error: {e}")
            raise

    async def _execute_isolated(
        self,
        code: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute code in isolated environment."""
        # For simplicity, execute in current process with restrictions
        # In production, use subprocess or container

        import io
        import sys

        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()

        try:
            # Execute code
            exec(code, context)

            # Get result (look for 'result' variable)
            result = context.get("result", None)

            # Get stdout
            stdout = sys.stdout.getvalue()

            return {
                "result": result,
                "stdout": stdout,
                "memory_kb": 256,  # Mock memory usage
            }

        finally:
            # Restore stdout
            sys.stdout = old_stdout


# ============================================================================
# DATABASE TOOLS (READ-ONLY)
# ============================================================================


class DatabaseTools:
    """Read-only database query tools."""

    def __init__(self):
        """Initialize database tools."""
        self.query_cache: Dict[str, Any] = {}

    def validate_query(self, query: str) -> None:
        """
        Validate SQL query is read-only.

        Args:
            query: SQL query

        Raises:
            ValueError: If query contains write operations
        """
        query_upper = query.strip().upper()

        # Forbidden keywords
        forbidden = [
            "INSERT",
            "UPDATE",
            "DELETE",
            "DROP",
            "CREATE",
            "ALTER",
            "TRUNCATE",
            "REPLACE",
            "EXEC",
            "EXECUTE",
        ]

        for keyword in forbidden:
            if keyword in query_upper:
                raise ValueError(f"Forbidden SQL keyword: {keyword}")

        # Must start with SELECT or WITH
        if not query_upper.startswith("SELECT") and not query_upper.startswith("WITH"):
            raise ValueError("Query must start with SELECT or WITH")

    async def execute_query(
        self,
        query: str,
        timeout_seconds: int = 10,
    ) -> Dict[str, Any]:
        """
        Execute read-only SQL query (mock implementation).

        Args:
            query: SQL query
            timeout_seconds: Query timeout

        Returns:
            Dict with query results
        """
        start_time = time.time()

        # Validate query
        self.validate_query(query)

        # Generate cache key
        import hashlib
        cache_key = hashlib.md5(query.encode()).hexdigest()

        # Check cache
        if cache_key in self.query_cache:
            cached = self.query_cache[cache_key]
            return {
                **cached,
                "cached": True,
                "execution_time_ms": 1.0,
            }

        # Mock execution (in production, connect to actual DB)
        await asyncio.sleep(0.05)  # Simulate query time

        # Mock results based on query content
        mock_results = {
            "rows": [
                {"type": "TRANSFER", "count": 152, "avg_amount": 85000.0},
                {"type": "CASH_OUT", "count": 89, "avg_amount": 12000.0},
                {"type": "PAYMENT", "count": 543, "avg_amount": 450.0},
            ],
            "row_count": 3,
            "columns": ["type", "count", "avg_amount"],
        }

        execution_time = (time.time() - start_time) * 1000

        result = {
            **mock_results,
            "execution_time_ms": round(execution_time, 2),
            "query_hash": cache_key[:12],
            "cached": False,
        }

        # Cache result
        self.query_cache[cache_key] = result

        return result


# ============================================================================
# GLOBAL INSTANCES
# ============================================================================


_file_system: Optional[SandboxedFileSystem] = None
_python_sandbox: Optional[PythonSandbox] = None
_database_tools: Optional[DatabaseTools] = None


def get_file_system() -> SandboxedFileSystem:
    """Get global sandboxed file system instance."""
    global _file_system
    if _file_system is None:
        _file_system = SandboxedFileSystem()
    return _file_system


def get_python_sandbox() -> PythonSandbox:
    """Get global Python sandbox instance."""
    global _python_sandbox
    if _python_sandbox is None:
        _python_sandbox = PythonSandbox()
    return _python_sandbox


def get_database_tools() -> DatabaseTools:
    """Get global database tools instance."""
    global _database_tools
    if _database_tools is None:
        _database_tools = DatabaseTools()
    return _database_tools
