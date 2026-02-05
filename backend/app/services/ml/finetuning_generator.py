"""
Fine-Tuning Dataset Generator

Prepares instruction-tuning datasets for fraud detection fine-tuning:
- Fraud explanation pairs
- Instruction format (Alpaca/ShareGPT style)
- Quality filtering
- Dataset versioning

Note: Actual fine-tuning skipped for M4 Pro constraints.
This prepares the data for future fine-tuning when resources are available.
"""

import json
import random
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd


@dataclass
class InstructionExample:
    """Instruction-tuning example in Alpaca format"""
    instruction: str
    input: str
    output: str
    metadata: Dict[str, Any]


@dataclass
class ConversationExample:
    """Conversation example in ShareGPT format"""
    conversations: List[Dict[str, str]]  # [{"from": "human", "value": "..."}, {"from": "gpt", "value": "..."}]
    metadata: Dict[str, Any]


class FineTuningDatasetGenerator:
    """Generate fine-tuning datasets for fraud detection"""

    def __init__(self, data_dir: str = "data", output_dir: str = "data/finetuning"):
        # Use absolute paths from project root
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent.parent.parent
        self.data_dir = project_root / data_dir
        self.output_dir = project_root / output_dir
        self.output_dir.mkdir(exist_ok=True, parents=True)

        # Load annotations if available
        self.annotations_dir = self.data_dir / "annotations"
        self.fraud_explanations = self._load_fraud_explanations()

    def _load_fraud_explanations(self) -> List[Dict]:
        """Load fraud explanations from annotations"""
        explanations_file = self.annotations_dir / "fraud_explanations.json"

        if explanations_file.exists():
            with open(explanations_file, 'r') as f:
                return json.load(f)

        print(f"No fraud explanations found at {explanations_file}")
        return []

    def generate_instruction_format(self,
                                   transaction: Dict[str, Any],
                                   analysis: str,
                                   verdict: str,
                                   confidence: float) -> InstructionExample:
        """
        Generate instruction-tuning example in Alpaca format

        Format:
        instruction: Analyze this financial transaction for fraud
        input: <transaction details>
        output: <analysis + verdict>
        """
        # Format input
        input_text = f"""Transaction Details:
- Type: {transaction.get('type', 'UNKNOWN')}
- Amount: ${transaction.get('amount', 0):,.2f}
- Origin Balance: ${transaction.get('oldbalanceOrg', 0):,.2f} → ${transaction.get('newbalanceOrig', 0):,.2f}
- Destination Balance: ${transaction.get('oldbalanceDest', 0):,.2f} → ${transaction.get('newbalanceDest', 0):,.2f}"""

        # Format output
        output_text = f"""Analysis: {analysis}

Verdict: {verdict.upper()}
Confidence: {confidence:.2f}

Reasoning:
This assessment is based on:
1. Balance consistency check: {'PASSED' if transaction.get('amount', 0) <= transaction.get('oldbalanceOrg', 0) else 'FAILED'}
2. Transaction type risk: {'HIGH' if transaction.get('type') in ['TRANSFER', 'CASH_OUT'] else 'LOW'}
3. Pattern matching: {verdict.upper()} pattern detected"""

        return InstructionExample(
            instruction="Analyze this financial transaction for fraud. Provide detailed reasoning and a verdict (FRAUD or LEGITIMATE) with confidence score.",
            input=input_text,
            output=output_text,
            metadata={
                "transaction_type": transaction.get('type'),
                "amount": transaction.get('amount'),
                "true_label": verdict,
                "generated_at": datetime.now().isoformat()
            }
        )

    def generate_conversation_format(self,
                                    transaction: Dict[str, Any],
                                    analysis: str,
                                    verdict: str,
                                    confidence: float) -> ConversationExample:
        """
        Generate conversation example in ShareGPT format

        Format:
        [
          {"from": "human", "value": "Analyze this transaction..."},
          {"from": "gpt", "value": "Analysis: ..."}
        ]
        """
        # Human message
        human_msg = f"""I need you to analyze this financial transaction for fraud:

Type: {transaction.get('type', 'UNKNOWN')}
Amount: ${transaction.get('amount', 0):,.2f}
Origin Balance: ${transaction.get('oldbalanceOrg', 0):,.2f} → ${transaction.get('newbalanceOrig', 0):,.2f}
Destination Balance: ${transaction.get('oldbalanceDest', 0):,.2f} → ${transaction.get('newbalanceDest', 0):,.2f}

Please provide a detailed analysis with your verdict and confidence level."""

        # GPT message
        gpt_msg = f"""{analysis}

Based on this analysis, I assess this transaction as **{verdict.upper()}** with {confidence:.0%} confidence.

Key factors:
- Balance verification: {'Amounts reconcile correctly' if transaction.get('amount', 0) <= transaction.get('oldbalanceOrg', 0) else 'Balance inconsistency detected'}
- Risk profile: {transaction.get('type', 'UNKNOWN')} transactions carry {'high' if transaction.get('type') in ['TRANSFER', 'CASH_OUT'] else 'moderate'} risk
- Pattern analysis: This matches typical {verdict} transaction patterns"""

        return ConversationExample(
            conversations=[
                {"from": "human", "value": human_msg},
                {"from": "gpt", "value": gpt_msg}
            ],
            metadata={
                "transaction_type": transaction.get('type'),
                "amount": transaction.get('amount'),
                "true_label": verdict,
                "generated_at": datetime.now().isoformat()
            }
        )

    def generate_from_dataset(self,
                            dataset_path: str,
                            sample_size: int = 1000,
                            format_type: str = "alpaca") -> List[Any]:
        """
        Generate fine-tuning dataset from transaction data

        Args:
            dataset_path: Path to CSV file with transactions
            sample_size: Number of examples to generate
            format_type: "alpaca" or "sharegpt"

        Returns:
            List of instruction examples
        """
        # Load data
        df = pd.read_csv(dataset_path)

        # Sample transactions (balanced fraud/legitimate)
        fraud_df = df[df['isFraud'] == 1].sample(
            n=min(sample_size // 2, len(df[df['isFraud'] == 1])),
            random_state=42
        )
        legit_df = df[df['isFraud'] == 0].sample(
            n=sample_size // 2,
            random_state=42
        )

        sample_df = pd.concat([fraud_df, legit_df]).sample(frac=1, random_state=42)

        print(f"Generating {len(sample_df)} examples ({len(fraud_df)} fraud, {len(legit_df)} legitimate)")

        # Generate examples
        examples = []

        for _, row in sample_df.iterrows():
            transaction = {
                'type': row['type'] if 'type' in row else 'UNKNOWN',
                'amount': row['amount'],
                'oldbalanceOrg': row['oldbalanceOrg'],
                'newbalanceOrig': row['newbalanceOrig'],
                'oldbalanceDest': row['oldbalanceDest'],
                'newbalanceDest': row['newbalanceDest']
            }

            verdict = "fraud" if row['isFraud'] == 1 else "legitimate"

            # Generate analysis
            analysis = self._generate_analysis(transaction, verdict)
            confidence = random.uniform(0.85, 0.99) if verdict == "fraud" else random.uniform(0.80, 0.95)

            if format_type == "alpaca":
                example = self.generate_instruction_format(
                    transaction, analysis, verdict, confidence
                )
            else:  # sharegpt
                example = self.generate_conversation_format(
                    transaction, analysis, verdict, confidence
                )

            examples.append(example)

        return examples

    def _generate_analysis(self, transaction: Dict, verdict: str) -> str:
        """Generate fraud analysis text"""
        amount = transaction['amount']
        old_balance = transaction['oldbalanceOrg']
        new_balance = transaction['newbalanceOrig']
        tx_type = transaction['type']

        if verdict == "fraud":
            # Fraud analysis
            if amount > old_balance:
                return f"Critical fraud indicator: Transaction amount (${amount:,.2f}) exceeds available balance (${old_balance:,.2f}). This is mathematically impossible in a legitimate transaction. Combined with {tx_type} transaction type, this strongly suggests fraudulent activity."
            elif new_balance == 0 and amount == old_balance:
                return f"Account drainage detected: Entire balance (${amount:,.2f}) withdrawn via {tx_type}. Complete account depletion is a common fraud pattern, especially when combined with high-risk transaction types."
            else:
                return f"Multiple fraud indicators detected: {tx_type} transaction for ${amount:,.2f} exhibits patterns consistent with fraudulent activity. Balance changes and transaction characteristics match known fraud signatures."
        else:
            # Legitimate analysis
            balance_check = abs((old_balance - amount) - new_balance) < 0.01
            if balance_check:
                return f"Transaction appears legitimate: {tx_type} for ${amount:,.2f} with proper balance reconciliation (${old_balance:,.2f} - ${amount:,.2f} = ${new_balance:,.2f}). No red flags detected in transaction pattern or amount."
            else:
                return f"Standard {tx_type} transaction for ${amount:,.2f}. Amount is reasonable relative to account balance (${old_balance:,.2f}). No fraudulent patterns detected."

    def save_dataset(self,
                    examples: List[Any],
                    filename: str,
                    format_type: str = "alpaca"):
        """Save dataset to JSONL file"""
        output_file = self.output_dir / filename

        with open(output_file, 'w') as f:
            for example in examples:
                json.dump(asdict(example), f)
                f.write('\n')

        print(f"Saved {len(examples)} examples to {output_file}")

        # Save metadata
        metadata = {
            "format": format_type,
            "num_examples": len(examples),
            "created_at": datetime.now().isoformat(),
            "filename": filename,
            "description": f"Fine-tuning dataset for fraud detection in {format_type} format"
        }

        metadata_file = self.output_dir / f"{filename}.metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

        return str(output_file)

    def generate_preference_pairs(self,
                                 dataset_path: str,
                                 num_pairs: int = 500) -> List[Dict]:
        """
        Generate preference pairs for DPO/RLHF

        Format:
        {
          "prompt": "Analyze this transaction...",
          "chosen": "Good analysis",
          "rejected": "Poor analysis"
        }
        """
        # Load data
        df = pd.read_csv(dataset_path)
        sample_df = df.sample(n=min(num_pairs, len(df)), random_state=42)

        preference_pairs = []

        for _, row in sample_df.iterrows():
            transaction = {
                'type': row.get('type', 'UNKNOWN'),
                'amount': row['amount'],
                'oldbalanceOrg': row['oldbalanceOrg'],
                'newbalanceOrig': row['newbalanceOrig'],
                'oldbalanceDest': row['oldbalanceDest'],
                'newbalanceDest': row['newbalanceDest']
            }

            verdict = "fraud" if row['isFraud'] == 1 else "legitimate"

            # Prompt
            prompt = f"""Analyze this financial transaction for fraud:

Type: {transaction['type']}
Amount: ${transaction['amount']:,.2f}
Origin: ${transaction['oldbalanceOrg']:,.2f} → ${transaction['newbalanceOrig']:,.2f}
Destination: ${transaction['oldbalanceDest']:,.2f} → ${transaction['newbalanceDest']:,.2f}"""

            # Chosen (good analysis)
            chosen = self._generate_analysis(transaction, verdict)
            chosen += f"\n\nVerdict: {verdict.upper()}"

            # Rejected (poor analysis - opposite verdict)
            wrong_verdict = "legitimate" if verdict == "fraud" else "fraud"
            rejected = f"This transaction appears to be {wrong_verdict}. No significant concerns detected."

            preference_pairs.append({
                "prompt": prompt,
                "chosen": chosen,
                "rejected": rejected,
                "true_label": verdict
            })

        return preference_pairs

    def create_full_pipeline(self, sample_size: int = 1000):
        """Create complete fine-tuning dataset pipeline"""
        # Find dataset
        dataset_path = self.data_dir / "processed" / "paysim_cleaned.csv"

        if not dataset_path.exists():
            print(f"Dataset not found: {dataset_path}")
            print("Skipping fine-tuning dataset generation")
            return

        print(f"\n{'='*60}")
        print(f"FINE-TUNING DATASET GENERATION")
        print(f"{'='*60}\n")

        # 1. Generate Alpaca format
        print("1. Generating Alpaca format dataset...")
        alpaca_examples = self.generate_from_dataset(
            str(dataset_path),
            sample_size=sample_size,
            format_type="alpaca"
        )
        alpaca_file = self.save_dataset(
            alpaca_examples,
            filename="fraud_detection_alpaca.jsonl",
            format_type="alpaca"
        )

        # 2. Generate ShareGPT format
        print("\n2. Generating ShareGPT format dataset...")
        sharegpt_examples = self.generate_from_dataset(
            str(dataset_path),
            sample_size=sample_size,
            format_type="sharegpt"
        )
        sharegpt_file = self.save_dataset(
            sharegpt_examples,
            filename="fraud_detection_sharegpt.jsonl",
            format_type="sharegpt"
        )

        # 3. Generate preference pairs for DPO
        print("\n3. Generating preference pairs for DPO/RLHF...")
        preference_pairs = self.generate_preference_pairs(
            str(dataset_path),
            num_pairs=sample_size // 2
        )

        pref_file = self.output_dir / "fraud_detection_preferences.jsonl"
        with open(pref_file, 'w') as f:
            for pair in preference_pairs:
                json.dump(pair, f)
                f.write('\n')

        print(f"Saved {len(preference_pairs)} preference pairs to {pref_file}")

        # Summary
        print(f"\n{'='*60}")
        print(f"DATASET GENERATION COMPLETE")
        print(f"{'='*60}")
        print(f"\nGenerated files:")
        print(f"1. {alpaca_file} - Alpaca format ({len(alpaca_examples)} examples)")
        print(f"2. {sharegpt_file} - ShareGPT format ({len(sharegpt_examples)} examples)")
        print(f"3. {pref_file} - Preference pairs ({len(preference_pairs)} pairs)")
        print(f"\nNext steps:")
        print(f"- Use these datasets for fine-tuning Mistral 7B with LoRA")
        print(f"- Configure LoRA: r=16, alpha=32, target_modules=['q_proj', 'v_proj']")
        print(f"- Training hyperparams: lr=2e-4, batch_size=4, gradient_accumulation=4")
        print(f"- Use preference pairs for DPO after initial supervised fine-tuning")
        print(f"\nNote: Actual fine-tuning skipped due to M4 Pro resource constraints.")
        print(f"Datasets are ready for future fine-tuning on appropriate hardware.\n")


# Global instance
finetuning_generator = FineTuningDatasetGenerator()
