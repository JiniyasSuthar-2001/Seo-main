"""
Centralized Master Permissions and Role-Based Access Control (RBAC) Module.
Provides authoritative server-side definitions, grouped permission structures,
and delegation validation functions.
"""
from typing import List, Dict, Set, Any

ALL_MASTER_PERMISSIONS = [
    # Dashboard
    "master.dashboard.view",
    
    # Customers
    "master.customers.view",
    "master.customers.create",
    "master.customers.edit",
    "master.customers.suspend",
    "master.customers.delete",
    
    # Websites
    "master.websites.view",
    "master.websites.edit",
    
    # AI Analytics & Control
    "master.ai_analytics.view",
    "master.ai_control.view",
    "master.ai_control.manage",
    
    # Credits
    "master.credits.view",
    "master.credits.manage",
    
    # Providers
    "master.providers.view",
    "master.providers.manage",
    
    # Global Activity
    "master.activity.view",
    
    # System Health
    "master.system_health.view",
    
    # Audit Logs
    "master.audit_logs.view",
    
    # Master Accounts Management
    "master.master_accounts.view",
    "master.master_accounts.create",
    "master.master_accounts.edit",
    "master.master_accounts.disable",
    "master.master_accounts.delete",
    
    # Roles Management
    "master.roles.view",
    "master.roles.create",
    "master.roles.edit",
    "master.roles.delete",
    
    # Session Management
    "master.sessions.view",
    "master.sessions.revoke"
]

PERMISSION_GROUPS = [
    {
        "id": "dashboard",
        "name": "Dashboard",
        "description": "Access to Master Space observability and metric overview",
        "permissions": [
            {"id": "master.dashboard.view", "label": "View Dashboard", "description": "View platform observability KPIs and charts"}
        ]
    },
    {
        "id": "customers",
        "name": "Customers",
        "description": "Customer accounts and tenant workspace administration",
        "permissions": [
            {"id": "master.customers.view", "label": "View Customers", "description": "View customer list and Customer 360 overview"},
            {"id": "master.customers.create", "label": "Create Customers", "description": "Provision new customer organizations"},
            {"id": "master.customers.edit", "label": "Edit Customers", "description": "Update customer details and profile"},
            {"id": "master.customers.suspend", "label": "Suspend / Unsuspend", "description": "Change customer status (Active / Suspended)"},
            {"id": "master.customers.delete", "label": "Delete Customers", "description": "Archive or remove customer accounts"}
        ]
    },
    {
        "id": "websites",
        "name": "Websites",
        "description": "Website audits, crawls, and health management",
        "permissions": [
            {"id": "master.websites.view", "label": "View Websites", "description": "View platform-wide websites, audits, and health"},
            {"id": "master.websites.edit", "label": "Edit Websites", "description": "Manage website settings and crawl schedules"}
        ]
    },
    {
        "id": "ai",
        "name": "AI Intelligence",
        "description": "AI request analytics, usage monitoring, and platform kill switches",
        "permissions": [
            {"id": "master.ai_analytics.view", "label": "View AI Analytics", "description": "View token usage, model requests, and costs"},
            {"id": "master.ai_control.view", "label": "View AI Controls", "description": "View platform AI budget and kill-switch states"},
            {"id": "master.ai_control.manage", "label": "Manage AI Control", "description": "Toggle global AI kill switches and budgets"}
        ]
    },
    {
        "id": "credits",
        "name": "Credits & Wallets",
        "description": "Tenant AI credit allocations, limits, and ledger inspection",
        "permissions": [
            {"id": "master.credits.view", "label": "View Credits", "description": "Inspect credit balances and transaction histories"},
            {"id": "master.credits.manage", "label": "Manage Credits", "description": "Allocate, adjust, or refund customer credits"}
        ]
    },
    {
        "id": "providers",
        "name": "Providers & Infrastructure",
        "description": "Third-party LLM and search provider configuration",
        "permissions": [
            {"id": "master.providers.view", "label": "View Providers", "description": "Inspect provider health and request distribution"},
            {"id": "master.providers.manage", "label": "Manage Providers", "description": "Configure routing rules and fallback providers"}
        ]
    },
    {
        "id": "activity",
        "name": "Global Activity",
        "description": "Platform-wide chronological audit stream",
        "permissions": [
            {"id": "master.activity.view", "label": "View Global Activity", "description": "Inspect chronological platform event stream"}
        ]
    },
    {
        "id": "system",
        "name": "System Health",
        "description": "Infrastructure status and error log monitoring",
        "permissions": [
            {"id": "master.system_health.view", "label": "View System Health", "description": "Inspect API, DB, Crawler, and Storage health"}
        ]
    },
    {
        "id": "audit",
        "name": "Audit Logs",
        "description": "Administrative security audit history",
        "permissions": [
            {"id": "master.audit_logs.view", "label": "View Audit Logs", "description": "Inspect administrative actions and security records"}
        ]
    },
    {
        "id": "master_accounts",
        "name": "Master Accounts",
        "description": "Master administration accounts and access delegation",
        "permissions": [
            {"id": "master.master_accounts.view", "label": "View Master Accounts", "description": "Inspect master accounts and assigned permissions"},
            {"id": "master.master_accounts.create", "label": "Create Master Account", "description": "Create additional Master Admin accounts"},
            {"id": "master.master_accounts.edit", "label": "Edit Master Account", "description": "Update Master Admin profiles and permissions"},
            {"id": "master.master_accounts.disable", "label": "Disable / Enable", "description": "Deactivate or reactivate Master Admin accounts"},
            {"id": "master.master_accounts.delete", "label": "Delete Master Account", "description": "Remove Master Admin accounts"}
        ]
    },
    {
        "id": "roles",
        "name": "Roles",
        "description": "Custom role creation and permission bundling",
        "permissions": [
            {"id": "master.roles.view", "label": "View Roles", "description": "Inspect custom role bundles"},
            {"id": "master.roles.create", "label": "Create Roles", "description": "Define new role permission templates"},
            {"id": "master.roles.edit", "label": "Edit Roles", "description": "Update custom role templates"},
            {"id": "master.roles.delete", "label": "Delete Roles", "description": "Remove unused custom roles"}
        ]
    },
    {
        "id": "sessions",
        "name": "Sessions",
        "description": "Master session inspection and security revocation",
        "permissions": [
            {"id": "master.sessions.view", "label": "View Sessions", "description": "Inspect active master authentication sessions"},
            {"id": "master.sessions.revoke", "label": "Revoke Sessions", "description": "Force logout and revoke active JWT sessions"}
        ]
    }
]

