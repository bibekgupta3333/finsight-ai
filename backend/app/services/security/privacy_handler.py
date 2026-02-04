"""
Privacy Handler

GDPR-compliant data privacy implementation:
- PII detection and sanitization
- Data anonymization
- Encryption markers
- GDPR compliance tracking
- Data retention policies
"""

import re
import hashlib
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from pydantic import BaseModel, Field
from pathlib import Path

logger = logging.getLogger(__name__)


class PIIDetectionResult(BaseModel):
    """Result of PII detection scan"""
    pii_found: bool
    pii_types: List[str] = Field(default_factory=list)
    locations: List[Dict[str, Any]] = Field(default_factory=list)
    sanitized_text: str
    redaction_count: int


class AnonymizationResult(BaseModel):
    """Result of data anonymization"""
    original_id: str
    anonymized_id: str
    method: str  # "hash", "pseudonym", "token"
    reversible: bool


class GDPRConsent(BaseModel):
    """GDPR consent record"""
    user_id: str
    consent_type: str  # "data_collection", "data_processing", "data_sharing"
    granted: bool
    timestamp: datetime
    ip_address: Optional[str] = None
    consent_version: str = "1.0"


class DataRetentionPolicy(BaseModel):
    """Data retention policy"""
    data_type: str
    retention_days: int
    auto_delete: bool
    legal_hold: bool = False


class PrivacyAudit(BaseModel):
    """Privacy compliance audit record"""
    audit_id: str
    timestamp: datetime
    data_accessed: List[str]
    purpose: str
    user_id: str
    consent_verified: bool
    retention_compliant: bool
    audit_trail: List[str] = Field(default_factory=list)


