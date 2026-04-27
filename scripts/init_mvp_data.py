
import sys
import os
from pathlib import Path

# 将项目根目录添加到 sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

import asyncio
from infra.db.sqlite import db

async def init_data():
    await db.init()
    
    # 0. Ensure tables exist
    await db._db.execute(
        "CREATE TABLE IF NOT EXISTS acl_policies("
        "user TEXT PRIMARY KEY, "
        "allow_patterns TEXT, "
        "deny_patterns TEXT"
        ")"
    )
    await db._db.commit()

    # 1. Create users
    from infra.db.sqlite import db as sqlite_db
    await sqlite_db.create_user("user", "password")
    print("User 'user' created with password 'password'.")
    
    await sqlite_db.create_user("admin", "admin")
    print("User 'admin' created with password 'admin'.")
    
    # 2. Add Roles
    await db._db.execute(
        "INSERT OR REPLACE INTO roles (name, allow_patterns, deny_patterns) VALUES (?, ?, ?)",
        ("admin", "*", "")
    )
    await db._db.execute(
        "INSERT OR REPLACE INTO roles (name, allow_patterns, deny_patterns) VALUES (?, ?, ?)",
        ("user", "*", "")
    )

    # 3. Assign Roles
    await db._db.execute(
        "INSERT OR REPLACE INTO user_roles (username, role_name) VALUES (?, ?)",
        ("admin", "admin")
    )
    await db._db.execute(
        "INSERT OR REPLACE INTO user_roles (username, role_name) VALUES (?, ?)",
        ("user", "user")
    )

    # 4. Add User Direct Policies (Optional overrides)
    await db._db.execute(
        "INSERT OR REPLACE INTO acl_policies (user, allow_patterns, deny_patterns) "
        "VALUES (?, ?, ?)",
        ("alice", "127.0.0.1:*", "")
    )
    await db._db.commit()
    print("RBAC roles and policies added.")
    
    await db.close()

if __name__ == "__main__":
    asyncio.run(init_data())
