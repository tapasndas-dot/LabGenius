from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.auth.hashing import verify_password

from app.models.user.user import User

from app.repositories.user.user_repository import UserRepository

from app.services.user.security_service import (
    SecurityService,
)
from app.services.user.security_audit_service import SecurityAuditService


class AuthService:

    def __init__(self):
        self.user_repository = UserRepository()
        self.security_service = SecurityService()

    def authenticate_user(
        self,
        db: Session,
        username: str,
        password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> User:

        user = self.user_repository.get_by_username(
            db,
            username,
        )

        # ----------------------------------------
        # User does not exist
        # ----------------------------------------

        if user is None:
            self._record_failed_attempt(
                db,
                username=username,
                failure_reason="INVALID_CREDENTIALS",
                ip_address=ip_address,
                user_agent=user_agent,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )

        # ----------------------------------------
        # Account inactive
        # ----------------------------------------

        if not user.is_active:
            self._record_failed_attempt(
                db,
                username=username,
                user=user,
                failure_reason="ACCOUNT_INACTIVE",
                ip_address=ip_address,
                user_agent=user_agent,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is inactive",
            )

        # ----------------------------------------
        # Account currently locked
        # ----------------------------------------

        if self.security_service.is_locked(user):

            self._record_failed_attempt(
                db,
                username=username,
                user=user,
                failure_reason="ACCOUNT_LOCKED",
                ip_address=ip_address,
                user_agent=user_agent,
            )

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is temporarily locked",
            )

        # ----------------------------------------
        # Lockout period has expired
        # ----------------------------------------

        if user.account_status == "LOCKED":

            user.account_status = "ACTIVE"
            user.failed_login_attempts = 0
            user.locked_until = None

            self.security_service.repository.save(
                db,
                user,
            )

        # ----------------------------------------
        # Verify password
        # ----------------------------------------

        if not verify_password(
            password,
            user.password_hash,
        ):

            self.security_service.record_failed_login(
                db,
                user,
            )

            self._record_failed_attempt(
                db,
                username=username,
                user=user,
                failure_reason="INVALID_CREDENTIALS",
                ip_address=ip_address,
                user_agent=user_agent,
                account_locked=user.account_status == "LOCKED",
            )

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )

        # ----------------------------------------
        # Successful login
        # ----------------------------------------

        self.security_service.record_successful_login(
            db,
            user,
        )

        self.security_service.audit_service.record_login(
            db,
            username=username,
            user_id=user.id,
            success=True,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.security_service.audit_service.record_event(
            db,
            event_type=SecurityAuditService.LOGIN_SUCCESS,
            actor_user_id=user.id,
            target_user_id=user.id,
        )
        db.commit()
        db.refresh(user)

        return user

    def _record_failed_attempt(
        self,
        db: Session,
        *,
        username: str,
        failure_reason: str,
        user: User | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        account_locked: bool = False,
    ) -> None:
        user_id = user.id if user is not None else None
        audit = self.security_service.audit_service
        audit.record_login(
            db,
            username=username,
            user_id=user_id,
            success=False,
            failure_reason=failure_reason,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        audit.record_event(
            db,
            event_type=SecurityAuditService.LOGIN_FAILURE,
            target_user_id=user_id,
            details={"failure_reason": failure_reason},
        )
        if account_locked:
            audit.record_event(
                db,
                event_type=SecurityAuditService.ACCOUNT_LOCKED,
                target_user_id=user_id,
                details={"failed_login_attempts": user.failed_login_attempts},
            )
        db.commit()
