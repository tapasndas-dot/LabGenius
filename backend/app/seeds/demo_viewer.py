"""Operator-controlled DEMO_VIEWER reconciliation, never application startup seeding.

Run from backend: python -m app.seeds.demo_viewer --apply
User creation and ORGANIZATION-scoped assignment remain with the normal admin APIs/UI.
"""

import argparse

from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models.user.permission import Permission
from app.models.user.role import Role
from app.models.user.role_permission import RolePermission
from app.seeds.permissions import PERMISSION_CATALOG
from app.services.audit_service import AuditAction, AuditService


DEMO_VIEWER_ROLE_CODE = "DEMO_VIEWER"
DEMO_VIEWER_ROLE_NAME = "Demo Viewer"
DEMO_VIEWER_ACCESS_SCOPE = "ORGANIZATION"
DEMO_VIEWER_PERMISSION_CODES = (
    "organization.view",
    "business_unit.view",
    "division.view",
    "department.view",
    "designation.view",
    "location.view",
    "manufacturer.view",
    "instrument_type.view",
    "material.view",
    "instrument.view",
    "test.view",
    "method.view",
    "specification.view",
    "sample.view",
    "sample_test_result.view",
    "stability_protocol.view",
    "stability_study.view",
    "stability_pull.view",
)


def reconcile_demo_viewer(db: Session) -> Role:
    """Reconcile only the canonical role; caller owns commit/rollback.

    Fail closed before writes if the catalog/database is not ready. Do not seed the
    entire permission catalog here: its existing seed also modifies ADMIN mappings.
    """
    approved = set(DEMO_VIEWER_PERMISSION_CODES)
    catalog = {item["permission_code"] for item in PERMISSION_CATALOG}
    if approved - catalog:
        raise ValueError("DEMO_VIEWER specification contains missing catalog permissions.")

    permissions = db.query(Permission).filter(
        Permission.permission_code.in_(approved)
    ).all()
    if {permission.permission_code for permission in permissions if permission.is_active} != approved:
        raise ValueError("All 18 DEMO_VIEWER permissions must already exist and be active.")

    audit = AuditService()
    role = db.query(Role).filter(Role.role_code == DEMO_VIEWER_ROLE_CODE).first()
    if role is None:
        role = Role(
            role_code=DEMO_VIEWER_ROLE_CODE, role_name=DEMO_VIEWER_ROLE_NAME,
            description="Curated prospect read-only access through normal RBAC.",
            is_active=True,
        )
        db.add(role)
        db.flush()
        audit.record_action(
            db, action=AuditAction.CREATE, entity_type="Role", entity_id=role.id,
            changes={"created": audit.snapshot(role)}, source="OPERATOR",
        )
    elif role.role_name != DEMO_VIEWER_ROLE_NAME:
        before = audit.snapshot(role)
        role.role_name = DEMO_VIEWER_ROLE_NAME
        audit.record_action(
            db, action=AuditAction.UPDATE, entity_type="Role", entity_id=role.id,
            changes=audit.changes(before, audit.snapshot(role)), source="OPERATOR",
        )

    mappings = db.query(RolePermission).filter(RolePermission.role_id == role.id).all()
    approved_ids = {permission.id for permission in permissions}
    retained = {}
    for mapping in mappings:
        if mapping.permission_id not in approved_ids:
            audit.record_action(
                db, action=AuditAction.UNASSIGN, entity_type="RolePermission",
                entity_id=mapping.id, changes={"unassigned": audit.snapshot(mapping)},
                source="OPERATOR",
            )
            db.delete(mapping)
        else:
            retained[mapping.permission_id] = mapping

    for permission in permissions:
        mapping = retained.get(permission.id)
        if mapping is None:
            mapping = RolePermission(role_id=role.id, permission_id=permission.id, is_active=True)
            db.add(mapping)
            db.flush()
            audit.record_action(
                db, action=AuditAction.ASSIGN, entity_type="RolePermission",
                entity_id=mapping.id, changes={"assigned": audit.snapshot(mapping)},
                source="OPERATOR",
            )
        elif not mapping.is_active:
            before = audit.snapshot(mapping)
            mapping.is_active = True
            audit.record_action(
                db, action=AuditAction.ACTIVATE, entity_type="RolePermission",
                entity_id=mapping.id, changes=audit.changes(before, audit.snapshot(mapping)),
                source="OPERATOR",
            )

    db.flush()
    db.expire(role, ["role_permissions"])
    return role


def main() -> None:
    parser = argparse.ArgumentParser(description="Reconcile the canonical DEMO_VIEWER role only.")
    parser.add_argument("--apply", action="store_true", help="Explicitly authorize database writes.")
    args = parser.parse_args()
    if not args.apply:
        parser.error("--apply is required; confirm the target database before executing.")
    try:
        with SessionLocal.begin() as db:
            reconcile_demo_viewer(db)
    except Exception:
        # Do not print connection errors/tracebacks that might contain credentials.
        raise SystemExit("DEMO_VIEWER reconciliation failed; transaction rolled back.") from None
    print("DEMO_VIEWER reconciled with exactly 18 permissions. No users were changed.")


if __name__ == "__main__":
    main()
