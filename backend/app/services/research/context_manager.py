"""
Context Window Management Service
Handles sliding windows, summarization, important content retention, overflow, and dynamic allocation
Optimized for M4 Pro - lightweight heuristics, no heavy models
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field


# ==================== Models ====================

class Message(BaseModel):
    """Single conversation message"""
    role: str = Field(..., description="Message role: system, user, assistant")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.now, description="Message timestamp")
    tokens: int = Field(default=0, description="Estimated token count")
    is_important: bool = Field(default=False, description="Whether message is important")
    importance_score: float = Field(default=0.0, description="Importance score (0-1)")


class ConversationWindow(BaseModel):
    """Conversation window with messages"""
    messages: List[Message] = Field(default_factory=list, description="Messages in window")
    total_tokens: int = Field(default=0, description="Total tokens in window")
    window_size: int = Field(default=10, description="Maximum messages in window")
    max_tokens: int = Field(default=4096, description="Maximum tokens allowed")
    overflow_detected: bool = Field(default=False, description="Whether overflow occurred")


class SummaryResult(BaseModel):
    """Context summarization result"""
    original_messages: int = Field(..., description="Number of original messages")
    original_tokens: int = Field(..., description="Original token count")
    summary: str = Field(..., description="Generated summary")
    summary_tokens: int = Field(..., description="Summary token count")
    compression_ratio: float = Field(..., description="Tokens saved ratio")
    messages_compressed: int = Field(..., description="Number of messages compressed")
    method: str = Field(default="extractive", description="Summarization method")


class ImportantContent(BaseModel):
    """Important content detection result"""
    message_index: int = Field(..., description="Index of message")
    content: str = Field(..., description="Message content")
    importance_score: float = Field(..., description="Importance score 0-1")
    reasons: List[str] = Field(default_factory=list, description="Why it's important")
    keywords: List[str] = Field(default_factory=list, description="Important keywords found")


class OverflowStatus(BaseModel):
    """Context overflow status"""
    current_tokens: int = Field(..., description="Current token count")
    max_tokens: int = Field(..., description="Maximum allowed tokens")
    utilization_percent: float = Field(..., description="Context utilization %")
    overflow_risk: str = Field(..., description="Risk level: safe, warning, critical, overflow")
    tokens_until_overflow: int = Field(..., description="Tokens until overflow")
    recommended_action: str = Field(..., description="What to do")
    can_fit_response: bool = Field(..., description="Can fit typical response")


class DynamicAllocation(BaseModel):
    """Dynamic context allocation result"""
    total_budget: int = Field(..., description="Total token budget")
    system_tokens: int = Field(..., description="Reserved for system")
    history_tokens: int = Field(..., description="Allocated for history")
    output_tokens: int = Field(..., description="Reserved for output")
    safety_margin: int = Field(..., description="Safety buffer")
    max_history_messages: int = Field(..., description="Max messages that fit")
    allocation_breakdown: Dict[str, float] = Field(default_factory=dict, description="Percentage breakdown")


class ManagedConversation(BaseModel):
    """Fully managed conversation result"""
    original_messages: int = Field(..., description="Original message count")
    original_tokens: int = Field(..., description="Original tokens")
    final_messages: int = Field(..., description="Final message count")
    final_tokens: int = Field(..., description="Final tokens")
    actions_taken: List[str] = Field(default_factory=list, description="Management actions")
    important_retained: int = Field(default=0, description="Important messages kept")
    summarized_count: int = Field(default=0, description="Messages summarized")
    pruned_count: int = Field(default=0, description="Messages pruned")
    managed_conversation: List[Message] = Field(default_factory=list, description="Final conversation")
    overflow_prevented: bool = Field(default=False, description="Whether overflow was prevented")


# ==================== Context Manager Service ====================

class ContextManager:
    """
    Context window management with sliding window, summarization, and overflow handling
    Optimized for M4 Pro - heuristic-based, no heavy models
    """

    def __init__(self):
        self.data_dir = Path("data/context_management")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Token estimation (same as tokenization service)
        self.avg_tokens_per_word = 0.75

        # Importance keywords (fraud domain)
        self.importance_keywords = {
            "critical", "urgent", "fraud", "suspicious", "unauthorized",
            "alert", "block", "approve", "reject", "violation", "anomaly",
            "risk", "high-risk", "investigation", "flagged", "detected",
            "policy", "rule", "threshold", "limit", "maximum", "minimum",
            "account", "balance", "transaction", "transfer", "payment",
            "decision", "recommendation", "conclusion", "result", "finding"
        }

        # Default allocation percentages
        self.default_allocation = {
            "system": 0.10,      # 10% for system prompt
            "history": 0.60,     # 60% for conversation history
            "output": 0.25,      # 25% reserved for output
            "safety": 0.05       # 5% safety margin
        }


    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text (heuristic-based)"""
        if not text:
            return 0

        # Word count baseline
        words = len(text.split())
        base_tokens = int(words * self.avg_tokens_per_word)

        # Adjust for special characters
        special_chars = len(re.findall(r'[^\w\s]', text))
        special_tokens = int(special_chars * 0.5)

        # Adjust for numbers
        numbers = len(re.findall(r'\b\d+\b', text))
        number_tokens = numbers

        # Adjust for code blocks (if present)
        code_blocks = len(re.findall(r'```[\s\S]*?```', text))
        code_tokens = code_blocks * 10

        return base_tokens + special_tokens + number_tokens + code_tokens


    def apply_sliding_window(
        self,
        messages: List[Dict[str, Any]],
        window_size: int = 10,
        preserve_system: bool = True
    ) -> ConversationWindow:
        """
        Apply sliding window to keep only recent messages

        Args:
            messages: List of message dicts with role, content
            window_size: Maximum number of messages to keep
            preserve_system: Always keep system messages

        Returns:
            ConversationWindow with windowed messages
        """
        if not messages:
            return ConversationWindow(messages=[], total_tokens=0, window_size=window_size)

        # Convert to Message objects and estimate tokens
        msg_objects = []
        for msg in messages:
            tokens = self.estimate_tokens(msg.get("content", ""))
            msg_obj = Message(
                role=msg.get("role", "user"),
                content=msg.get("content", ""),
                timestamp=datetime.fromisoformat(msg.get("timestamp", datetime.now().isoformat())),
                tokens=tokens
            )
            msg_objects.append(msg_obj)

        # Separate system messages
        system_msgs = [m for m in msg_objects if m.role == "system"]
        non_system_msgs = [m for m in msg_objects if m.role != "system"]

        # Apply sliding window to non-system messages
        if len(non_system_msgs) > window_size:
            windowed = non_system_msgs[-window_size:]
        else:
            windowed = non_system_msgs

        # Combine system + windowed (if preserve_system)
        if preserve_system:
            final_messages = system_msgs + windowed
        else:
            final_messages = windowed

        # Calculate total tokens
        total_tokens = sum(m.tokens for m in final_messages)

        # Log to JSONL
        self._log_window_operation({
            "operation": "sliding_window",
            "timestamp": datetime.now().isoformat(),
            "original_count": len(msg_objects),
            "windowed_count": len(final_messages),
            "window_size": window_size,
            "total_tokens": total_tokens
        })

        return ConversationWindow(
            messages=final_messages,
            total_tokens=total_tokens,
            window_size=window_size,
            overflow_detected=False
        )


    def summarize_context(
        self,
        messages: List[Dict[str, Any]],
        target_compression: float = 0.5
    ) -> SummaryResult:
        """
        Summarize conversation context (extractive summarization)

        Args:
            messages: List of message dicts
            target_compression: Target compression ratio (0.5 = 50% reduction)

        Returns:
            SummaryResult with summary and metrics
        """
        if not messages:
            return SummaryResult(
                original_messages=0,
                original_tokens=0,
                summary="",
                summary_tokens=0,
                compression_ratio=0.0,
                messages_compressed=0
            )

        # Calculate original tokens
        original_tokens = sum(self.estimate_tokens(m.get("content", "")) for m in messages)

        # Extractive summarization: Select most important sentences
        all_sentences = []
        for i, msg in enumerate(messages):
            content = msg.get("content", "")
            sentences = re.split(r'[.!?]+', content)
            for sent in sentences:
                sent = sent.strip()
                if sent:
                    # Score sentence by importance keywords
                    score = sum(1 for kw in self.importance_keywords if kw.lower() in sent.lower())
                    all_sentences.append({
                        "text": sent,
                        "score": score,
                        "msg_index": i,
                        "role": msg.get("role", "user")
                    })

        # Sort by score and select top sentences
        all_sentences.sort(key=lambda x: x["score"], reverse=True)

        # Calculate how many sentences to keep
        target_tokens = int(original_tokens * (1 - target_compression))
        selected_sentences = []
        current_tokens = 0

        for sent_obj in all_sentences:
            sent_tokens = self.estimate_tokens(sent_obj["text"])
            if current_tokens + sent_tokens <= target_tokens:
                selected_sentences.append(sent_obj)
                current_tokens += sent_tokens
            else:
                break

        # Sort selected sentences by original order
        selected_sentences.sort(key=lambda x: x["msg_index"])

        # Build summary
        summary_parts = []
        for sent in selected_sentences:
            role_prefix = f"[{sent['role']}]" if sent['role'] != 'user' else ""
            summary_parts.append(f"{role_prefix} {sent['text']}")

        summary = " ".join(summary_parts)
        summary_tokens = self.estimate_tokens(summary)

        # Calculate actual compression
        compression_ratio = 1 - (summary_tokens / original_tokens) if original_tokens > 0 else 0

        # Log to JSONL
        self._log_summarization({
            "timestamp": datetime.now().isoformat(),
            "original_messages": len(messages),
            "original_tokens": original_tokens,
            "summary_tokens": summary_tokens,
            "compression_ratio": compression_ratio,
            "method": "extractive"
        })

        return SummaryResult(
            original_messages=len(messages),
            original_tokens=original_tokens,
            summary=summary,
            summary_tokens=summary_tokens,
            compression_ratio=compression_ratio,
            messages_compressed=len(messages),
            method="extractive"
        )


    def detect_important_content(
        self,
        messages: List[Dict[str, Any]],
        threshold: float = 0.3
    ) -> List[ImportantContent]:
        """
        Detect important messages that should be retained

        Args:
            messages: List of message dicts
            threshold: Importance score threshold (0-1)

        Returns:
            List of ImportantContent objects
        """
        important_items = []

        for i, msg in enumerate(messages):
            content = msg.get("content", "")

            # Calculate importance score
            reasons = []
            keywords_found = []
            score = 0.0

            # Check for importance keywords
            content_lower = content.lower()
            for kw in self.importance_keywords:
                if kw in content_lower:
                    keywords_found.append(kw)
                    score += 0.1

            # Check for decision-related content
            if any(word in content_lower for word in ["decision", "approve", "reject", "block"]):
                reasons.append("Contains decision")
                score += 0.2

            # Check for numerical data (amounts, scores, thresholds)
            if re.search(r'\$[\d,]+|\d+\.\d+%|\d+/\d+', content):
                reasons.append("Contains numerical data")
                score += 0.15

            # Check for policy/rule references
            if any(word in content_lower for word in ["policy", "rule", "threshold", "limit"]):
                reasons.append("References policy/rules")
                score += 0.2

            # Check for anomaly/risk mentions
            if any(word in content_lower for word in ["anomaly", "risk", "suspicious", "fraud"]):
                reasons.append("Mentions risk/fraud")
                score += 0.25

            # Check for system messages (always important)
            if msg.get("role") == "system":
                reasons.append("System message")
                score += 0.3

            # Check for long, detailed content
            if len(content.split()) > 50:
                reasons.append("Detailed content")
                score += 0.1

            # Cap score at 1.0
            score = min(score, 1.0)

            # If above threshold, mark as important
            if score >= threshold:
                important_items.append(ImportantContent(
                    message_index=i,
                    content=content[:200] + "..." if len(content) > 200 else content,
                    importance_score=round(score, 2),
                    reasons=reasons,
                    keywords=keywords_found
                ))

        return important_items


    def check_overflow(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: int = 4096,
        output_reserve: int = 1024
    ) -> OverflowStatus:
        """
        Check for context window overflow

        Args:
            messages: List of message dicts
            max_tokens: Maximum context window size
            output_reserve: Tokens to reserve for output

        Returns:
            OverflowStatus with risk level and recommendations
        """
        # Calculate current token usage
        current_tokens = sum(self.estimate_tokens(m.get("content", "")) for m in messages)

        # Calculate available tokens (after output reserve)
        available_tokens = max_tokens - output_reserve

        # Calculate utilization
        utilization = (current_tokens / available_tokens) * 100

        # Determine risk level
        if current_tokens >= available_tokens:
            risk = "overflow"
            action = "CRITICAL: Immediate context pruning required"
            can_fit = False
        elif utilization >= 90:
            risk = "critical"
            action = "Summarize or prune context immediately"
            can_fit = False
        elif utilization >= 75:
            risk = "warning"
            action = "Consider summarizing older messages"
            can_fit = True
        else:
            risk = "safe"
            action = "No action needed"
            can_fit = True

        tokens_until_overflow = max(0, available_tokens - current_tokens)

        return OverflowStatus(
            current_tokens=current_tokens,
            max_tokens=max_tokens,
            utilization_percent=round(utilization, 1),
            overflow_risk=risk,
            tokens_until_overflow=tokens_until_overflow,
            recommended_action=action,
            can_fit_response=can_fit
        )


    def allocate_dynamic(
        self,
        total_budget: int = 4096,
        system_prompt: Optional[str] = None,
        expected_output_length: str = "medium"
    ) -> DynamicAllocation:
        """
        Dynamically allocate context window budget

        Args:
            total_budget: Total token budget
            system_prompt: System prompt to account for
            expected_output_length: short/medium/long

        Returns:
            DynamicAllocation with token allocations
        """
        # Calculate system tokens
        if system_prompt:
            system_tokens = self.estimate_tokens(system_prompt)
        else:
            # Default system prompt size
            system_tokens = int(total_budget * self.default_allocation["system"])

        # Calculate output reserve based on expected length
        output_multipliers = {
            "short": 0.15,   # 15% for short responses
            "medium": 0.25,  # 25% for medium responses
            "long": 0.40     # 40% for long responses
        }
        output_percent = output_multipliers.get(expected_output_length, 0.25)
        output_tokens = int(total_budget * output_percent)

        # Calculate safety margin
        safety_tokens = int(total_budget * self.default_allocation["safety"])

        # Remaining for history
        history_tokens = total_budget - system_tokens - output_tokens - safety_tokens

        # Calculate max messages that fit (assume avg 100 tokens per message)
        avg_tokens_per_message = 100
        max_history_messages = max(1, history_tokens // avg_tokens_per_message)

        # Breakdown percentages
        breakdown = {
            "system": round((system_tokens / total_budget) * 100, 1),
            "history": round((history_tokens / total_budget) * 100, 1),
            "output": round((output_tokens / total_budget) * 100, 1),
            "safety": round((safety_tokens / total_budget) * 100, 1)
        }

        return DynamicAllocation(
            total_budget=total_budget,
            system_tokens=system_tokens,
            history_tokens=history_tokens,
            output_tokens=output_tokens,
            safety_margin=safety_tokens,
            max_history_messages=max_history_messages,
            allocation_breakdown=breakdown
        )


    def manage_conversation(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: int = 4096,
        window_size: int = 10,
        preserve_important: bool = True,
        auto_summarize: bool = True
    ) -> ManagedConversation:
        """
        Comprehensive conversation management with all strategies

        Args:
            messages: List of message dicts
            max_tokens: Maximum context window
            window_size: Sliding window size
            preserve_important: Keep important messages
            auto_summarize: Auto-summarize when needed

        Returns:
            ManagedConversation with fully managed conversation
        """
        if not messages:
            return ManagedConversation(
                original_messages=0,
                original_tokens=0,
                final_messages=0,
                final_tokens=0,
                managed_conversation=[]
            )

        original_count = len(messages)
        original_tokens = sum(self.estimate_tokens(m.get("content", "")) for m in messages)

        actions = []
        current_messages = messages.copy()

        # Step 1: Check for overflow
        overflow = self.check_overflow(current_messages, max_tokens)

        if overflow.overflow_risk in ["overflow", "critical"]:
            actions.append(f"Overflow detected: {overflow.overflow_risk}")

            # Step 2: Detect important content
            important_content = []
            if preserve_important:
                important_content = self.detect_important_content(current_messages)
                important_indices = {ic.message_index for ic in important_content}
                actions.append(f"Identified {len(important_content)} important messages")
            else:
                important_indices = set()

            # Step 3: Apply sliding window (keep recent + important)
            if len(current_messages) > window_size:
                # Keep system messages
                system_msgs = [m for i, m in enumerate(current_messages) if m.get("role") == "system"]

                # Keep important messages
                important_msgs = [m for i, m in enumerate(current_messages) if i in important_indices and m.get("role") != "system"]

                # Keep recent messages (sliding window)
                recent_msgs = [m for i, m in enumerate(current_messages[-window_size:]) if m.get("role") != "system"]

                # Combine and deduplicate
                seen_content = set()
                combined = []

                for msg in system_msgs + important_msgs + recent_msgs:
                    content = msg.get("content", "")
                    if content not in seen_content:
                        combined.append(msg)
                        seen_content.add(content)

                pruned_count = len(current_messages) - len(combined)
                current_messages = combined
                actions.append(f"Applied sliding window: pruned {pruned_count} messages")

            # Step 4: Check if still overflowing
            current_tokens = sum(self.estimate_tokens(m.get("content", "")) for m in current_messages)

            if current_tokens > max_tokens * 0.75 and auto_summarize:
                # Summarize older messages (except system and important)
                messages_to_summarize = []
                messages_to_keep = []

                for i, msg in enumerate(current_messages):
                    # Keep system messages and important messages
                    if msg.get("role") == "system" or i in important_indices:
                        messages_to_keep.append(msg)
                    # Keep recent messages (last 3)
                    elif i >= len(current_messages) - 3:
                        messages_to_keep.append(msg)
                    else:
                        messages_to_summarize.append(msg)

                if messages_to_summarize:
                    summary_result = self.summarize_context(messages_to_summarize, target_compression=0.6)

                    # Create summary message
                    summary_msg = {
                        "role": "system",
                        "content": f"[Previous conversation summary]: {summary_result.summary}",
                        "timestamp": datetime.now().isoformat()
                    }

                    current_messages = [summary_msg] + messages_to_keep
                    actions.append(f"Summarized {len(messages_to_summarize)} messages ({summary_result.compression_ratio*100:.1f}% compression)")
        else:
            actions.append(f"No overflow: {overflow.utilization_percent}% utilization")

        # Convert to Message objects
        final_msg_objects = []
        for msg in current_messages:
            tokens = self.estimate_tokens(msg.get("content", ""))
            msg_obj = Message(
                role=msg.get("role", "user"),
                content=msg.get("content", ""),
                timestamp=datetime.fromisoformat(msg.get("timestamp", datetime.now().isoformat())),
                tokens=tokens,
                is_important=preserve_important
            )
            final_msg_objects.append(msg_obj)

        final_tokens = sum(m.tokens for m in final_msg_objects)

        # Count actions
        important_retained = len([ic for ic in (self.detect_important_content(current_messages) if preserve_important else [])])
        summarized_count = len([a for a in actions if "Summarized" in a])
        pruned_count = original_count - len(final_msg_objects)

        # Log to JSONL
        self._log_conversation_management({
            "timestamp": datetime.now().isoformat(),
            "original_messages": original_count,
            "original_tokens": original_tokens,
            "final_messages": len(final_msg_objects),
            "final_tokens": final_tokens,
            "actions": actions,
            "overflow_prevented": overflow.overflow_risk in ["overflow", "critical"]
        })

        return ManagedConversation(
            original_messages=original_count,
            original_tokens=original_tokens,
            final_messages=len(final_msg_objects),
            final_tokens=final_tokens,
            actions_taken=actions,
            important_retained=important_retained,
            summarized_count=summarized_count,
            pruned_count=pruned_count,
            managed_conversation=final_msg_objects,
            overflow_prevented=overflow.overflow_risk in ["overflow", "critical"]
        )


    # ==================== Logging ====================

    def _log_window_operation(self, data: Dict[str, Any]):
        """Log sliding window operation"""
        log_file = self.data_dir / "window_operations.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps(data) + "\n")


    def _log_summarization(self, data: Dict[str, Any]):
        """Log summarization operation"""
        log_file = self.data_dir / "summarizations.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps(data) + "\n")


    def _log_conversation_management(self, data: Dict[str, Any]):
        """Log conversation management operation"""
        log_file = self.data_dir / "conversation_management.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps(data) + "\n")


# ==================== Service Instance ====================

context_manager = ContextManager()
