"""Vectorize and populate ChromaDB for fraud detection inference.

This script:
1. Loads processed fraud data
2. Creates embeddings for transactions
3. Populates ChromaDB collections for RAG:
   - fraud_cases: Known fraud examples
   - fraud_policies: Detection rules from markdown files
   - transaction_patterns: Behavioral patterns

Usage:
    python scripts/vectorize_data.py

Author: FinSight AI Team
Date: January 5, 2026
"""

import json
import logging
from pathlib import Path
from typing import Dict, List

import chromadb
import pandas as pd
from chromadb.config import Settings as ChromaSettings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class DataVectorizer:
    """Vectorize and populate ChromaDB for fraud detection."""

    def __init__(
        self,
        chroma_host: str = "localhost",
        chroma_port: int = 8001,
        persist_directory: str = "./data/chromadb",
    ):
        """Initialize vectorizer.

        Args:
            chroma_host: ChromaDB host
            chroma_port: ChromaDB port
            persist_directory: Local persist directory for ChromaDB
        """
        self.chroma_host = chroma_host
        self.chroma_port = chroma_port
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB client
        self.client = self._init_chroma_client()

        logger.info(
            f"DataVectorizer initialized with ChromaDB at {chroma_host}:{chroma_port}"
        )

    def _init_chroma_client(self) -> chromadb.Client:
        """Initialize ChromaDB client.

        Returns:
            ChromaDB client instance

        Raises:
            ConnectionError: If cannot connect to ChromaDB
        """
        try:
            # Try HTTP client first (for Docker Compose setup)
            client = chromadb.HttpClient(
                host=self.chroma_host,
                port=self.chroma_port,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            # Test connection
            client.heartbeat()
            logger.info(f"✓ Connected to ChromaDB at {self.chroma_host}:{self.chroma_port}")
            return client
        except Exception as e:
            logger.warning(f"HTTP client failed: {e}")
            logger.info("Attempting persistent client for local development...")
            try:
                # Fallback to persistent client (local development)
                client = chromadb.PersistentClient(
                    path=str(self.persist_directory),
                    settings=ChromaSettings(anonymized_telemetry=False),
                )
                logger.info(f"✓ Using persistent ChromaDB at {self.persist_directory}")
                return client
            except Exception as e2:
                raise ConnectionError(
                    f"Failed to connect to ChromaDB: HTTP={e}, Persistent={e2}"
                )

    def create_collections(self):
        """Create or reset ChromaDB collections."""
        logger.info("Creating/resetting ChromaDB collections...")

        collections = [
            ("fraud_cases", "Known fraud transaction examples for RAG"),
            ("fraud_policies", "Fraud detection rules and policies"),
            ("fraud_explanations", "LLM-generated fraud explanations"),
            ("transaction_patterns", "Behavioral patterns and statistics"),
        ]

        for name, description in collections:
            try:
                # Delete if exists
                try:
                    self.client.delete_collection(name)
                    logger.info(f"  Deleted existing collection: {name}")
                except Exception:
                    pass

                # Create new collection
                self.client.create_collection(
                    name=name,
                    metadata={"description": description},
                )
                logger.info(f"  ✓ Created collection: {name}")
            except Exception as e:
                logger.error(f"  ✗ Failed to create {name}: {e}")

    def vectorize_fraud_cases(self, data_path: str, limit: int = 500):
        """Vectorize known fraud cases for RAG.

        Args:
            data_path: Path to cleaned data CSV
            limit: Maximum number of fraud cases to vectorize
        """
        logger.info(f"Vectorizing fraud cases from {data_path}...")

        # Load data
        df = pd.read_csv(data_path)
        fraud_df = df[df["isFraud"] == 1].head(limit)
        logger.info(f"Found {len(fraud_df)} fraud cases to vectorize")

        # Get collection
        collection = self.client.get_collection("fraud_cases")

        # Prepare documents
        documents = []
        metadatas = []
        ids = []

        for idx, row in fraud_df.iterrows():
            # Create document text (what gets embedded)
            doc_text = (
                f"Transaction Type: {row['type']}, "
                f"Amount: ${row['amount']:.2f}, "
                f"Old Balance Origin: ${row['oldbalanceOrg']:.2f}, "
                f"New Balance Origin: ${row['newbalanceOrig']:.2f}, "
                f"Old Balance Destination: ${row['oldbalanceDest']:.2f}, "
                f"New Balance Destination: ${row['newbalanceDest']:.2f}, "
                f"Hour: {row.get('hour', 'N/A')}, "
                f"Day: {row.get('day', 'N/A')}, "
                f"Is High Value: {row.get('is_high_value', False)}, "
                f"Zero Balance Origin: {row.get('zero_balance_orig', False)}, "
                f"Zero Balance Destination: {row.get('zero_balance_dest', False)}"
            )

            # Metadata (filterable attributes)
            metadata = {
                "transaction_id": f"TXN_{idx}",
                "type": row["type"],
                "amount": float(row["amount"]),
                "isFraud": int(row["isFraud"]),
                "isFlaggedFraud": int(row["isFlaggedFraud"]),
                "step": int(row["step"]),
                "is_high_value": bool(row.get("is_high_value", False)),
            }

            documents.append(doc_text)
            metadatas.append(metadata)
            ids.append(f"fraud_case_{idx}")

        # Add to collection in batches
        batch_size = 100
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i : i + batch_size]
            batch_meta = metadatas[i : i + batch_size]
            batch_ids = ids[i : i + batch_size]

            collection.add(documents=batch_docs, metadatas=batch_meta, ids=batch_ids)
            logger.info(
                f"  Added batch {i // batch_size + 1}/{(len(documents) - 1) // batch_size + 1}"
            )

        logger.info(f"✓ Vectorized {len(documents)} fraud cases")

    def vectorize_fraud_policies(self, policies_dir: str):
        """Vectorize fraud detection policies from markdown files.

        Args:
            policies_dir: Path to fraud policies directory
        """
        logger.info(f"Vectorizing fraud policies from {policies_dir}...")

        policies_path = Path(policies_dir)
        if not policies_path.exists():
            logger.warning(f"Policies directory not found: {policies_dir}")
            return

        # Get collection
        collection = self.client.get_collection("fraud_policies")

        # Load all policy markdown files
        policy_files = list(policies_path.glob("*.md"))
        logger.info(f"Found {len(policy_files)} policy files")

        documents = []
        metadatas = []
        ids = []

        for policy_file in policy_files:
            policy_name = policy_file.stem
            policy_content = policy_file.read_text()

            # Extract sections if available
            sections = policy_content.split("\n## ")

            for idx, section in enumerate(sections):
                if not section.strip():
                    continue

                # Add document
                documents.append(section)
                metadatas.append(
                    {
                        "policy_name": policy_name,
                        "section_index": idx,
                        "source_file": str(policy_file.name),
                    }
                )
                ids.append(f"policy_{policy_name}_{idx}")

        # Add to collection
        if documents:
            collection.add(documents=documents, metadatas=metadatas, ids=ids)
            logger.info(f"✓ Vectorized {len(documents)} policy sections")
        else:
            logger.warning("No policy documents to vectorize")

    def vectorize_fraud_explanations(self, explanations_path: str):
        """Vectorize LLM-generated fraud explanations.

        Args:
            explanations_path: Path to fraud explanations JSON
        """
        logger.info(f"Vectorizing fraud explanations from {explanations_path}...")

        exp_file = Path(explanations_path)
        if not exp_file.exists():
            logger.warning(f"Explanations file not found: {explanations_path}")
            return

        # Load explanations
        with open(exp_file, "r") as f:
            explanations = json.load(f)

        logger.info(f"Loaded {len(explanations)} explanations")

        # Get collection
        collection = self.client.get_collection("fraud_explanations")

        documents = []
        metadatas = []
        ids = []

        for exp in explanations:
            # Create document from explanation
            doc_text = (
                f"Transaction {exp['transaction_id']}: "
                f"{exp['explanation']} "
                f"Reason: {exp['fraud_reason_code']} "
                f"Decision: {exp['decision']}"
            )

            metadata = {
                "transaction_id": exp["transaction_id"],
                "type": exp["type"],
                "amount": float(exp["amount"]),
                "fraud_reason_code": exp["fraud_reason_code"],
                "decision": exp["decision"],
                "confidence": float(exp["confidence"]),
            }

            documents.append(doc_text)
            metadatas.append(metadata)
            ids.append(f"explanation_{exp['transaction_id']}")

        # Add to collection
        if documents:
            collection.add(documents=documents, metadatas=metadatas, ids=ids)
            logger.info(f"✓ Vectorized {len(documents)} fraud explanations")

    def create_transaction_patterns(self, data_path: str):
        """Create and vectorize transaction patterns and statistics.

        Args:
            data_path: Path to cleaned data CSV
        """
        logger.info(f"Creating transaction patterns from {data_path}...")

        # Load data
        df = pd.read_csv(data_path)

        # Get collection
        collection = self.client.get_collection("transaction_patterns")

        documents = []
        metadatas = []
        ids = []

        # Pattern 1: Fraud rate by transaction type
        fraud_by_type = (
            df.groupby("type")
            .agg(
                total=("isFraud", "count"),
                fraud_count=("isFraud", "sum"),
                avg_amount=("amount", "mean"),
            )
            .reset_index()
        )
        fraud_by_type["fraud_rate"] = (
            fraud_by_type["fraud_count"] / fraud_by_type["total"]
        )

        for _, row in fraud_by_type.iterrows():
            doc_text = (
                f"Transaction type {row['type']} has {row['fraud_count']} fraud cases "
                f"out of {row['total']} total transactions ({row['fraud_rate']:.4%} fraud rate). "
                f"Average amount: ${row['avg_amount']:.2f}"
            )
            documents.append(doc_text)
            metadatas.append(
                {
                    "pattern_type": "fraud_by_transaction_type",
                    "transaction_type": row["type"],
                    "fraud_rate": float(row["fraud_rate"]),
                    "total_transactions": int(row["total"]),
                }
            )
            ids.append(f"pattern_type_{row['type']}")

        # Pattern 2: High-value transaction fraud
        high_value_threshold = df["amount"].quantile(0.9)
        high_value_df = df[df["amount"] >= high_value_threshold]
        high_value_fraud_rate = high_value_df["isFraud"].mean()

        doc_text = (
            f"High-value transactions (≥${high_value_threshold:.2f}) have a "
            f"{high_value_fraud_rate:.4%} fraud rate, compared to "
            f"{df['isFraud'].mean():.4%} overall."
        )
        documents.append(doc_text)
        metadatas.append(
            {
                "pattern_type": "high_value_fraud",
                "threshold": float(high_value_threshold),
                "fraud_rate": float(high_value_fraud_rate),
            }
        )
        ids.append("pattern_high_value")

        # Pattern 3: Zero balance patterns
        if "zero_balance_orig" in df.columns:
            zero_balance_df = df[df["zero_balance_orig"] == 1]
            zero_balance_fraud_rate = zero_balance_df["isFraud"].mean()

            doc_text = (
                f"Transactions that drain the origin account to zero have a "
                f"{zero_balance_fraud_rate:.4%} fraud rate."
            )
            documents.append(doc_text)
            metadatas.append(
                {
                    "pattern_type": "zero_balance_fraud",
                    "fraud_rate": float(zero_balance_fraud_rate),
                }
            )
            ids.append("pattern_zero_balance")

        # Add to collection
        if documents:
            collection.add(documents=documents, metadatas=metadatas, ids=ids)
            logger.info(f"✓ Created {len(documents)} transaction patterns")

    def verify_collections(self):
        """Verify that all collections were populated successfully."""
        logger.info("\n" + "=" * 80)
        logger.info("VERIFYING CHROMADB COLLECTIONS")
        logger.info("=" * 80)

        collections = [
            "fraud_cases",
            "fraud_policies",
            "fraud_explanations",
            "transaction_patterns",
        ]

        for name in collections:
            try:
                collection = self.client.get_collection(name)
                count = collection.count()
                logger.info(f"✓ {name}: {count} documents")

                # Test query
                if count > 0:
                    results = collection.query(
                        query_texts=["fraud transaction"], n_results=1
                    )
                    logger.info(f"  Sample query returned {len(results['ids'][0])} results")
            except Exception as e:
                logger.error(f"✗ {name}: Error - {e}")

    def run_vectorization(self):
        """Run complete vectorization pipeline."""
        logger.info("\n" + "=" * 80)
        logger.info("STARTING DATA VECTORIZATION PIPELINE")
        logger.info("=" * 80)

        # Setup paths
        project_root = Path(__file__).parent.parent.parent
        data_dir = project_root / "data"

        # Create collections
        self.create_collections()

        # Vectorize fraud cases
        fraud_data_path = data_dir / "processed" / "paysim_cleaned.csv"
        if fraud_data_path.exists():
            self.vectorize_fraud_cases(str(fraud_data_path), limit=500)
        else:
            logger.warning(f"Cleaned data not found: {fraud_data_path}")

        # Vectorize policies
        policies_dir = data_dir / "fraud_policies"
        if policies_dir.exists():
            self.vectorize_fraud_policies(str(policies_dir))
        else:
            logger.warning(f"Policies directory not found: {policies_dir}")

        # Vectorize explanations
        explanations_path = data_dir / "annotations" / "fraud_explanations.json"
        if explanations_path.exists():
            self.vectorize_fraud_explanations(str(explanations_path))
        else:
            logger.warning(f"Explanations not found: {explanations_path}")

        # Create transaction patterns
        if fraud_data_path.exists():
            self.create_transaction_patterns(str(fraud_data_path))

        # Verify
        self.verify_collections()

        logger.info("\n" + "=" * 80)
        logger.info("✓ DATA VECTORIZATION COMPLETED")
        logger.info("=" * 80)
        logger.info("\nChromaDB is now ready for fraud detection inference!")
        logger.info(f"Collections available at {self.chroma_host}:{self.chroma_port}")


def main():
    """Main entry point."""
    # Initialize vectorizer
    vectorizer = DataVectorizer(
        chroma_host="localhost",
        chroma_port=8001,
        persist_directory="./data/chromadb",
    )

    # Run vectorization
    vectorizer.run_vectorization()


if __name__ == "__main__":
    main()
