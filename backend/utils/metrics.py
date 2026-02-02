"""
Reusable Metrics and Evaluation Utilities for ML Models.

This module provides comprehensive metrics calculation, visualization,
and threshold optimization functions for fraud detection models.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, confusion_matrix,
    roc_curve, precision_recall_curve, matthews_corrcoef
)
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path


class ClassificationMetrics:
    """Calculate comprehensive classification metrics."""
    
    @staticmethod
    def calculate_all_metrics(
        y_true: np.ndarray,
        y_pred: np.ndarray,
        y_pred_proba: np.ndarray
    ) -> Dict[str, float]:
        """
        Calculate all classification metrics.
        
        Args:
            y_true: True labels (0/1)
            y_pred: Predicted labels (0/1)
            y_pred_proba: Predicted probabilities for class 1
            
        Returns:
            Dictionary of metrics
        """
        # Confusion matrix components
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
        
        # Basic metrics
        accuracy = accuracy_score(y_true, y_pred)
        precision = precision_score(y_true, y_pred, zero_division=0)
        recall = recall_score(y_true, y_pred, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)
        
        # Additional metrics
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
        fnr = fn / (fn + tp) if (fn + tp) > 0 else 0
        
        # ROC-AUC and PR-AUC
        try:
            roc_auc = roc_auc_score(y_true, y_pred_proba)
        except ValueError:
            roc_auc = 0.0
        
        try:
            pr_auc = average_precision_score(y_true, y_pred_proba)
        except ValueError:
            pr_auc = 0.0
        
        # Matthews Correlation Coefficient
        mcc = matthews_corrcoef(y_true, y_pred)
        
        return {
            # Basic metrics
            "accuracy": float(accuracy),
            "precision": float(precision),
            "recall": float(recall),
            "f1_score": float(f1),
            
            # Additional classification metrics
            "specificity": float(specificity),
            "false_positive_rate": float(fpr),
            "false_negative_rate": float(fnr),
            
            # AUC metrics
            "roc_auc": float(roc_auc),
            "pr_auc": float(pr_auc),
            
            # Correlation
            "mcc": float(mcc),
            
            # Confusion matrix
            "true_negatives": int(tn),
            "false_positives": int(fp),
            "false_negatives": int(fn),
            "true_positives": int(tp)
        }


class BusinessMetrics:
    """Calculate business-relevant metrics for fraud detection."""
    
    @staticmethod
    def calculate_expected_loss(
        y_true: np.ndarray,
        y_pred: np.ndarray,
        cost_fp: float = 5.0,
        cost_fn: float = 100.0
    ) -> Dict[str, float]:
        """
        Calculate expected loss based on costs of false positives and negatives.
        
        Args:
            y_true: True labels
            y_pred: Predicted labels
            cost_fp: Cost of false positive (manual review)
            cost_fn: Cost of false negative (fraud loss)
            
        Returns:
            Dictionary with loss metrics
        """
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
        
        total_fp_cost = fp * cost_fp
        total_fn_cost = fn * cost_fn
        total_cost = total_fp_cost + total_fn_cost
        
        # Cost per transaction
        n_transactions = len(y_true)
        cost_per_transaction = total_cost / n_transactions if n_transactions > 0 else 0
        
        return {
            "total_fp_cost": float(total_fp_cost),
            "total_fn_cost": float(total_fn_cost),
            "total_cost": float(total_cost),
            "cost_per_transaction": float(cost_per_transaction),
            "fp_count": int(fp),
            "fn_count": int(fn),
            "cost_fp": float(cost_fp),
            "cost_fn": float(cost_fn)
        }
    
    @staticmethod
    def precision_at_k(
        y_true: np.ndarray,
        y_pred_proba: np.ndarray,
        k: float = 0.01
    ) -> float:
        """
        Calculate precision at top k% of risky transactions.
        
        Args:
            y_true: True labels
            y_pred_proba: Predicted probabilities
            k: Percentage of top risky transactions (0.01 = 1%)
            
        Returns:
            Precision at k
        """
        n = len(y_true)
        n_top_k = max(1, int(n * k))
        
        # Get indices of top k% predictions
        top_k_indices = np.argsort(y_pred_proba)[::-1][:n_top_k]
        
        # Calculate precision on top k
        y_true_top_k = y_true[top_k_indices]
        precision_k = y_true_top_k.sum() / len(y_true_top_k) if len(y_true_top_k) > 0 else 0
        
        return float(precision_k)


class ThresholdOptimizer:
    """Optimize classification threshold based on different criteria."""
    
    @staticmethod
    def find_optimal_threshold_f1(
        y_true: np.ndarray,
        y_pred_proba: np.ndarray
    ) -> Tuple[float, float]:
        """
        Find threshold that maximizes F1-score.
        
        Args:
            y_true: True labels
            y_pred_proba: Predicted probabilities
            
        Returns:
            (optimal_threshold, best_f1_score)
        """
        precision, recall, thresholds = precision_recall_curve(y_true, y_pred_proba)
        
        # Calculate F1 for each threshold
        f1_scores = 2 * (precision * recall) / (precision + recall + 1e-10)
        
        # Find best threshold
        best_idx = np.argmax(f1_scores)
        best_threshold = thresholds[best_idx] if best_idx < len(thresholds) else 0.5
        best_f1 = f1_scores[best_idx]
        
        return float(best_threshold), float(best_f1)
    
    @staticmethod
    def find_optimal_threshold_cost(
        y_true: np.ndarray,
        y_pred_proba: np.ndarray,
        cost_fp: float = 5.0,
        cost_fn: float = 100.0
    ) -> Tuple[float, float]:
        """
        Find threshold that minimizes expected cost.
        
        Args:
            y_true: True labels
            y_pred_proba: Predicted probabilities
            cost_fp: Cost of false positive
            cost_fn: Cost of false negative
            
        Returns:
            (optimal_threshold, minimum_cost)
        """
        thresholds = np.linspace(0, 1, 100)
        costs = []
        
        for threshold in thresholds:
            y_pred = (y_pred_proba >= threshold).astype(int)
            tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
            
            total_cost = (fp * cost_fp) + (fn * cost_fn)
            costs.append(total_cost)
        
        best_idx = np.argmin(costs)
        best_threshold = thresholds[best_idx]
        min_cost = costs[best_idx]
        
        return float(best_threshold), float(min_cost)
    
    @staticmethod
    def define_risk_thresholds(
        y_true: np.ndarray,
        y_pred_proba: np.ndarray,
        target_recall: float = 0.95
    ) -> Dict[str, float]:
        """
        Define three-tier thresholds: Approve/Review/Block.
        
        Args:
            y_true: True labels
            y_pred_proba: Predicted probabilities
            target_recall: Target recall for high-risk threshold
            
        Returns:
            Dictionary with threshold levels
        """
        # Find threshold for target recall
        precision, recall, thresholds = precision_recall_curve(y_true, y_pred_proba)
        
        # High-risk threshold (Block): Achieve target recall
        high_idx = np.argmin(np.abs(recall - target_recall))
        high_threshold = thresholds[high_idx] if high_idx < len(thresholds) else 0.7
        
        # Low-risk threshold (Approve): Very high precision
        low_threshold = 0.3
        
        return {
            "approve_threshold": float(low_threshold),  # < 0.3: Auto-approve
            "review_threshold": float(high_threshold),  # 0.3-0.7: Manual review
            "block_threshold": float(high_threshold),   # > 0.7: Auto-block
            "target_recall": float(target_recall)
        }


class MetricsVisualizer:
    """Visualization utilities for model evaluation."""
    
    @staticmethod
    def plot_confusion_matrix(
        y_true: np.ndarray,
        y_pred: np.ndarray,
        save_path: Optional[Path] = None,
        normalize: bool = False
    ) -> plt.Figure:
        """
        Plot confusion matrix as heatmap.
        
        Args:
            y_true: True labels
            y_pred: Predicted labels
            save_path: Path to save figure
            normalize: Whether to normalize values
            
        Returns:
            Matplotlib figure
        """
        cm = confusion_matrix(y_true, y_pred)
        
        if normalize:
            cm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
            fmt = '.2%'
            title = 'Normalized Confusion Matrix'
        else:
            fmt = 'd'
            title = 'Confusion Matrix'
        
        fig, ax = plt.subplots(figsize=(8, 6))
        sns.heatmap(
            cm, annot=True, fmt=fmt, cmap='Blues',
            xticklabels=['Legitimate', 'Fraud'],
            yticklabels=['Legitimate', 'Fraud'],
            ax=ax
        )
        ax.set_ylabel('True Label')
        ax.set_xlabel('Predicted Label')
        ax.set_title(title)
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            plt.close()
        
        return fig
    
    @staticmethod
    def plot_roc_curve(
        y_true: np.ndarray,
        y_pred_proba: np.ndarray,
        save_path: Optional[Path] = None,
        model_name: str = "Model"
    ) -> plt.Figure:
        """
        Plot ROC curve.
        
        Args:
            y_true: True labels
            y_pred_proba: Predicted probabilities
            save_path: Path to save figure
            model_name: Name for legend
            
        Returns:
            Matplotlib figure
        """
        fpr, tpr, thresholds = roc_curve(y_true, y_pred_proba)
        roc_auc = roc_auc_score(y_true, y_pred_proba)
        
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.plot(fpr, tpr, label=f'{model_name} (AUC = {roc_auc:.3f})', linewidth=2)
        ax.plot([0, 1], [0, 1], 'k--', label='Random (AUC = 0.500)', linewidth=1)
        ax.set_xlabel('False Positive Rate')
        ax.set_ylabel('True Positive Rate')
        ax.set_title('ROC Curve')
        ax.legend(loc='lower right')
        ax.grid(alpha=0.3)
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            plt.close()
        
        return fig
    
    @staticmethod
    def plot_precision_recall_curve(
        y_true: np.ndarray,
        y_pred_proba: np.ndarray,
        save_path: Optional[Path] = None,
        model_name: str = "Model"
    ) -> plt.Figure:
        """
        Plot Precision-Recall curve.
        
        Args:
            y_true: True labels
            y_pred_proba: Predicted probabilities
            save_path: Path to save figure
            model_name: Name for legend
            
        Returns:
            Matplotlib figure
        """
        precision, recall, thresholds = precision_recall_curve(y_true, y_pred_proba)
        pr_auc = average_precision_score(y_true, y_pred_proba)
        
        # Baseline (random classifier)
        baseline = y_true.sum() / len(y_true)
        
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.plot(recall, precision, label=f'{model_name} (AP = {pr_auc:.3f})', linewidth=2)
        ax.axhline(y=baseline, color='k', linestyle='--', 
                   label=f'Baseline (AP = {baseline:.3f})', linewidth=1)
        ax.set_xlabel('Recall')
        ax.set_ylabel('Precision')
        ax.set_title('Precision-Recall Curve')
        ax.legend(loc='upper right')
        ax.grid(alpha=0.3)
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            plt.close()
        
        return fig
    
    @staticmethod
    def plot_threshold_analysis(
        y_true: np.ndarray,
        y_pred_proba: np.ndarray,
        save_path: Optional[Path] = None
    ) -> plt.Figure:
        """
        Plot precision, recall, F1 vs threshold.
        
        Args:
            y_true: True labels
            y_pred_proba: Predicted probabilities
            save_path: Path to save figure
            
        Returns:
            Matplotlib figure
        """
        thresholds = np.linspace(0, 1, 100)
        precisions = []
        recalls = []
        f1_scores = []
        
        for threshold in thresholds:
            y_pred = (y_pred_proba >= threshold).astype(int)
            precisions.append(precision_score(y_true, y_pred, zero_division=0))
            recalls.append(recall_score(y_true, y_pred, zero_division=0))
            f1_scores.append(f1_score(y_true, y_pred, zero_division=0))
        
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(thresholds, precisions, label='Precision', linewidth=2)
        ax.plot(thresholds, recalls, label='Recall', linewidth=2)
        ax.plot(thresholds, f1_scores, label='F1-Score', linewidth=2)
        
        # Mark optimal F1 threshold
        best_idx = np.argmax(f1_scores)
        best_threshold = thresholds[best_idx]
        ax.axvline(x=best_threshold, color='red', linestyle='--', 
                   label=f'Optimal F1 Threshold = {best_threshold:.3f}', linewidth=1)
        
        ax.set_xlabel('Threshold')
        ax.set_ylabel('Score')
        ax.set_title('Metrics vs Classification Threshold')
        ax.legend(loc='best')
        ax.grid(alpha=0.3)
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            plt.close()
        
        return fig


def generate_metrics_summary(metrics: Dict[str, float]) -> str:
    """
    Generate a formatted summary of metrics.
    
    Args:
        metrics: Dictionary of metric names and values
        
    Returns:
        Formatted string summary
    """
    summary = []
    summary.append("=" * 80)
    summary.append("METRICS SUMMARY")
    summary.append("=" * 80)
    
    # Basic metrics
    summary.append("\n📊 Classification Metrics:")
    summary.append(f"  Accuracy:    {metrics.get('accuracy', 0):.4f}")
    summary.append(f"  Precision:   {metrics.get('precision', 0):.4f}")
    summary.append(f"  Recall:      {metrics.get('recall', 0):.4f}")
    summary.append(f"  F1-Score:    {metrics.get('f1_score', 0):.4f}")
    summary.append(f"  Specificity: {metrics.get('specificity', 0):.4f}")
    
    # AUC metrics
    summary.append("\n📈 AUC Metrics:")
    summary.append(f"  ROC-AUC:     {metrics.get('roc_auc', 0):.4f}")
    summary.append(f"  PR-AUC:      {metrics.get('pr_auc', 0):.4f}")
    summary.append(f"  MCC:         {metrics.get('mcc', 0):.4f}")
    
    # Error rates
    summary.append("\n⚠️ Error Rates:")
    summary.append(f"  FPR (False Positive Rate): {metrics.get('false_positive_rate', 0):.4f}")
    summary.append(f"  FNR (False Negative Rate): {metrics.get('false_negative_rate', 0):.4f}")
    
    # Confusion matrix
    summary.append("\n🎯 Confusion Matrix:")
    summary.append(f"  True Negatives:  {metrics.get('true_negatives', 0):,}")
    summary.append(f"  False Positives: {metrics.get('false_positives', 0):,}")
    summary.append(f"  False Negatives: {metrics.get('false_negatives', 0):,}")
    summary.append(f"  True Positives:  {metrics.get('true_positives', 0):,}")
    
    summary.append("=" * 80)
    
    return "\n".join(summary)
