import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from infra.db.sqlite import SQLiteDB


class SQLiteDBTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        handle = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        handle.close()
        self.db_path = handle.name
        self.db = SQLiteDB(self.db_path)
        await self.db.init()

    async def asyncTearDown(self):
        await self.db.close()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    async def test_create_user_requires_unique_username(self):
        await self.db.create_user("alice", "secret")

        self.assertTrue(await self.db.validate_password("alice", "secret"))

        with self.assertRaisesRegex(ValueError, "Username already exists"):
            await self.db.create_user("alice", "another-secret")

    async def test_user_tunnel_crud_is_scoped_to_owner(self):
        await self.db.create_user("alice", "secret")
        await self.db.create_user("bob", "secret")

        tunnel_config = {
            "ssh_host": "10.0.0.1",
            "ssh_port": 22,
            "username": "root",
            "password": "ssh-pass",
            "local_port": 9000,
            "remote_host": "127.0.0.1",
            "remote_port": 80,
            "type": "local",
            "remark": "prod",
            "group_name": "生产环境",
        }

        await self.db.save_user_tunnel("alice", "tid-1", tunnel_config, is_active=True)

        alice_tunnel = await self.db.get_user_tunnel("alice", "tid-1")
        self.assertIsNotNone(alice_tunnel)
        self.assertTrue(alice_tunnel["is_active"])
        self.assertEqual(alice_tunnel["remark"], "prod")
        self.assertEqual(alice_tunnel["group_name"], "生产环境")
        self.assertIsNone(await self.db.get_user_tunnel("bob", "tid-1"))

        await self.db.update_user_tunnel(
            "alice",
            "tid-1",
            {"remark": "prod-updated", "local_port": 9001, "group_name": "核心服务"},
            is_active=False,
        )

        updated = await self.db.get_user_tunnel("alice", "tid-1")
        self.assertEqual(updated["remark"], "prod-updated")
        self.assertEqual(updated["local_port"], 9001)
        self.assertEqual(updated["group_name"], "核心服务")
        self.assertFalse(updated["is_active"])

        await self.db.set_user_tunnel_active("alice", "tid-1", True)
        reactivated = await self.db.get_user_tunnel("alice", "tid-1")
        self.assertTrue(reactivated["is_active"])

        self.assertEqual(len(await self.db.list_user_tunnels("alice")), 1)
        self.assertEqual(len(await self.db.list_user_tunnels("bob")), 0)

        self.assertTrue(await self.db.delete_user_tunnel("alice", "tid-1"))
        self.assertEqual(len(await self.db.list_user_tunnels("alice")), 0)

    async def test_tunnel_groups_can_be_listed_renamed_and_cleared(self):
        await self.db.create_user("alice", "secret")
        base_config = {
            "ssh_host": "10.0.0.1",
            "ssh_port": 22,
            "username": "root",
            "password": "ssh-pass",
            "local_port": 9000,
            "remote_host": "127.0.0.1",
            "remote_port": 80,
            "type": "local",
            "remark": "prod",
        }

        await self.db.save_user_tunnel("alice", "tid-1", {**base_config, "group_name": "生产"}, is_active=True)
        await self.db.save_user_tunnel("alice", "tid-2", {**base_config, "local_port": 9001, "group_name": "生产"}, is_active=False)
        await self.db.save_user_tunnel("alice", "tid-3", {**base_config, "local_port": 9002, "group_name": "测试"}, is_active=False)

        groups = await self.db.list_user_tunnel_groups("alice")
        groups_by_name = {group["group_name"]: group for group in groups}
        self.assertEqual(groups_by_name["生产"]["tunnel_count"], 2)
        self.assertEqual(groups_by_name["生产"]["active_count"], 1)

        renamed = await self.db.rename_user_tunnel_group("alice", "生产", "核心")
        self.assertEqual(renamed, 2)
        renamed_tunnel = await self.db.get_user_tunnel("alice", "tid-1")
        self.assertEqual(renamed_tunnel["group_name"], "核心")

        cleared = await self.db.clear_user_tunnel_group("alice", "测试")
        self.assertEqual(cleared, 1)
        cleared_tunnel = await self.db.get_user_tunnel("alice", "tid-3")
        self.assertIsNone(cleared_tunnel["group_name"])

    async def test_delete_audit_logs_older_than_cutoff(self):
        now = datetime.now(timezone.utc)
        old_timestamp = (now - timedelta(days=10)).isoformat()
        recent_timestamp = (now - timedelta(hours=2)).isoformat()

        await self.db.add_audit_log(old_timestamp, "admin", "login", "system", "success", "old")
        await self.db.add_audit_log(recent_timestamp, "admin", "login", "system", "success", "recent")

        deleted_count = await self.db.delete_audit_logs_older_than(
            (now - timedelta(days=7)).isoformat()
        )
        logs = await self.db.list_audit_logs(limit=10)

        self.assertEqual(deleted_count, 1)
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["details"], "recent")


if __name__ == "__main__":
    unittest.main()