class PrivacyHandler:
    """Privacy and GDPR compliance handler"""

    def __init__(self):
        self.data_dir = Path("data/privacy")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.consents_file = self.data_dir / "gdpr_consents.jsonl"
        self.audits_file = self.data_dir / "privacy_audits.jsonl"
        self.retention_file = self.data_dir / "retention_policies.json"

        # Default retention policies (in days)
        self.retention_policies = {
            "transaction_logs": DataRetentionPolicy(
                data_type="transaction_logs",
                retention_days=2555,  # 7 years (regulatory requirement)
                auto_delete=False,
                legal_hold=True
            ),
            "user_data": DataRetentionPolicy(
                data_type="user_data",
                retention_days=365,  # 1 year
                auto_delete=True,
                legal_hold=False
            ),
            "fraud_reports": DataRetentionPolicy(
                data_type="fraud_reports",
                retention_days=1825,  # 5 years
                auto_delete=False,
                legal_hold=True
            ),
            "audit_logs": DataRetentionPolicy(
                data_type="audit_logs",
                retention_days=2555,  # 7 years
                auto_delete=False,
                legal_hold=True
            ),
            "pii_data": DataRetentionPolicy(
                data_type="pii_data",
                retention_days=365,  # 1 year
                auto_delete=True,
                legal_hold=False
            )
        }

        # PII detection patterns
        self.pii_patterns = {
            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "phone": r'\b(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',
            "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
            "credit_card": r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
            "ip_address": r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
            "date_of_birth": r'\b\d{2}/\d{2}/\d{4}\b',
            "name": r'\b[A-Z][a-z]+\s[A-Z][a-z]+\b',  # Simple pattern for first+last
            "address": r'\b\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd)\b'
        }

    # ========== PII Detection & Sanitization ==========

    def detect_pii(self, text: str) -> PIIDetectionResult:
        """
        Detect personally identifiable information in text.

        Args:
            text: Input text to scan

        Returns:
            PIIDetectionResult with found PII and sanitized version
        """
        pii_found = False
        pii_types = []
        locations = []
        sanitized = text
        redaction_count = 0

        for pii_type, pattern in self.pii_patterns.items():
            matches = list(re.finditer(pattern, text))

            if matches:
                pii_found = True
                pii_types.append(pii_type)

                for match in matches:
                    locations.append({
                        "type": pii_type,
                        "start": match.start(),
                        "end": match.end(),
                        "value": match.group()
                    })

                    # Redact in sanitized version
                    redaction_label = f"[{pii_type.upper()}_REDACTED]"
                    sanitized = re.sub(pattern, redaction_label, sanitized)
                    redaction_count += len(matches)

        return PIIDetectionResult(
            pii_found=pii_found,
            pii_types=pii_types,
            locations=locations,
            sanitized_text=sanitized,
            redaction_count=redaction_count
        )

    def sanitize_transaction_data(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize transaction data by removing/redacting PII.

        Args:
            transaction: Raw transaction dictionary

        Returns:
            Sanitized transaction with PII redacted
        """
        sanitized = transaction.copy()

        # Fields that might contain PII
        pii_fields = ["nameOrig", "nameDest", "memo", "description"]

        for field in pii_fields:
            if field in sanitized and isinstance(sanitized[field], str):
                detection = self.detect_pii(sanitized[field])
                if detection.pii_found:
                    sanitized[field] = detection.sanitized_text
                    logger.info(f"Redacted {detection.redaction_count} PII instances in field '{field}'")

        return sanitized

    def anonymize_user_id(self, user_id: str, method: str = "hash") -> AnonymizationResult:
        """
        Anonymize user identifier.

        Args:
            user_id: Original user ID
            method: Anonymization method ("hash", "pseudonym", "token")

        Returns:
            AnonymizationResult with anonymized ID
        """
        if method == "hash":
            # SHA-256 hash (irreversible)
            anonymized = hashlib.sha256(user_id.encode()).hexdigest()[:16]
            reversible = False
        elif method == "pseudonym":
            # Pseudonym mapping (reversible if mapping is stored)
            import secrets
            anonymized = f"user_{secrets.token_hex(8)}"
            reversible = True
        elif method == "token":
            # Secure token (irreversible)
            import secrets
            anonymized = secrets.token_urlsafe(16)
            reversible = False
        else:
            raise ValueError(f"Unknown anonymization method: {method}")

        return AnonymizationResult(
            original_id=user_id,
            anonymized_id=anonymized,
            method=method,
            reversible=reversible
        )

    # ========== GDPR Compliance ==========

    def record_consent(self, consent: GDPRConsent) -> None:
        """
        Record GDPR consent.

        Args:
            consent: GDPRConsent record
        """
        with open(self.consents_file, 'a') as f:
            f.write(consent.model_dump_json() + '\n')

        logger.info(
            f"Recorded {consent.consent_type} consent for user {consent.user_id}: "
            f"{'granted' if consent.granted else 'denied'}"
        )

    def verify_consent(self, user_id: str, consent_type: str) -> bool:
        """
        Verify if user has granted consent.

        Args:
            user_id: User identifier
            consent_type: Type of consent to check

        Returns:
            True if consent granted, False otherwise
        """
        if not self.consents_file.exists():
            return False

        # Read consents in reverse (most recent first)
        with open(self.consents_file, 'r') as f:
            consents = [json.loads(line) for line in f]

        # Find most recent consent for this user and type
        for consent_data in reversed(consents):
            if (consent_data["user_id"] == user_id and
                consent_data["consent_type"] == consent_type):
                return consent_data["granted"]

        return False

    def get_user_data(self, user_id: str) -> Dict[str, Any]:
        """
        Get all data for a user (GDPR data portability right).

        Args:
            user_id: User identifier

        Returns:
            Dictionary with all user data
        """
        user_data = {
            "user_id": user_id,
            "consents": [],
            "audits": [],
            "export_timestamp": datetime.utcnow().isoformat()
        }

        # Get consents
        if self.consents_file.exists():
            with open(self.consents_file, 'r') as f:
                consents = [
                    json.loads(line) for line in f
                    if json.loads(line)["user_id"] == user_id
                ]
                user_data["consents"] = consents

        # Get audits
        if self.audits_file.exists():
            with open(self.audits_file, 'r') as f:
                audits = [
                    json.loads(line) for line in f
                    if json.loads(line)["user_id"] == user_id
                ]
                user_data["audits"] = audits

        logger.info(f"Exported data for user {user_id}: {len(consents)} consents, {len(audits)} audits")

        return user_data

    def delete_user_data(self, user_id: str) -> Dict[str, int]:
        """
        Delete all user data (GDPR right to erasure).

        Args:
            user_id: User identifier

        Returns:
            Dictionary with count of deleted records
        """
        deleted_counts = {
            "consents": 0,
            "audits": 0
        }

        # Delete consents
        if self.consents_file.exists():
            consents = []
            with open(self.consents_file, 'r') as f:
                for line in f:
                    consent_data = json.loads(line)
                    if consent_data["user_id"] != user_id:
                        consents.append(line)
                    else:
                        deleted_counts["consents"] += 1

            with open(self.consents_file, 'w') as f:
                f.writelines(consents)

        # Delete audits
        if self.audits_file.exists():
            audits = []
            with open(self.audits_file, 'r') as f:
                for line in f:
                    audit_data = json.loads(line)
                    if audit_data["user_id"] != user_id:
                        audits.append(line)
                    else:
                        deleted_counts["audits"] += 1

            with open(self.audits_file, 'w') as f:
                f.writelines(audits)

        logger.info(f"Deleted data for user {user_id}: {deleted_counts}")

        return deleted_counts

    # ========== Data Retention ==========

    def get_retention_policy(self, data_type: str) -> Optional[DataRetentionPolicy]:
        """Get retention policy for data type"""
        return self.retention_policies.get(data_type)

    def check_retention_compliance(self, data_type: str, data_age_days: int) -> bool:
        """
        Check if data age complies with retention policy.

        Args:
            data_type: Type of data
            data_age_days: Age of data in days

        Returns:
            True if compliant (within retention period), False if should be deleted
        """
        policy = self.get_retention_policy(data_type)

        if not policy:
            logger.warning(f"No retention policy for data type: {data_type}")
            return True  # Default to keeping data if no policy

        if policy.legal_hold:
            return True  # Never delete data under legal hold

        return data_age_days <= policy.retention_days

    def get_expired_data(self, data_type: str, records: List[Dict]) -> List[Dict]:
        """
        Filter records that have exceeded retention period.

        Args:
            data_type: Type of data
            records: List of records with 'timestamp' field

        Returns:
            List of expired records
        """
        policy = self.get_retention_policy(data_type)

        if not policy or policy.legal_hold:
            return []

        cutoff_date = datetime.utcnow() - timedelta(days=policy.retention_days)

        expired = [
            record for record in records
            if datetime.fromisoformat(record["timestamp"]) < cutoff_date
        ]

        return expired

    # ========== Privacy Auditing ==========

    def record_privacy_audit(self, audit: PrivacyAudit) -> None:
        """
        Record privacy audit trail.

        Args:
            audit: PrivacyAudit record
        """
        with open(self.audits_file, 'a') as f:
            f.write(audit.model_dump_json() + '\n')

        logger.info(f"Recorded privacy audit {audit.audit_id} for user {audit.user_id}")

    def get_privacy_dashboard(self, days: int = 7) -> Dict[str, Any]:
        """
        Get privacy compliance dashboard.

        Args:
            days: Number of days to include

        Returns:
            Dashboard with compliance metrics
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        dashboard = {
            "period_days": days,
            "total_audits": 0,
            "consent_violations": 0,
            "retention_violations": 0,
            "pii_accessed": 0,
            "data_types_accessed": set(),
            "audit_trail": []
        }

        if not self.audits_file.exists():
            return dashboard

        with open(self.audits_file, 'r') as f:
            for line in f:
                audit_data = json.loads(line)
                audit_time = datetime.fromisoformat(audit_data["timestamp"])

                if audit_time < cutoff:
                    continue

                dashboard["total_audits"] += 1

                if not audit_data["consent_verified"]:
                    dashboard["consent_violations"] += 1

                if not audit_data["retention_compliant"]:
                    dashboard["retention_violations"] += 1

                dashboard["data_types_accessed"].update(audit_data["data_accessed"])

                if len(dashboard["audit_trail"]) < 10:  # Last 10 audits
                    dashboard["audit_trail"].append({
                        "audit_id": audit_data["audit_id"],
                        "timestamp": audit_data["timestamp"],
                        "user_id": audit_data["user_id"],
                        "purpose": audit_data["purpose"],
                        "compliant": audit_data["consent_verified"] and audit_data["retention_compliant"]
                    })

        dashboard["data_types_accessed"] = list(dashboard["data_types_accessed"])

        return dashboard

    # ========== Encryption Markers ==========

    def mark_for_encryption(self, data: Dict[str, Any], fields: List[str]) -> Dict[str, Any]:
        """
        Mark fields for encryption (metadata only, actual encryption done by data layer).

        Args:
            data: Data dictionary
            fields: Fields to mark for encryption

        Returns:
            Data with encryption metadata
        """
        marked = data.copy()
        marked["_encryption_metadata"] = {
            "encrypted_fields": fields,
            "encryption_required": True,
            "marked_at": datetime.utcnow().isoformat()
        }

        return marked

    def verify_encryption(self, data: Dict[str, Any]) -> bool:
        """
        Verify if data has encryption metadata.

        Args:
            data: Data dictionary

        Returns:
            True if encryption metadata present
        """
        return "_encryption_metadata" in data and data["_encryption_metadata"].get("encryption_required", False)


# Global instance
privacy_handler = PrivacyHandler()