def get_all_permissions() -> List[str]:
    """Returns a flat list of all valid Master permission identifiers."""
    return list(ALL_MASTER_PERMISSIONS)

def get_grouped_permissions() -> List[Dict[str, Any]]:
    """Returns permission groups structured for frontend UI presentation."""
    return PERMISSION_GROUPS

def user_has_master_permission(user_role: str, user_permissions: List[str], required_permission: str) -> bool:
    """
    Evaluates whether a user holds the required Master permission.
    SUPER_MASTER and SUPER_ADMIN roles or '*' permission hold full authority.
    """
    clean_role = (user_role or "").upper()
    if clean_role in ("SUPER_MASTER", "SUPER_ADMIN"):
        return True
    if "*" in user_permissions or "ALL" in user_permissions:
        return True
    return required_permission in user_permissions

def validate_permission_delegation(actor_role: str, actor_permissions: List[str], target_permissions: List[str]) -> bool:
    """
    Enforces permission delegation hierarchy:
    SUPER_MASTER may grant any valid Master permission.
    A limited MASTER_ADMIN can ONLY delegate permissions they themselves possess.
    """
    clean_role = (actor_role or "").upper()
    if clean_role in ("SUPER_MASTER", "SUPER_ADMIN") or "*" in actor_permissions:
        return True
    
    actor_perm_set = set(actor_permissions)
    target_perm_set = set(target_permissions)
    
    # Target permissions must be a subset of actor's held permissions
    return target_perm_set.issubset(actor_perm_set)
