"""
Hybrid Search Implementation - BM25 + Vector Search

Combines keyword-based BM25 with vector similarity for better retrieval.
Re-ranks results using cross-encoder for optimal relevance.
"""

import math
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


class BM25:
    """
    BM25 (Best Matching 25) algorithm for keyword-based search.

    BM25 scoring formula:
    score(D, Q) = Σ IDF(qi) * (f(qi, D) * (k1 + 1)) / (f(qi, D) + k1 * (1 - b + b * |D| / avgdl))

    where:
    - D: document
    - Q: query
    - qi: query term i
    - f(qi, D): frequency of qi in D
    - |D|: length of document D
    - avgdl: average document length
    - k1, b: tuning parameters
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus: List[List[str]] = []
        self.doc_freqs: List[Counter] = []
        self.idf: Dict[str, float] = {}
        self.avgdl: float = 0.0
        self.doc_len: List[int] = []

    def fit(self, corpus: List[str]):
        """Fit BM25 on corpus."""
        self.corpus = [doc.lower().split() for doc in corpus]
        self.doc_freqs = [Counter(doc) for doc in self.corpus]
        self.doc_len = [len(doc) for doc in self.corpus]
        self.avgdl = sum(self.doc_len) / len(self.doc_len) if self.doc_len else 0.0

        # Calculate IDF
        df = defaultdict(int)
        for doc in self.corpus:
            for word in set(doc):
                df[word] += 1

        num_docs = len(self.corpus)
        for word, freq in df.items():
            self.idf[word] = math.log((num_docs - freq + 0.5) / (freq + 0.5) + 1.0)

    def score(self, query: str, doc_idx: int) -> float:
        """Calculate BM25 score for a query and document."""
        query_terms = query.lower().split()
        score = 0.0
        doc_len = self.doc_len[doc_idx]
        doc_freqs = self.doc_freqs[doc_idx]

        for term in query_terms:
            if term not in self.idf:
                continue

            term_freq = doc_freqs.get(term, 0)
            idf = self.idf[term]

            # BM25 formula
            numerator = term_freq * (self.k1 + 1)
            denominator = term_freq + self.k1 * (1 - self.b + self.b * doc_len / self.avgdl)
            score += idf * (numerator / denominator)

        return score

    def get_top_n(self, query: str, n: int = 10) -> List[Tuple[int, float]]:
        """Get top N documents for query."""
        scores = [(idx, self.score(query, idx)) for idx in range(len(self.corpus))]
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:n]


class HybridSearch:
    """
    Hybrid search combining BM25 and vector similarity.

    Workflow:
    1. Retrieve candidates using BM25 (keyword matching)
    2. Retrieve candidates using vector search (semantic similarity)
    3. Merge and re-rank using weighted combination
    4. Optional: Re-rank with cross-encoder for final scores
    """

    def __init__(
        self,
        bm25_weight: float = 0.3,
        vector_weight: float = 0.7,
        use_reranking: bool = False,
    ):
        self.bm25_weight = bm25_weight
        self.vector_weight = vector_weight
        self.use_reranking = use_reranking
        self.bm25: Optional[BM25] = None
        self.documents: List[str] = []
        self.document_ids: List[str] = []
        self.metadatas: List[Dict[str, Any]] = []

    def index_documents(
        self,
        ids: List[str],
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ):
        """Index documents for hybrid search."""
        self.document_ids = ids
        self.documents = documents
        self.metadatas = metadatas or [{} for _ in documents]

        # Build BM25 index
        self.bm25 = BM25()
        self.bm25.fit(documents)

    def search(
        self,
        query: str,
        vector_results: List[Dict[str, Any]],
        n_results: int = 10,
        min_bm25_score: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search.

        Args:
            query: Search query
            vector_results: Results from vector search (ChromaDB)
            n_results: Number of results to return
            min_bm25_score: Minimum BM25 score threshold

        Returns:
            List of ranked results with hybrid scores
        """
        if not self.bm25:
            return vector_results[:n_results]

        # Get BM25 scores
        bm25_scores = {}
        for idx, (doc_id, score) in enumerate(self.bm25.get_top_n(query, n=len(self.documents))):
            if score >= min_bm25_score:
                bm25_scores[self.document_ids[doc_id]] = score

        # Normalize BM25 scores
        if bm25_scores:
            max_bm25 = max(bm25_scores.values())
            if max_bm25 > 0:
                bm25_scores = {k: v / max_bm25 for k, v in bm25_scores.items()}

        # Create lookup for vector scores
        vector_scores = {}
        for result in vector_results:
            doc_id = result.get("id")
            # ChromaDB returns distance, convert to similarity
            similarity = result.get("similarity", 0.0)
            if isinstance(similarity, (int, float)):
                vector_scores[doc_id] = similarity

        # Combine scores
        all_doc_ids = set(bm25_scores.keys()) | set(vector_scores.keys())
        hybrid_results = []

        for doc_id in all_doc_ids:
            bm25_score = bm25_scores.get(doc_id, 0.0)
            vector_score = vector_scores.get(doc_id, 0.0)

            # Weighted combination
            hybrid_score = (
                self.bm25_weight * bm25_score +
                self.vector_weight * vector_score
            )

            # Find document content and metadata
            doc_content = None
            doc_metadata = {}

            # Check vector results first
            for result in vector_results:
                if result.get("id") == doc_id:
                    doc_content = result.get("content")
                    doc_metadata = result.get("metadata", {})
                    break

            # If not in vector results, find in indexed documents
            if doc_content is None:
                try:
                    idx = self.document_ids.index(doc_id)
                    doc_content = self.documents[idx]
                    doc_metadata = self.metadatas[idx]
                except ValueError:
                    continue

            hybrid_results.append({
                "id": doc_id,
                "content": doc_content,
                "metadata": doc_metadata,
                "hybrid_score": hybrid_score,
                "bm25_score": bm25_score,
                "vector_score": vector_score,
            })

        # Sort by hybrid score
        hybrid_results.sort(key=lambda x: x["hybrid_score"], reverse=True)

        return hybrid_results[:n_results]

    def rerank(
        self,
        query: str,
        results: List[Dict[str, Any]],
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Re-rank results using cross-encoder (placeholder).

        In production, this would use a cross-encoder model like:
        - cross-encoder/ms-marco-MiniLM-L-6-v2
        - cross-encoder/ms-marco-electra-base

        For now, returns results as-is.
        """
        # TODO: Implement cross-encoder re-ranking
        # This would require loading a cross-encoder model
        # and scoring each query-document pair

        return results[:top_k]


class MemoryRetriever:
    """
    Memory retriever with hybrid search capabilities.
    Integrates with MemoryManager for intelligent retrieval.
    """

    def __init__(self, memory_manager):
        self.memory_manager = memory_manager
        self.hybrid_search: Optional[HybridSearch] = None
        self.indexed_collections: Dict[str, bool] = {}

    def build_index(self, collection_name: str):
        """Build BM25 index for a collection."""
        if collection_name == "episodic":
            collection = self.memory_manager.episodic.collection
        elif collection_name == "semantic":
            collection = self.memory_manager.semantic.collection
        else:
            raise ValueError(f"Unknown collection: {collection_name}")

        # Get all documents from collection
        results = collection.get()

        if not results["ids"]:
            return

        # Initialize hybrid search
        self.hybrid_search = HybridSearch(
            bm25_weight=0.3,
            vector_weight=0.7,
        )

        # Index documents
        self.hybrid_search.index_documents(
            ids=results["ids"],
            documents=results["documents"],
            metadatas=results["metadatas"],
        )

        self.indexed_collections[collection_name] = True

    def retrieve_with_hybrid_search(
        self,
        query: str,
        collection_name: str = "episodic",
        n_results: int = 10,
        min_similarity: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """Retrieve memories using hybrid search."""
        # Build index if not already done
        if collection_name not in self.indexed_collections:
            self.build_index(collection_name)

        # Get vector search results
        if collection_name == "episodic":
            vector_results = self.memory_manager.episodic.retrieve_similar(
                query=query,
                n_results=n_results * 2,  # Retrieve more for hybrid search
                min_similarity=min_similarity,
            )
        elif collection_name == "semantic":
            vector_results = self.memory_manager.semantic.retrieve_knowledge(
                query=query,
                n_results=n_results * 2,
            )
        else:
            return []

        # Apply hybrid search
        if self.hybrid_search:
            hybrid_results = self.hybrid_search.search(
                query=query,
                vector_results=vector_results,
                n_results=n_results,
            )
            return hybrid_results

        return vector_results[:n_results]

    def retrieve_contextual(
        self,
        query: str,
        context: Dict[str, Any],
        n_results: int = 5,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Retrieve memories with context awareness.

        Context can include:
        - transaction_type: Filter by transaction type
        - amount_range: Filter by amount range
        - time_range: Filter by time range
        - fraud_label: Filter by fraud status
        """
        results = {}

        # Build filters from context
        filters = {}
        if "transaction_type" in context:
            filters["transaction_type"] = context["transaction_type"]
        if "fraud_label" in context:
            filters["fraud_detected"] = context["fraud_label"]

        # Retrieve from episodic memory with filters
        episodic_results = self.memory_manager.episodic.retrieve_similar(
            query=query,
            n_results=n_results,
            filters=filters if filters else None,
        )
        results["episodic"] = episodic_results

        # Retrieve from semantic memory
        category = context.get("category")
        semantic_results = self.memory_manager.semantic.retrieve_knowledge(
            query=query,
            category=category,
            n_results=n_results,
        )
        results["semantic"] = semantic_results

        return results

    def get_retrieval_stats(self) -> Dict[str, Any]:
        """Get retrieval statistics."""
        return {
            "indexed_collections": list(self.indexed_collections.keys()),
            "hybrid_search_enabled": self.hybrid_search is not None,
            "bm25_weight": self.hybrid_search.bm25_weight if self.hybrid_search else None,
            "vector_weight": self.hybrid_search.vector_weight if self.hybrid_search else None,
        }
