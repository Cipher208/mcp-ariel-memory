"""
Shared Module - cache, db pool, embeddings, metrics, saga, middleware, dream buffer, archived memories, migrations, read-only replica
"""
from .cache import MemoryCache
from .db_pool import DBPool
from .embeddings import EmbeddingCache, embed_text, embed_texts, similarity
from .metrics import metrics
from .saga import Saga, create_consolidation_saga, create_backup_saga
from .middleware import MiddlewarePipeline, MiddlewareContext, ValidationMiddleware, RateLimitMiddleware, ImportanceGateMiddleware, AuditMiddleware, DedupMiddleware
from .dream_buffer import DreamBuffer, dream_buffer
from .archived_memories import ArchivedMemories, archived_memories
from .migrations import MigrationManager, migration_manager
from .read_only import ReadOnlyReplica, read_only_replica

__all__ = [
    "MemoryCache", "DBPool",
    "EmbeddingCache", "embed_text", "embed_texts", "similarity",
    "metrics",
    "Saga", "create_consolidation_saga", "create_backup_saga",
    "MiddlewarePipeline", "MiddlewareContext", "ValidationMiddleware", "RateLimitMiddleware",
    "ImportanceGateMiddleware", "AuditMiddleware", "DedupMiddleware",
    "DreamBuffer", "dream_buffer",
    "ArchivedMemories", "archived_memories",
    "MigrationManager", "migration_manager",
    "ReadOnlyReplica", "read_only_replica",
]
