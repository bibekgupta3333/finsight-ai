"""
Security Manager

Production-grade security implementation:
- JWT authentication
- Rate limiting
- Input validation and sanitization
- File upload security
- Secrets management helpers
"""

import jwt
import hashlib
import time
import re
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List
from pydantic import BaseModel, Field, validator
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


# JWT Configuration
JWT_SECRET_KEY = secrets.token_urlsafe(32)  # In production, use env variable
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24


class TokenData(BaseModel):
    """JWT token data"""
    user_id: str
    username: str
    roles: List[str] = Field(default_factory=list)
    exp: Optional[datetime] = None


class RateLimitConfig(BaseModel):
    """Rate limit configuration"""
    max_requests: int
    window_seconds: int
    identifier: str  # IP, user_id, or API key


class ValidationResult(BaseModel):
    """Input validation result"""
    is_valid: bool
    sanitized_input: Any
    validation_errors: List[str] = Field(default_factory=list)
    security_warnings: List[str] = Field(default_factory=list)


class FileUploadResult(BaseModel):
    """File upload validation result"""
    is_safe: bool
    file_type: str
    file_size: int
    security_issues: List[str] = Field(default_factory=list)
    sanitized_filename: str


class SecurityManager:
    """Security implementation for fraud detection system"""

    def __init__(self):
        # Rate limiting storage (in production, use Redis)
        self.rate_limit_store: Dict[str, List[float]] = defaultdict(list)

        # Allowed file extensions for uploads
        self.allowed_extensions = {'.csv', '.json', '.txt', '.pdf'}
        self.max_file_size_mb = 10

    # ========== JWT Authentication ==========

    def create_access_token(
        self,
        user_id: str,
        username: str,
        roles: List[str] = None,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create JWT access token.

        Args:
            user_id: Unique user identifier
            username: Username
            roles: User roles for authorization
            expires_delta: Custom expiration time

        Returns:
            JWT token string
        """
        if expires_delta is None:
            expires_delta = timedelta(hours=JWT_EXPIRATION_HOURS)

        expire = datetime.utcnow() + expires_delta

        payload = {
            "sub": user_id,
            "username": username,
            "roles": roles or ["user"],
            "exp": expire,
            "iat": datetime.utcnow()
        }

        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        logger.info(f"Created access token for user {username}")

        return token

    def verify_token(self, token: str) -> Optional[TokenData]:
        """
        Verify and decode JWT token.

        Args:
            token: JWT token string

        Returns:
            TokenData if valid, None if invalid
        """
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

            return TokenData(
                user_id=payload["sub"],
                username=payload["username"],
                roles=payload.get("roles", ["user"]),
                exp=datetime.fromtimestamp(payload["exp"])
            )
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.JWTError as e:
            logger.error(f"JWT validation error: {e}")
            return None

    def refresh_token(self, old_token: str) -> Optional[str]:
        """
        Refresh an existing token.

        Args:
            old_token: Existing JWT token

        Returns:
            New token if old token is valid, None otherwise
        """
        token_data = self.verify_token(old_token)
        if not token_data:
            return None

        # Create new token with same data
        return self.create_access_token(
            user_id=token_data.user_id,
            username=token_data.username,
            roles=token_data.roles
        )

    # ========== Rate Limiting ==========

    def check_rate_limit(self, config: RateLimitConfig) -> bool:
        """
        Check if request is within rate limit.

        Args:
            config: Rate limit configuration

        Returns:
            True if within limit, False if exceeded
        """
        now = time.time()
        key = f"{config.identifier}"

        # Get requests in current window
        requests = self.rate_limit_store[key]

        # Remove old requests outside window
        cutoff = now - config.window_seconds
        requests = [req_time for req_time in requests if req_time > cutoff]

        # Update store
        self.rate_limit_store[key] = requests

        # Check if limit exceeded
        if len(requests) >= config.max_requests:
            logger.warning(
                f"Rate limit exceeded for {config.identifier}: "
                f"{len(requests)}/{config.max_requests} in {config.window_seconds}s"
            )
            return False

        # Add current request
        requests.append(now)
        self.rate_limit_store[key] = requests

        return True

    def get_rate_limit_status(self, identifier: str, window_seconds: int = 60) -> Dict[str, Any]:
        """
        Get current rate limit status for identifier.

        Args:
            identifier: Rate limit identifier
            window_seconds: Time window

        Returns:
            Status dictionary with request count and remaining
        """
        now = time.time()
        cutoff = now - window_seconds

        requests = [
            req_time for req_time in self.rate_limit_store.get(identifier, [])
            if req_time > cutoff
        ]

        return {
            "identifier": identifier,
            "requests_in_window": len(requests),
            "window_seconds": window_seconds,
            "oldest_request_age": int(now - requests[0]) if requests else 0
        }

    # ========== Input Validation & Sanitization ==========

    def validate_transaction_input(self, data: Dict[str, Any]) -> ValidationResult:
        """
        Validate and sanitize transaction input.

        Checks for:
        - Required fields
        - Data types
        - Value ranges
        - SQL injection patterns
        - XSS patterns
        """
        errors = []
        warnings = []
        sanitized = data.copy()

        # Required fields
        required_fields = ["amount", "type"]
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")

        # Validate amount
        if "amount" in data:
            try:
                amount = float(data["amount"])
                if amount < 0:
                    errors.append("Amount cannot be negative")
                if amount > 10_000_000:
                    warnings.append(f"Unusually high amount: ${amount:,.2f}")
                sanitized["amount"] = amount
            except (ValueError, TypeError):
                errors.append("Invalid amount: must be a number")

        # Validate transaction type
        if "type" in data:
            valid_types = ["PAYMENT", "TRANSFER", "CASH_OUT", "DEBIT", "CASH_IN"]
            if data["type"].upper() not in valid_types:
                errors.append(f"Invalid transaction type: {data['type']}")
            else:
                sanitized["type"] = data["type"].upper()

        # Check for SQL injection patterns
        sql_patterns = [
            r"('\s*OR\s*'?\d*'?\s*=\s*'?\d*)",
            r"(--|\#|\/\*)",
            r"(DROP|DELETE|INSERT|UPDATE|SELECT.*FROM)",
            r"(UNION.*SELECT)",
            r"(xp_cmdshell|exec\s*\()"
        ]

        for key, value in data.items():
            if isinstance(value, str):
                for pattern in sql_patterns:
                    if re.search(pattern, value, re.IGNORECASE):
                        warnings.append(f"Potential SQL injection in field '{key}'")
                        # Escape single quotes
                        sanitized[key] = value.replace("'", "''")
                        break

        # Check for XSS patterns
        xss_patterns = [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"on\w+\s*=",
            r"<iframe",
            r"<embed"
        ]

        for key, value in data.items():
            if isinstance(value, str):
                for pattern in xss_patterns:
                    if re.search(pattern, value, re.IGNORECASE):
                        warnings.append(f"Potential XSS in field '{key}'")
                        # Strip HTML tags
                        sanitized[key] = re.sub(r'<[^>]+>', '', value)
                        break

        # Validate string lengths
        for key, value in data.items():
            if isinstance(value, str) and len(value) > 1000:
                warnings.append(f"Field '{key}' exceeds reasonable length (1000 chars)")
                sanitized[key] = value[:1000]  # Truncate

        is_valid = len(errors) == 0

        return ValidationResult(
            is_valid=is_valid,
            sanitized_input=sanitized,
            validation_errors=errors,
            security_warnings=warnings
        )

    def sanitize_string(self, input_str: str) -> str:
        """
        Sanitize string input for safe processing.

        Removes:
        - HTML tags
        - SQL injection patterns
        - Control characters
        - Excessive whitespace
        """
        # Remove HTML tags
        sanitized = re.sub(r'<[^>]+>', '', input_str)

        # Remove control characters except newline and tab
        sanitized = ''.join(
            char for char in sanitized
            if char.isprintable() or char in '\n\t'
        )

        # Collapse excessive whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized)

        # Escape single quotes for SQL safety
        sanitized = sanitized.replace("'", "''")

        # Trim
        sanitized = sanitized.strip()

        return sanitized

    # ========== File Upload Security ==========

    def validate_file_upload(
        self,
        filename: str,
        file_content: bytes,
        expected_type: Optional[str] = None
    ) -> FileUploadResult:
        """
        Validate file upload for security.

        Checks:
        - File extension whitelist
        - File size limits
        - Magic bytes verification
        - Filename sanitization
        """
        issues = []

        # Sanitize filename
        sanitized_filename = self._sanitize_filename(filename)

        # Check extension
        import os
        _, ext = os.path.splitext(sanitized_filename)
        ext = ext.lower()

        if ext not in self.allowed_extensions:
            issues.append(f"File extension '{ext}' not allowed. Allowed: {self.allowed_extensions}")

        # Check file size
        file_size = len(file_content)
        max_size = self.max_file_size_mb * 1024 * 1024

        if file_size > max_size:
            issues.append(f"File size {file_size} bytes exceeds maximum {max_size} bytes")

        # Detect file type from magic bytes
        detected_type = self._detect_file_type(file_content)

        # Verify expected type if provided
        if expected_type and detected_type != expected_type:
            issues.append(
                f"File type mismatch: expected {expected_type}, detected {detected_type}"
            )

        is_safe = len(issues) == 0

        return FileUploadResult(
            is_safe=is_safe,
            file_type=detected_type,
            file_size=file_size,
            security_issues=issues,
            sanitized_filename=sanitized_filename
        )

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent directory traversal"""
        # Remove directory components
        import os
        filename = os.path.basename(filename)

        # Remove special characters
        filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)

        # Prevent hidden files
        if filename.startswith('.'):
            filename = '_' + filename

        # Limit length
        if len(filename) > 255:
            name, ext = os.path.splitext(filename)
            filename = name[:250] + ext

        return filename

    def _detect_file_type(self, content: bytes) -> str:
        """Detect file type from magic bytes"""
        if not content:
            return "empty"

        # CSV (text file)
        try:
            content[:1024].decode('utf-8')
            if b',' in content[:1024]:
                return "csv"
            return "text"
        except UnicodeDecodeError:
            pass

        # JSON
        if content[:1].strip() in [b'{', b'[']:
            return "json"

        # PDF
        if content[:4] == b'%PDF':
            return "pdf"

        return "unknown"

    # ========== Secrets Management Helpers ==========

    def hash_api_key(self, api_key: str) -> str:
        """
        Hash API key for secure storage.

        Uses SHA-256 for one-way hashing.
        """
        return hashlib.sha256(api_key.encode()).hexdigest()

    def generate_api_key(self, prefix: str = "fsk") -> str:
        """
        Generate secure API key.

        Args:
            prefix: Key prefix for identification

        Returns:
            API key in format: prefix_random32chars
        """
        random_part = secrets.token_urlsafe(32)
        return f"{prefix}_{random_part}"

    def verify_api_key(self, provided_key: str, stored_hash: str) -> bool:
        """
        Verify API key against stored hash.

        Args:
            provided_key: API key provided by user
            stored_hash: Stored hash of valid API key

        Returns:
            True if key matches hash
        """
        provided_hash = self.hash_api_key(provided_key)
        return secrets.compare_digest(provided_hash, stored_hash)


# Global instance
security_manager = SecurityManager()
