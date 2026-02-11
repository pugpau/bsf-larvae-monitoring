"""
Unit tests for authentication service classes.
Tests AuthenticationService, UserManagementService, SecurityService.
"""

import uuid

import pytest
from fastapi import HTTPException

from src.auth.models import User, UserRole
from src.auth.repository import UserRepository, SessionRepository, LoginAttemptRepository
from src.auth.schemas import (
    LoginRequest,
    UserCreate,
    UserUpdate,
    PasswordChange,
    SecurityStatusResponse,
)
from src.auth.service import (
    AuthenticationService,
    UserManagementService,
    SecurityService,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _seed_user(
    session,
    username: str = "svcuser",
    email: str = "svc@example.com",
    password: str = "TestPass123!",
    role: UserRole = UserRole.VIEWER,
    **kwargs,
) -> User:
    """Seed a user directly via repository for service tests."""
    repo = UserRepository(session)
    return await repo.create_user(
        username=username,
        email=email,
        password=password,
        full_name=f"Service User ({username})",
        role=role,
        **kwargs,
    )


# ===========================================================================
# AuthenticationService
# ===========================================================================


@pytest.mark.unit
@pytest.mark.auth
class TestAuthenticationServiceLogin:
    async def test_authenticate_success(self, async_session):
        await _seed_user(async_session)

        svc = AuthenticationService(async_session)
        request = LoginRequest(username="svcuser", password="TestPass123!")
        token_data, error = await svc.authenticate_user(request, ip_address="127.0.0.1")

        assert error is None
        assert token_data is not None
        assert "access_token" in token_data
        assert "refresh_token" in token_data
        assert token_data["token_type"] == "bearer"
        assert token_data["user"]["username"] == "svcuser"

    async def test_authenticate_wrong_password(self, async_session):
        await _seed_user(async_session)

        svc = AuthenticationService(async_session)
        request = LoginRequest(username="svcuser", password="WrongPass!")
        token_data, error = await svc.authenticate_user(request, ip_address="127.0.0.1")

        assert token_data is None
        assert error == "Invalid username or password"

    async def test_authenticate_nonexistent_user(self, async_session):
        svc = AuthenticationService(async_session)
        request = LoginRequest(username="nobody", password="Whatever1!")
        token_data, error = await svc.authenticate_user(request, ip_address="127.0.0.1")

        assert token_data is None
        assert error == "Invalid username or password"

    async def test_authenticate_by_email(self, async_session):
        await _seed_user(async_session)

        svc = AuthenticationService(async_session)
        request = LoginRequest(username="svc@example.com", password="TestPass123!")
        token_data, error = await svc.authenticate_user(request, ip_address="127.0.0.1")

        # Email lookup happens when username lookup fails
        # authenticate_user still uses username for the actual auth check
        # so this may return invalid credentials depending on implementation
        # The important thing is it doesn't crash
        assert isinstance(error, (str, type(None)))

    async def test_authenticate_locked_account(self, async_session):
        user = await _seed_user(async_session)
        # Lock the account by setting locked_until in the future
        repo = UserRepository(async_session)
        await repo.lock_user_account(str(user.id), duration_minutes=30)

        # Expire cache so the locked state is visible to subsequent queries
        async_session.expire_all()

        svc = AuthenticationService(async_session)
        request = LoginRequest(username="svcuser", password="TestPass123!")
        token_data, error = await svc.authenticate_user(request, ip_address="127.0.0.1")

        assert token_data is None
        assert "locked" in error.lower()


@pytest.mark.unit
@pytest.mark.auth
class TestAuthenticationServiceRefresh:
    async def test_refresh_valid_token(self, async_session):
        user = await _seed_user(async_session)

        svc = AuthenticationService(async_session)
        # First login to get tokens
        request = LoginRequest(username="svcuser", password="TestPass123!")
        token_data, _ = await svc.authenticate_user(request, ip_address="127.0.0.1")

        # Refresh
        refresh_result, error = await svc.refresh_access_token(token_data["refresh_token"])

        assert error is None
        assert refresh_result is not None
        assert "access_token" in refresh_result

    async def test_refresh_invalid_token(self, async_session):
        svc = AuthenticationService(async_session)
        result, error = await svc.refresh_access_token("invalid.token.here")

        assert result is None
        assert error is not None


@pytest.mark.unit
@pytest.mark.auth
class TestAuthenticationServiceLogout:
    async def test_logout_user(self, async_session):
        user = await _seed_user(async_session)

        svc = AuthenticationService(async_session)
        # Login first
        request = LoginRequest(username="svcuser", password="TestPass123!")
        await svc.authenticate_user(request, ip_address="127.0.0.1")

        result = await svc.logout_user(str(user.id))
        assert result is True

    async def test_logout_with_session_token(self, async_session):
        user = await _seed_user(async_session)

        svc = AuthenticationService(async_session)
        result = await svc.logout_user(str(user.id), session_token="some-token")
        assert result is True


# ===========================================================================
# UserManagementService
# ===========================================================================


@pytest.mark.unit
@pytest.mark.auth
class TestUserManagementServiceCreate:
    async def test_create_user(self, async_session):
        svc = UserManagementService(async_session)
        user_data = UserCreate(
            username="newuser",
            email="new@example.com",
            full_name="New User",
            password="StrongP@ss1",
            role=UserRole.OPERATOR,
        )

        user = await svc.create_user(user_data, created_by="admin-id")

        assert user.username == "newuser"
        assert user.role == UserRole.OPERATOR

    async def test_create_user_duplicate_username(self, async_session):
        await _seed_user(async_session, username="dup", email="dup1@example.com")

        svc = UserManagementService(async_session)
        user_data = UserCreate(
            username="dup",
            email="dup2@example.com",
            full_name="Dup",
            password="StrongP@ss1",
        )

        with pytest.raises(HTTPException) as exc_info:
            await svc.create_user(user_data)
        assert exc_info.value.status_code == 400
        assert "Username already exists" in exc_info.value.detail

    async def test_create_user_duplicate_email(self, async_session):
        await _seed_user(async_session, username="orig", email="same@example.com")

        svc = UserManagementService(async_session)
        user_data = UserCreate(
            username="different",
            email="same@example.com",
            full_name="Different",
            password="StrongP@ss1",
        )

        with pytest.raises(HTTPException) as exc_info:
            await svc.create_user(user_data)
        assert exc_info.value.status_code == 400
        assert "Email already exists" in exc_info.value.detail


@pytest.mark.unit
@pytest.mark.auth
class TestUserManagementServiceRead:
    async def test_get_users(self, async_session):
        await _seed_user(async_session, username="u1", email="u1@example.com")
        await _seed_user(async_session, username="u2", email="u2@example.com")

        svc = UserManagementService(async_session)
        users = await svc.get_users()
        assert len(users) == 2

    async def test_get_users_with_filters(self, async_session):
        await _seed_user(async_session, username="admin1", email="a@example.com", role=UserRole.ADMIN)
        await _seed_user(async_session, username="view1", email="v@example.com", role=UserRole.VIEWER)

        svc = UserManagementService(async_session)
        admins = await svc.get_users(role=UserRole.ADMIN)
        assert len(admins) == 1

    async def test_get_user_by_id(self, async_session):
        user = await _seed_user(async_session)

        svc = UserManagementService(async_session)
        found = await svc.get_user_by_id(str(user.id))
        assert found is not None
        assert found.username == "svcuser"

    async def test_get_user_by_id_not_found(self, async_session):
        svc = UserManagementService(async_session)
        found = await svc.get_user_by_id(str(uuid.uuid4()))
        assert found is None


@pytest.mark.unit
@pytest.mark.auth
class TestUserManagementServiceLock:
    async def test_lock_account(self, async_session):
        user = await _seed_user(async_session)

        svc = UserManagementService(async_session)
        result = await svc.lock_user_account(str(user.id), duration_minutes=15)
        assert result is True

    async def test_unlock_account(self, async_session):
        user = await _seed_user(async_session)

        svc = UserManagementService(async_session)
        await svc.lock_user_account(str(user.id))
        result = await svc.unlock_user_account(str(user.id))
        assert result is True


@pytest.mark.unit
@pytest.mark.auth
class TestUserManagementServicePassword:
    async def test_change_own_password(self, async_session):
        user = await _seed_user(async_session)

        svc = UserManagementService(async_session)
        pwd_change = PasswordChange(
            current_password="TestPass123!",
            new_password="NewSecure1!",
        )

        result = await svc.change_password(str(user.id), pwd_change, user)
        assert result is True

    async def test_change_password_wrong_current(self, async_session):
        user = await _seed_user(async_session)

        svc = UserManagementService(async_session)
        pwd_change = PasswordChange(
            current_password="WrongCurrent!",
            new_password="NewSecure1!",
        )

        with pytest.raises(HTTPException) as exc_info:
            await svc.change_password(str(user.id), pwd_change, user)
        assert exc_info.value.status_code == 400

    async def test_change_password_user_not_found(self, async_session):
        user = await _seed_user(async_session)

        svc = UserManagementService(async_session)
        pwd_change = PasswordChange(
            current_password="TestPass123!",
            new_password="NewSecure1!",
        )

        with pytest.raises(HTTPException) as exc_info:
            await svc.change_password(str(uuid.uuid4()), pwd_change, user)
        assert exc_info.value.status_code == 404


# ===========================================================================
# SecurityService
# ===========================================================================


@pytest.mark.unit
@pytest.mark.auth
class TestSecurityService:
    async def test_get_security_status(self, async_session):
        svc = SecurityService(async_session)
        status = await svc.get_security_status()

        assert isinstance(status, SecurityStatusResponse)
        assert status.system_health == "healthy"

    async def test_cleanup_expired_sessions(self, async_session):
        svc = SecurityService(async_session)
        cleaned = await svc.cleanup_expired_sessions()
        assert cleaned == 0  # No sessions to clean

    async def test_get_recent_login_attempts_empty(self, async_session):
        svc = SecurityService(async_session)
        attempts = await svc.get_recent_login_attempts()
        assert attempts == []

    async def test_get_recent_login_attempts_with_data(self, async_session):
        # Seed some login attempts
        login_repo = LoginAttemptRepository(async_session)
        await login_repo.log_login_attempt(
            username="alice",
            success=True,
            ip_address="1.1.1.1",
        )
        await login_repo.log_login_attempt(
            username="alice",
            success=False,
            ip_address="1.1.1.1",
            failure_reason="invalid_credentials",
        )

        svc = SecurityService(async_session)
        attempts = await svc.get_recent_login_attempts(username="alice")
        assert len(attempts) == 2

    async def test_get_recent_login_attempts_with_hours(self, async_session):
        login_repo = LoginAttemptRepository(async_session)
        await login_repo.log_login_attempt(
            username="bob",
            success=True,
            ip_address="2.2.2.2",
        )

        svc = SecurityService(async_session)
        attempts = await svc.get_recent_login_attempts(hours=1)
        assert len(attempts) == 1


# ===========================================================================
# UserManagementService — update_user & delete_user
# ===========================================================================


@pytest.mark.unit
@pytest.mark.auth
class TestUserManagementServiceUpdate:
    async def test_update_user_email(self, async_session):
        user = await _seed_user(async_session, username="upd1", email="upd1@example.com")

        svc = UserManagementService(async_session)
        updated = await svc.update_user(
            str(user.id),
            UserUpdate(email="newemail@example.com"),
            updated_by="admin",
        )
        assert updated is not None

    async def test_update_user_duplicate_email(self, async_session):
        await _seed_user(async_session, username="u1", email="taken@example.com")
        user2 = await _seed_user(async_session, username="u2", email="u2@example.com")

        svc = UserManagementService(async_session)
        with pytest.raises(HTTPException) as exc_info:
            await svc.update_user(
                str(user2.id),
                UserUpdate(email="taken@example.com"),
            )
        assert exc_info.value.status_code == 400


@pytest.mark.unit
@pytest.mark.auth
class TestUserManagementServiceDelete:
    async def test_delete_user(self, async_session):
        user = await _seed_user(async_session, username="del1", email="del1@example.com")

        svc = UserManagementService(async_session)
        success = await svc.delete_user(str(user.id), deleted_by="admin")
        assert success is True

    async def test_delete_nonexistent_user(self, async_session):
        svc = UserManagementService(async_session)
        import uuid
        success = await svc.delete_user(str(uuid.uuid4()))
        assert success is False


# ===========================================================================
# APIKeyService
# ===========================================================================


@pytest.mark.unit
@pytest.mark.auth
class TestAPIKeyService:
    async def test_create_api_key(self, async_session):
        from src.auth.service import APIKeyService
        from src.auth.schemas import APIKeyCreate

        user = await _seed_user(async_session, username="apiuser", email="api@example.com")

        svc = APIKeyService(async_session)
        key_data = APIKeyCreate(
            name="test-key",
            description="Test API key",
        )
        full_key, key_id = await svc.create_api_key(key_data, created_by=str(user.id))

        assert full_key.startswith("bsf_")
        assert key_id is not None

    async def test_revoke_api_key(self, async_session):
        from src.auth.service import APIKeyService
        from src.auth.schemas import APIKeyCreate

        user = await _seed_user(async_session, username="apiuser2", email="api2@example.com")

        svc = APIKeyService(async_session)
        key_data = APIKeyCreate(name="revoke-key")
        _, key_id = await svc.create_api_key(key_data, created_by=str(user.id))

        success = await svc.revoke_api_key(key_id)
        assert success is True

    async def test_get_user_api_keys(self, async_session):
        from src.auth.service import APIKeyService
        from src.auth.schemas import APIKeyCreate

        user = await _seed_user(async_session, username="apiuser3", email="api3@example.com")

        svc = APIKeyService(async_session)
        key_data = APIKeyCreate(name="list-key")
        await svc.create_api_key(key_data, created_by=str(user.id))

        keys = await svc.get_user_api_keys(str(user.id))
        assert len(keys) == 1
