"""Operations tools — auth, backup, saga, data transfer, search.

Merged into action-based tools to reduce tool count.
"""

import asyncio
import time
from pathlib import Path

from mcp.server.fastmcp import Context

from shared.metrics import metrics


def _get_ctx(ctx: Context):
    from mcp_server.server import _get_ctx as _g

    return _g(ctx)


def register_tools(mcp):
    @mcp.tool()
    async def memory_api_key(
        action: str = "list",
        user_id: str = "default",
        label: str = "",
        api_key: str = "",
        ctx: Context = None,
    ) -> dict:
        """Manage API keys.

        Args:
            action: "create", "revoke", or "list"
            user_id: User to create key for (create only)
            label: Optional label (create only)
            api_key: Key to revoke (revoke only)
        """
        from features.auth import api_key_auth

        metrics.inc("tool_calls")
        metrics.inc("tool_api_key")

        if action == "create":
            key = api_key_auth.create_key(user_id, label)
            return {"api_key": key, "user_id": user_id, "label": label}
        elif action == "revoke":
            revoked = api_key_auth.revoke(api_key)
            return {"revoked": revoked}
        else:
            return {"keys": api_key_auth.list_keys()}

    @mcp.tool()
    async def memory_backup(
        action: str = "status",
        backup_name: str = "",
        ctx: Context = None,
    ) -> dict:
        """Manage backups.

        Args:
            action: "now", "list", "restore", or "status"
            backup_name: Backup to restore (restore only)
        """
        from features.backup_cron import backup_cron

        metrics.inc("tool_calls")
        metrics.inc("tool_backup")

        if action == "now":
            path = await backup_cron.backup_now()
            return {"path": path}
        elif action == "list":
            return {"backups": await backup_cron.list_backups()}
        elif action == "restore":
            return await backup_cron.restore(backup_name)
        else:
            return backup_cron.status()

    @mcp.tool()
    async def memory_saga(
        action: str = "consolidate",
        user_id: str = "default",
        ctx: Context = None,
    ) -> dict:
        """Run sagas with auto-rollback on failure.

        Args:
            action: "consolidate" (gather→distill→promote) or "backup" (copy→verify)
            user_id: User identifier (consolidate only)
        """
        metrics.inc("tool_calls")
        metrics.inc("tool_saga")
        app = _get_ctx(ctx)

        if action == "consolidate":
            from shared.saga import create_consolidation_saga

            saga = create_consolidation_saga(user_id, mm=app.mm)
            result = await saga.execute({"user_id": user_id, "_mm": app.mm})
        else:
            from shared.saga import create_backup_saga

            saga = create_backup_saga()
            result = await saga.execute()

        return {"status": saga.status.value, "result": result, "steps": saga.get_state()["steps"]}

    @mcp.tool()
    async def memory_data(
        action: str = "list",
        user_id: str = "default",
        file_path: str = "",
        target_user_id: str = "",
        ctx: Context = None,
    ) -> dict:
        """Import/export memory data.

        Args:
            action: "export", "import", or "list"
            user_id: User to export (export only)
            file_path: File to import (import only)
            target_user_id: Import as this user (import only, defaults to user_id)
        """
        metrics.inc("tool_calls")
        metrics.inc("tool_data")
        app = _get_ctx(ctx)

        if action == "export":
            path = await app.import_export.export_user(user_id)
            return {"path": path}
        elif action == "import":
            result = await app.import_export.import_user(file_path, target_user_id or user_id)
            return result
        else:
            return {"exports": app.import_export.list_exports()}

    @mcp.tool()
    async def memory_sync_replica(
        ctx: Context = None,
    ) -> dict:
        """Sync read-only replica for dashboard/metrics."""
        metrics.inc("tool_calls")
        metrics.inc("tool_sync_replica")
        from shared.read_only import read_only_replica

        result = await asyncio.to_thread(read_only_replica.sync)
        return {"synced": result, "ready": read_only_replica.is_ready()}

    @mcp.tool()
    async def memory_cleanup(
        user_id: str = "default",
        retention_days: int = 30,
        ctx: Context = None,
    ) -> dict:
        """Full memory cleanup: deduplicate, archive, clean staging.

        Args:
            user_id: User identifier
            retention_days: Days to keep audit logs (default 30)
        """
        metrics.inc("tool_calls")
        metrics.inc("tool_cleanup")

        from features.compression import MemoryCompressor
        from features.audit_trail import AuditTrail
        from features.backup_cron import backup_cron
        from shared.dream_buffer import dream_buffer
        from shared.saga import saga_watchdog

        mc = MemoryCompressor()
        at = AuditTrail()
        archive_dir = str(Path.home() / ".mcp-ariel-memory" / "archives")

        results = {}

        dedup_task = mc.deduplicate_core(user_id)
        compress_task = mc.compress_episodes(user_id, 0.3)
        dream_task = dream_buffer.cleanup_old(24, 500)
        audit_task = at.archive_and_prune(retention_days, archive_dir)
        backup_task = backup_cron.cleanup_old()

        dedup_r, compress_r, dream_r, audit_r, backup_r = await asyncio.gather(dedup_task, compress_task, dream_task, audit_task, backup_task)

        results["dedup_core"] = dedup_r
        results["compress_episodes"] = compress_r
        results["dream_buffer_cleanup"] = dream_r
        results["audit_archive"] = audit_r
        results["backup_cleanup"] = backup_r
        results["saga_cleanup"] = saga_watchdog.cleanup_completed()

        return results

    @mcp.tool()
    async def memory_lucidity_purge(
        user_id: str = "default",
        hours: int = 24,
        ctx: Context = None,
    ) -> dict:
        """Emergency purge: delete all data from the last N hours.

        Args:
            user_id: User identifier
            hours: How many hours back to purge (default 24)
        """
        metrics.inc("tool_calls")
        metrics.inc("tool_lucidity_purge")
        app = _get_ctx(ctx)
        cutoff = time.time() - (hours * 3600)

        async def _delete_core():
            conn = await app.mm.user_memory(user_id).l4._get_conn()
            try:
                cursor = await conn.execute("DELETE FROM core_memory WHERE user_id=? AND created_at > ?", (user_id, cutoff))
                result = cursor.rowcount
                await conn.commit()
                return result
            finally:
                conn.close()

        async def _delete_episodes():
            conn = await app.mm.user_memory(user_id).l3._get_conn()
            try:
                cursor = await conn.execute("DELETE FROM episodes WHERE user_id=? AND created_at > ?", (user_id, cutoff))
                result = cursor.rowcount
                await conn.commit()
                return result
            finally:
                conn.close()

        async def _delete_staging():
            from shared.dream_buffer import DreamBuffer

            db = DreamBuffer()
            return db.clear_staging(user_id)

        async def _delete_audit():
            from features.audit_trail import AuditTrail

            at = AuditTrail()
            conn = at._get_conn()
            try:
                cursor = await conn.execute("DELETE FROM audit_log WHERE user_id=? AND timestamp > ?", (user_id, cutoff))
                result = cursor.rowcount
                await conn.commit()
                return result
            finally:
                conn.close()

        async def _delete_graph():
            from graph.epistemic import EpistemicGraph

            eg = EpistemicGraph(layer="user")
            conn = eg._get_conn()
            try:
                cursor = await conn.execute("DELETE FROM epi_nodes WHERE user_id=? AND created_at > ?", (user_id, cutoff))
                result = cursor.rowcount
                await conn.commit()
                return result
            finally:
                conn.close()

        core_r, episodes_r, staging_r, audit_r, graph_r = await asyncio.gather(
            _delete_core(), _delete_episodes(), _delete_staging(), _delete_audit(), _delete_graph()
        )

        return {
            "core_memory": core_r,
            "episodes": episodes_r,
            "staging": staging_r,
            "audit": audit_r,
            "graph_nodes": graph_r,
        }

    @mcp.tool()
    async def memory_search_rrf(
        query: str = "",
        user_id: str = "default",
        limit: int = 10,
        strategy: str = "hybrid",
        ctx: Context = None,
    ) -> dict:
        """Hybrid search using Reciprocal Rank Fusion (FTS5 + vector similarity).

        Args:
            query: Search query
            user_id: User identifier
            limit: Max results (default 10)
            strategy: "fts" (keyword), "mib" (semantic), "hybrid" (combined), or "auto" (auto-select)
        """
        metrics.inc("tool_calls")
        metrics.inc("tool_search_rrf")
        app = _get_ctx(ctx)
        results = await app.user_rag.search(query, user_id=user_id, strategy=strategy, limit=limit)
        return {"results": results, "count": len(results), "strategy": strategy}
