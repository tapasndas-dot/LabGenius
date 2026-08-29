"""
Seed the standard LabGenius permission catalog and ADMIN role.

This script is idempotent:
- Existing permissions are preserved.
- Missing permissions are created.
- Existing ADMIN role is preserved.
- Missing ADMIN role is created.
- Existing role-permission mappings are preserved.
- Missing ADMIN mappings are created.

Run from backend directory:

    python -m app.seeds.permissions
"""

from sqlalchemy.orm import Session

from app.database.session import SessionLocal

from app.models.user.permission import Permission
from app.models.user.role import Role
from app.models.user.role_permission import RolePermission


# ---------------------------------------------------------------------------
# Standard permission catalog
# ---------------------------------------------------------------------------

PERMISSION_CATALOG = [
    {
        "permission_code": "audit.view",
        "permission_name": "View Audit Events",
        "description": "View application audit events within assigned organization scope.",
    },
    # Organization
    {
        "permission_code": "organization.view",
        "permission_name": "View Organization",
        "description": "View organization information.",
    },
    {
        "permission_code": "organization.create",
        "permission_name": "Create Organization",
        "description": "Create a new organization.",
    },
    {
        "permission_code": "organization.update",
        "permission_name": "Update Organization",
        "description": "Update organization information.",
    },
    {
        "permission_code": "organization.delete",
        "permission_name": "Delete Organization",
        "description": "Delete an organization.",
    },

    # Business Unit
    {
        "permission_code": "business_unit.view",
        "permission_name": "View Business Unit",
        "description": "View business unit information.",
    },
    {
        "permission_code": "business_unit.create",
        "permission_name": "Create Business Unit",
        "description": "Create a new business unit.",
    },
    {
        "permission_code": "business_unit.update",
        "permission_name": "Update Business Unit",
        "description": "Update business unit information.",
    },
    {
        "permission_code": "business_unit.delete",
        "permission_name": "Delete Business Unit",
        "description": "Delete a business unit.",
    },

    # Division
    {
        "permission_code": "division.view",
        "permission_name": "View Division",
        "description": "View division information.",
    },
    {
        "permission_code": "division.create",
        "permission_name": "Create Division",
        "description": "Create a new division.",
    },
    {
        "permission_code": "division.update",
        "permission_name": "Update Division",
        "description": "Update division information.",
    },
    {
        "permission_code": "division.delete",
        "permission_name": "Delete Division",
        "description": "Delete a division.",
    },

    # Department
    {
        "permission_code": "department.view",
        "permission_name": "View Department",
        "description": "View department information.",
    },
    {
        "permission_code": "department.create",
        "permission_name": "Create Department",
        "description": "Create a new department.",
    },
    {
        "permission_code": "department.update",
        "permission_name": "Update Department",
        "description": "Update department information.",
    },
    {
        "permission_code": "department.delete",
        "permission_name": "Delete Department",
        "description": "Delete a department.",
    },

    # Designation
    {
        "permission_code": "designation.view",
        "permission_name": "View Designation",
        "description": "View designation information.",
    },
    {
        "permission_code": "designation.create",
        "permission_name": "Create Designation",
        "description": "Create a new designation.",
    },
    {
        "permission_code": "designation.update",
        "permission_name": "Update Designation",
        "description": "Update designation information.",
    },
    {
        "permission_code": "designation.delete",
        "permission_name": "Delete Designation",
        "description": "Delete a designation.",
    },

    # User
    {
        "permission_code": "user.view",
        "permission_name": "View User",
        "description": "View user information.",
    },
    {
        "permission_code": "user.create",
        "permission_name": "Create User",
        "description": "Create a new user.",
    },
    {
        "permission_code": "user.update",
        "permission_name": "Update User",
        "description": "Update user information.",
    },
    {
        "permission_code": "user.delete",
        "permission_name": "Delete User",
        "description": "Delete a user.",
    },
        {
        "permission_code": "permission.view",
        "permission_name": "View Permissions",
        "description": "View application permission definitions.",
    },
    {
        "permission_code": "permission.update",
        "permission_name": "Update Permissions",
        "description": "Activate or deactivate application permissions.",
    },
    {
        "permission_code": "role.view",
        "permission_name": "View Roles",
        "description": "Allows viewing security roles.",
    },
    {
        "permission_code": "role.create",
        "permission_name": "Create Roles",
        "description": "Allows creating security roles.",
    },
    {
        "permission_code": "role.update",
        "permission_name": "Update Roles",
        "description": "Allows updating and activating or deactivating security roles.",
    },
    {
        "permission_code": "role.delete",
        "permission_name": "Delete Roles",
        "description": "Allows deleting security roles.",
    },
]

