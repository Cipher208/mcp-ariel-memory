"""
Shared Module - connection manager, cache, embeddings, metrics, saga, middleware, dream buffer, archived memories, migrations, read-only replica
"""
from .connection import AsyncConnectionManager, connection_manager
from .cache import MemoryCache
from .embeddings import EmbeddingCache, embed_text, embed_texts, similarity
from .metrics import metrics
from .saga import Saga, create_consolidation_saga, create_backup_saga
from .middleware import MiddlewarePipeline, MiddlewareContext, ValidationMiddleware, RateLimitMiddleware, ImportanceGateMiddleware, AuditMiddleware, DedupMiddleware
from .dream_buffer import DreamBuffer
from .archived_memories import ArchivedMemories
from .migrations import MigrationManager, migration_manager
from .read_only import ReadOnlyReplica, read_only_replica

__all__ = [
    "AsyncConnectionManager", "connection_manager",
    "MemoryCache",
    "EmbeddingCache", "embed_text", "embed_texts", "similarity",
    "metrics",
    "Saga", "create_consolidation_saga", "create_backup_saga",
    "MiddlewarePipeline", "MiddlewareContext", "ValidationMiddleware", "RateLimitMiddleware",
    "ImportanceGateMiddleware", "AuditMiddleware", "DedupMiddleware",
    "DreamBuffer",
    "ArchivedMemories",
    "MigrationManager", "migration_manager",
    "ReadOnlyReplica", "read_only_replica",
]
