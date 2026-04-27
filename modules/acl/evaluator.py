
import fnmatch
from typing import Dict, List, Optional
from pydantic import BaseModel
from infra.db.sqlite import db

class UserPolicy(BaseModel):
    allow: List[str] = []
    deny: List[str] = []

class ACLEvaluator:
    def __init__(self):
        self._user_policies: Dict[str, UserPolicy] = {}
        self._role_policies: Dict[str, UserPolicy] = {}
        self._user_roles: Dict[str, List[str]] = {}

    async def load_policies(self):
        """Load roles and policies from database"""
        if not db._db:
            await db.init()
        
        # 1. Load Roles
        cur = await db._db.execute("SELECT name, allow_patterns, deny_patterns FROM roles")
        rows = await cur.fetchall()
        self._role_policies = {}
        for row in rows:
            name, allow, deny = row
            self._role_policies[name] = UserPolicy(
                allow=allow.split(",") if allow else [],
                deny=deny.split(",") if deny else []
            )

        # 2. Load User-Role mapping
        cur = await db._db.execute("SELECT username, role_name FROM user_roles")
        rows = await cur.fetchall()
        self._user_roles = {}
        for row in rows:
            user, role = row
            if user not in self._user_roles:
                self._user_roles[user] = []
            self._user_roles[user].append(role)

        # 3. Load User Direct Policies
        cur = await db._db.execute("SELECT user, allow_patterns, deny_patterns FROM acl_policies")
        rows = await cur.fetchall()
        self._user_policies = {}
        for row in rows:
            user, allow, deny = row
            self._user_policies[user] = UserPolicy(
                allow=allow.split(",") if allow else [],
                deny=deny.split(",") if deny else []
            )

    def is_allowed(self, user: str, resource: str) -> bool:
        # 1. Check User Direct Policies first (Override)
        user_policy = self._user_policies.get(user)
        if user_policy:
            # Deny takes precedence
            for pattern in user_policy.deny:
                if pattern == "*" or fnmatch.fnmatch(resource, pattern):
                    return False
            for pattern in user_policy.allow:
                if pattern == "*" or fnmatch.fnmatch(resource, pattern):
                    return True

        # 2. Check Roles
        roles = self._user_roles.get(user, [])
        for role_name in roles:
            role_policy = self._role_policies.get(role_name)
            if role_policy:
                # If any role denies, it's denied
                for pattern in role_policy.deny:
                    if pattern == "*" or fnmatch.fnmatch(resource, pattern):
                        return False
                # If any role allows, we mark it as potentially allowed but keep checking other roles for deny
                # (Simple model: any role allow + no role deny = allow)
        
        # Second pass for role allows
        for role_name in roles:
            role_policy = self._role_policies.get(role_name)
            if role_policy:
                for pattern in role_policy.allow:
                    if pattern == "*" or fnmatch.fnmatch(resource, pattern):
                        return True
        
        return False

acl_evaluator = ACLEvaluator()
