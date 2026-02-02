"""
Model Registry with Version Tracking and Rollback.

Manages model versions, metadata, and deployment lifecycle.
Enables zero-downtime rollback to previous versions.
"""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Paths
BACKEND_DIR = Path(__file__).parent.parent.parent
MODELS_DIR = BACKEND_DIR / "models"
REGISTRY_FILE = MODELS_DIR / "model_registry.json"
ARCHIVE_DIR = MODELS_DIR / "archive"
ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)


class ModelRegistry:
    """
    Central registry for ML model versions and metadata.

    Features:
    - Version tracking
    - Production/staging environments
    - Rollback capability
    - Metadata storage
    - Audit trails
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelRegistry, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize model registry."""
        if self._initialized:
            return

        self.registry = self._load_registry()
        self._initialized = True

        logger.info(f"Model Registry initialized from {REGISTRY_FILE}")

    def _load_registry(self) -> Dict:
        """
        Load registry from disk.

        Returns:
            Dict with registry data
        """
        if REGISTRY_FILE.exists():
            with open(REGISTRY_FILE, "r") as f:
                registry = json.load(f)
            logger.info(f"Loaded registry with {len(registry.get('models', {}))} models")
            return registry
        else:
            # Initialize empty registry
            registry = {
                "created_at": datetime.utcnow().isoformat(),
                "last_updated": datetime.utcnow().isoformat(),
                "models": {}
            }
            self._save_registry(registry)
            logger.info("Created new model registry")
            return registry

    def _save_registry(self, registry: Dict = None):
        """
        Save registry to disk.

        Args:
            registry: Registry data (uses self.registry if None)
        """
        if registry is None:
            registry = self.registry

        registry["last_updated"] = datetime.utcnow().isoformat()

        with open(REGISTRY_FILE, "w") as f:
            json.dump(registry, f, indent=2)

        logger.debug("Registry saved")

    def register_model(
        self,
        model_name: str,
        version: str,
        performance: Dict,
        metadata: Optional[Dict] = None,
        environment: str = "staging"
    ) -> bool:
        """
        Register a new model version.

        Args:
            model_name: Model name ("lightgbm", "xgboost", "random_forest")
            version: Version string (e.g., "v1", "v2")
            performance: Performance metrics dict
            metadata: Optional additional metadata
            environment: Target environment ("staging", "production")

        Returns:
            bool: True if successful
        """
        try:
            if model_name not in self.registry["models"]:
                self.registry["models"][model_name] = {
                    "versions": {},
                    "production": None,
                    "staging": None,
                    "history": []
                }

            # Register version
            version_info = {
                "version": version,
                "registered_at": datetime.utcnow().isoformat(),
                "performance": performance,
                "metadata": metadata or {},
                "environment": environment,
                "deployed_at": None,
                "promoted_from": None,
                "deprecated": False
            }

            self.registry["models"][model_name]["versions"][version] = version_info

            # Set staging/production pointer
            if environment == "staging":
                self.registry["models"][model_name]["staging"] = version
            elif environment == "production":
                self.registry["models"][model_name]["production"] = version
                version_info["deployed_at"] = datetime.utcnow().isoformat()

            # Add to history
            self.registry["models"][model_name]["history"].append({
                "timestamp": datetime.utcnow().isoformat(),
                "action": "register",
                "version": version,
                "environment": environment
            })

            self._save_registry()

            logger.info(
                f"✓ Registered {model_name} {version} in {environment} "
                f"(F1={performance.get('f1_score', 0):.4f})"
            )
            return True

        except Exception as e:
            logger.error(f"Error registering model: {e}")
            return False

    def promote_to_production(
        self,
        model_name: str,
        version: str,
        backup_current: bool = True
    ) -> bool:
        """
        Promote a model version to production.

        Args:
            model_name: Model name
            version: Version to promote
            backup_current: Whether to backup current production model

        Returns:
            bool: True if successful
        """
        try:
            if model_name not in self.registry["models"]:
                logger.error(f"Model {model_name} not found in registry")
                return False

            if version not in self.registry["models"][model_name]["versions"]:
                logger.error(f"Version {version} not found for {model_name}")
                return False

            # Get current production version
            current_prod = self.registry["models"][model_name].get("production")

            # Backup current production model
            if backup_current and current_prod:
                self._archive_model(model_name, current_prod)

            # Promote to production
            self.registry["models"][model_name]["production"] = version
            self.registry["models"][model_name]["versions"][version]["environment"] = "production"
            self.registry["models"][model_name]["versions"][version]["deployed_at"] = datetime.utcnow().isoformat()
            self.registry["models"][model_name]["versions"][version]["promoted_from"] = current_prod

            # Add to history
            self.registry["models"][model_name]["history"].append({
                "timestamp": datetime.utcnow().isoformat(),
                "action": "promote",
                "version": version,
                "previous_version": current_prod,
                "environment": "production"
            })

            self._save_registry()

            logger.info(f"✓ Promoted {model_name} {version} to production (was: {current_prod})")
            return True

        except Exception as e:
            logger.error(f"Error promoting model: {e}")
            return False

    def rollback_to_version(
        self,
        model_name: str,
        target_version: str
    ) -> bool:
        """
        Rollback to a previous model version.

        Args:
            model_name: Model name
            target_version: Version to rollback to

        Returns:
            bool: True if successful
        """
        try:
            if model_name not in self.registry["models"]:
                logger.error(f"Model {model_name} not found in registry")
                return False

            if target_version not in self.registry["models"][model_name]["versions"]:
                logger.error(f"Version {target_version} not found for {model_name}")
                return False

            current_version = self.registry["models"][model_name].get("production")

            # Archive current version
            if current_version:
                self._archive_model(model_name, current_version)

            # Restore target version from archive if needed
            self._restore_model(model_name, target_version)

            # Update registry
            self.registry["models"][model_name]["production"] = target_version
            self.registry["models"][model_name]["versions"][target_version]["environment"] = "production"
            self.registry["models"][model_name]["versions"][target_version]["deployed_at"] = datetime.utcnow().isoformat()

            # Add to history
            self.registry["models"][model_name]["history"].append({
                "timestamp": datetime.utcnow().isoformat(),
                "action": "rollback",
                "version": target_version,
                "previous_version": current_version,
                "environment": "production"
            })

            self._save_registry()

            logger.info(f"✓ Rolled back {model_name} to {target_version} (was: {current_version})")
            return True

        except Exception as e:
            logger.error(f"Error rolling back model: {e}")
            return False

    def _archive_model(self, model_name: str, version: str):
        """
        Archive a model version.

        Args:
            model_name: Model name
            version: Version to archive
        """
        try:
            # Create archive directory for this model
            model_archive_dir = ARCHIVE_DIR / model_name
            model_archive_dir.mkdir(parents=True, exist_ok=True)

            # Determine file extension based on model type
            if model_name == "lightgbm":
                ext = ".txt"
            elif model_name == "xgboost":
                ext = ".json"
            else:
                ext = ".pkl"

            # Archive model file
            model_file = MODELS_DIR / f"{model_name}_{version}{ext}"
            if model_file.exists():
                archive_file = model_archive_dir / f"{model_name}_{version}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}{ext}"
                shutil.copy2(model_file, archive_file)
                logger.info(f"✓ Archived {model_file.name} to {archive_file}")

            # Archive metadata
            metadata_file = MODELS_DIR / f"{model_name}_{version}_metadata.json"
            if metadata_file.exists():
                archive_metadata = model_archive_dir / f"{model_name}_{version}_metadata_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
                shutil.copy2(metadata_file, archive_metadata)

            # Archive feature engineer
            fe_file = MODELS_DIR / f"feature_engineer_{version}.pkl"
            if fe_file.exists():
                archive_fe = model_archive_dir / f"feature_engineer_{version}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pkl"
                shutil.copy2(fe_file, archive_fe)

        except Exception as e:
            logger.error(f"Error archiving model: {e}")

    def _restore_model(self, model_name: str, version: str):
        """
        Restore a model version from archive.

        Args:
            model_name: Model name
            version: Version to restore
        """
        try:
            # Check if model is already in models directory
            if model_name == "lightgbm":
                ext = ".txt"
            elif model_name == "xgboost":
                ext = ".json"
            else:
                ext = ".pkl"

            model_file = MODELS_DIR / f"{model_name}_{version}{ext}"

            if model_file.exists():
                logger.info(f"Model {model_name} {version} already exists in models directory")
                return

            # Look for archived version
            model_archive_dir = ARCHIVE_DIR / model_name
            if not model_archive_dir.exists():
                logger.warning(f"No archive found for {model_name}")
                return

            # Find latest archived version
            archived_models = sorted(model_archive_dir.glob(f"{model_name}_{version}_*{ext}"))
            if archived_models:
                latest_archive = archived_models[-1]
                shutil.copy2(latest_archive, model_file)
                logger.info(f"✓ Restored {model_file.name} from archive")
            else:
                logger.warning(f"No archived model found for {model_name} {version}")

        except Exception as e:
            logger.error(f"Error restoring model: {e}")

    def get_model_info(self, model_name: str) -> Optional[Dict]:
        """
        Get information about a model.

        Args:
            model_name: Model name

        Returns:
            Dict with model info or None
        """
        if model_name not in self.registry["models"]:
            return None

        return self.registry["models"][model_name]

    def get_production_version(self, model_name: str) -> Optional[str]:
        """
        Get current production version.

        Args:
            model_name: Model name

        Returns:
            Version string or None
        """
        if model_name in self.registry["models"]:
            return self.registry["models"][model_name].get("production")
        return None

    def list_all_versions(self, model_name: str) -> List[Dict]:
        """
        List all versions of a model.

        Args:
            model_name: Model name

        Returns:
            List of version info dicts
        """
        if model_name not in self.registry["models"]:
            return []

        versions = []
        for version, info in self.registry["models"][model_name]["versions"].items():
            versions.append({
                "version": version,
                "environment": info.get("environment"),
                "f1_score": info.get("performance", {}).get("f1_score"),
                "registered_at": info.get("registered_at"),
                "deployed_at": info.get("deployed_at"),
                "deprecated": info.get("deprecated", False)
            })

        # Sort by registration date (newest first)
        versions.sort(key=lambda x: x["registered_at"], reverse=True)

        return versions

    def deprecate_version(self, model_name: str, version: str) -> bool:
        """
        Mark a version as deprecated.

        Args:
            model_name: Model name
            version: Version to deprecate

        Returns:
            bool: True if successful
        """
        try:
            if model_name in self.registry["models"]:
                if version in self.registry["models"][model_name]["versions"]:
                    self.registry["models"][model_name]["versions"][version]["deprecated"] = True
                    self._save_registry()
                    logger.info(f"✓ Deprecated {model_name} {version}")
                    return True
            return False
        except Exception as e:
            logger.error(f"Error deprecating version: {e}")
            return False


# Singleton instance
_model_registry = None


def get_model_registry() -> ModelRegistry:
    """Get singleton instance of ModelRegistry."""
    global _model_registry
    if _model_registry is None:
        _model_registry = ModelRegistry()
    return _model_registry