PERMISSION_CATALOG += [
    {
        "permission_code": f"{resource}.{action}",
        "permission_name": f"{action.title()} {display_name}",
        "description": f"{action.title()} {display_name.lower()} records within the actor's organization.",
    }
    for resource, display_name in (
        ("location", "Location"),
        ("manufacturer", "Manufacturer"),
        ("instrument_type", "Instrument Type"),
        ("material", "Material"),
    )
    for action in ("view", "create", "update", "delete")
]


# ---------------------------------------------------------------------------
# ADMIN role
# ---------------------------------------------------------------------------

ADMIN_ROLE_CODE = "ADMIN"
ADMIN_ROLE_NAME = "Administrator"
ADMIN_ROLE_DESCRIPTION = (
    "Full administrative access to the LabGenius application."
)


# ---------------------------------------------------------------------------
# Seed function
# ---------------------------------------------------------------------------

def seed_permissions(db: Session) -> None:
    """
    Create the standard permission catalog and ADMIN role mappings.

    The operation is idempotent and safe to execute repeatedly.
    """

    created_permissions = 0
    existing_permissions = 0
    created_mappings = 0
    existing_mappings = 0

    # -----------------------------------------------------------------------
    # 1. Create missing permissions
    # -----------------------------------------------------------------------

    permissions_by_code: dict[str, Permission] = {}

    for item in PERMISSION_CATALOG:

        permission = (
            db.query(Permission)
            .filter(
                Permission.permission_code
                == item["permission_code"]
            )
            .first()
        )

        if permission is None:
            permission = Permission(
                permission_code=item["permission_code"],
                permission_name=item["permission_name"],
                description=item["description"],
            )

            db.add(permission)

            created_permissions += 1

        else:
            existing_permissions += 1

        permissions_by_code[
            item["permission_code"]
        ] = permission

    # -----------------------------------------------------------------------
    # 2. Make sure all newly-created permissions have IDs
    # -----------------------------------------------------------------------

    db.flush()

    # -----------------------------------------------------------------------
    # 3. Find or create ADMIN role
    # -----------------------------------------------------------------------

    admin_role = (
        db.query(Role)
        .filter(
            Role.role_code == ADMIN_ROLE_CODE
        )
        .first()
    )

    if admin_role is None:

        admin_role = Role(
            role_code=ADMIN_ROLE_CODE,
            role_name=ADMIN_ROLE_NAME,
            description=ADMIN_ROLE_DESCRIPTION,
        )

        db.add(admin_role)

        db.flush()

        print("Created ADMIN role.")

    else:
        print(
            f"ADMIN role already exists: {admin_role.id}"
        )

    # -----------------------------------------------------------------------
    # 4. Assign every standard permission to ADMIN
    # -----------------------------------------------------------------------

    for permission in permissions_by_code.values():

        existing_mapping = (
            db.query(RolePermission)
            .filter(
                RolePermission.role_id
                == admin_role.id,
                RolePermission.permission_id
                == permission.id,
            )
            .first()
        )

        if existing_mapping is None:

            mapping = RolePermission(
                role_id=admin_role.id,
                permission_id=permission.id,
            )

            db.add(mapping)

            created_mappings += 1

        else:
            existing_mappings += 1

    # -----------------------------------------------------------------------
    # 5. Commit everything as one transaction
    # -----------------------------------------------------------------------

    db.commit()

    print()
    print("=" * 60)
    print("LabGenius Permission Seed Completed")
    print("=" * 60)
    print(
        f"Permissions created : {created_permissions}"
    )
    print(
        f"Permissions existing: {existing_permissions}"
    )
    print(
        f"ADMIN mappings created : {created_mappings}"
    )
    print(
        f"ADMIN mappings existing: {existing_mappings}"
    )
    print("=" * 60)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """
    Entry point for command-line execution.
    """

    db = SessionLocal()

    try:
        seed_permissions(db)

    except Exception:
        db.rollback()

        print()
        print("=" * 60)
        print("ERROR: Permission seed failed.")
        print("Transaction rolled back.")
        print("=" * 60)

        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
