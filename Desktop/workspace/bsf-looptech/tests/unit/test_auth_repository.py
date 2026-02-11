"""
Unit tests for authentication repository classes.
Tests UserRepository, SessionRepository, LoginAttemptRepository, APIKeyRepository.
"""

import uuid
from datetime import datetime, timedelta

import pytest

from src.auth.models import User, UserRole, Permission, DEFAULT_ROLE_PERMISSIONS
from src.auth.repository import (
    UserRepository,
    SessionRepository,
    LoginAttemptRepository,
    APIKeyRepository,
)
from src.auth.security import get_password_hash, SecurityConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_test_user(
    repo: UserRepository,
    username: str = "testuser",
    email: str = "test@example.com",
    password: str = "TestPass123!",
    role: UserRole = UserRole.VIEWER,
    **kwargs,
) -> User:
    """Helper to create a user through the repository."""
    return await repo.create_user(
        username=username,
        email=email,
        password=password,
        full_name=f"Test User ({username})",
        role=role,
        **kwargs,
    )


# ===========================================================================
# UserRepository
# ===========================================================================


@pytest.mark.unit
@pytest.mark.auth
class TestUserRepositoryCreate:
    async def test_create_user(self, async_session):
        repo = UserRepository(async_session)
        user = await _create_test_user(repo)

        assert user.id is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.full_name == "Test User (testuser)"
        assert user.role == UserRole.VIEWER
        assert user.is_active is True
        assert user.hashed_password != "TestPass123!"

    async def test_create_user_with_role(self, async_session):
        repo = UserRepository(async_session)
        user = await _create_test_user(repo, role=UserRole.ADMIN)

        assert user.role == UserRole.ADMIN

    async def test_create_user_with_extra_fields(self, async_session):
        repo = UserRepository(async_session)
        user = await _create_test_user(
            repo,
            phone="090-1234-5678",
            department="Engineering",
            position="Engineer",
        )

        assert user.phone == "090-1234-5678"
        assert user.department == "Engineering"


@pytest.mark.unit
@pytest.mark.auth
class TestUserRepositoryGet:
    async def test_get_user_by_id(self, async_session):
        repo = UserRepository(async_session)
        created = await _create_test_user(repo)

        found = await repo.get_user_by_id(str(created.id))
        assert found is not None
        assert found.username == "testuser"

    async def test_get_user_by_id_not_found(self, async_session):
        repo = UserRepository(async_session)
        found = await repo.get_user_by_id(str(uuid.uuid4()))
        assert found is None

    async def test_get_user_by_username(self, async_session):
        repo = UserRepository(async_session)
        await _create_test_user(repo)

        found = await repo.get_user_by_username("testuser")
        assert found is not None
        assert found.email == "test@example.com"

    async def test_get_user_by_username_not_found(self, async_session):
        repo = UserRepository(async_session)
        found = await repo.get_user_by_username("nonexistent")
        assert found is None

    async def test_get_user_by_email(self, async_session):
        repo = UserRepository(async_session)
        await _create_test_user(repo)

        found = await repo.get_user_by_email("test@example.com")
        assert found is not None
        assert found.username == "testuser"

    async def test_get_user_by_email_not_found(self, async_session):
        repo = UserRepository(async_session)
        found = await repo.get_user_by_email("nope@example.com")
        assert found is None


@pytest.mark.unit
@pytest.mark.auth
class TestUserRepositoryAuthenticate:
    async def test_authenticate_success(self, async_session):
        repo = UserRepository(async_session)
        await _create_test_user(repo)

        user = await repo.authenticate_user("testuser", "TestPass123!")
        assert user is not None
        assert user.username == "testuser"
        assert user.failed_login_attempts == 0
        assert user.last_login is not None

    async def test_authenticate_wrong_password(self, async_session):
        repo = UserRepository(async_session)
        await _create_test_user(repo)

        user = await repo.authenticate_user("testuser", "WrongPass!")
        assert user is None

    async def test_authenticate_nonexistent_user(self, async_session):
        repo = UserRepository(async_session)
        user = await repo.authenticate_user("noone", "whatever")
        assert user is None

    async def test_authenticate_inactive_user(self, async_session):
        repo = UserRepository(async_session)
        await _create_test_user(repo, is_active=False)

        user = await repo.authenticate_user("testuser", "TestPass123!")
        assert user is None


@pytest.mark.unit
@pytest.mark.auth
class TestUserRepositoryPassword:
    async def test_change_password(self, async_session):
        repo = UserRepository(async_session)
        created = await _create_test_user(repo)

        success = await repo.change_password(str(created.id), "NewPass456!")
        assert success is True

        # Expire cache so re-query reads fresh DB state
        async_session.expire_all()

        # Old password should no longer work
        user = await repo.authenticate_user("testuser", "TestPass123!")
        assert user is None

        # New password should work
        user = await repo.authenticate_user("testuser", "NewPass456!")
        assert user is not None

    async def test_change_password_nonexistent(self, async_session):
        repo = UserRepository(async_session)
        success = await repo.change_password(str(uuid.uuid4()), "Whatever1!")
        assert success is False


@pytest.mark.unit
@pytest.mark.auth
class TestUserRepositoryLock:
    async def test_lock_user_account_temporary(self, async_session):
        repo = UserRepository(async_session)
        created = await _create_test_user(repo)

        success = await repo.lock_user_account(str(created.id), duration_minutes=30)
        assert success is True

        # Refresh the ORM object from DB after bulk UPDATE
        await async_session.refresh(created)
        assert created.is_active is True
        assert created.locked_until is not None

    async def test_lock_user_account_permanent(self, async_session):
        repo = UserRepository(async_session)
        created = await _create_test_user(repo)

        success = await repo.lock_user_account(str(created.id))
        assert success is True

        await async_session.refresh(created)
        assert created.is_active is False

    async def test_lock_nonexistent_returns_false(self, async_session):
        repo = UserRepository(async_session)
        success = await repo.lock_user_account(str(uuid.uuid4()))
        assert success is False

    async def test_unlock_user_account(self, async_session):
        repo = UserRepository(async_session)
        created = await _create_test_user(repo)

        await repo.lock_user_account(str(created.id))
        success = await repo.unlock_user_account(str(created.id))
        assert success is True

        refreshed = await repo.get_user_by_id(str(created.id))
        assert refreshed.is_active is True
        assert refreshed.locked_until is None
        assert refreshed.failed_login_attempts == 0

    async def test_unlock_nonexistent_returns_false(self, async_session):
        repo = UserRepository(async_session)
        success = await repo.unlock_user_account(str(uuid.uuid4()))
        assert success is False


@pytest.mark.unit
@pytest.mark.auth
class TestUserRepositoryFailedLogin:
    async def test_increment_failed_login(self, async_session):
        repo = UserRepository(async_session)
        await _create_test_user(repo)

        count = await repo.increment_failed_login("testuser")
        assert count == 1

        count = await repo.increment_failed_login("testuser")
        assert count == 2

    async def test_increment_failed_login_nonexistent(self, async_session):
        repo = UserRepository(async_session)
        count = await repo.increment_failed_login("noone")
        assert count == 0

    async def test_auto_lock_after_max_attempts(self, async_session):
        repo = UserRepository(async_session)
        await _create_test_user(repo)

        for i in range(SecurityConfig.MAX_LOGIN_ATTEMPTS):
            count = await repo.increment_failed_login("testuser")

        assert count == SecurityConfig.MAX_LOGIN_ATTEMPTS

        # User should now be locked (temporarily)
        user = await repo.get_user_by_username("testuser")
        assert user.locked_until is not None


@pytest.mark.unit
@pytest.mark.auth
class TestUserRepositoryList:
    async def test_get_users_empty(self, async_session):
        repo = UserRepository(async_session)
        users = await repo.get_users()
        assert users == []

    async def test_get_users(self, async_session):
        repo = UserRepository(async_session)
        await _create_test_user(repo, username="user1", email="u1@example.com")
        await _create_test_user(repo, username="user2", email="u2@example.com")

        users = await repo.get_users()
        assert len(users) == 2

    async def test_get_users_with_role_filter(self, async_session):
        repo = UserRepository(async_session)
        await _create_test_user(repo, username="admin1", email="a@example.com", role=UserRole.ADMIN)
        await _create_test_user(repo, username="viewer1", email="v@example.com", role=UserRole.VIEWER)

        admins = await repo.get_users(role=UserRole.ADMIN)
        assert len(admins) == 1
        assert admins[0].username == "admin1"

    async def test_get_users_with_active_filter(self, async_session):
        repo = UserRepository(async_session)
        await _create_test_user(repo, username="active1", email="a@example.com")
        await _create_test_user(repo, username="inactive1", email="i@example.com", is_active=False)

        active = await repo.get_users(is_active=True)
        assert len(active) == 1
        assert active[0].username == "active1"

    async def test_get_users_pagination(self, async_session):
        repo = UserRepository(async_session)
        for i in range(5):
            await _create_test_user(repo, username=f"user{i}", email=f"u{i}@example.com")

        page = await repo.get_users(skip=0, limit=2)
        assert len(page) == 2


@pytest.mark.unit
@pytest.mark.auth
class TestUserRepositoryPermission:
    async def test_admin_has_all_permissions(self, async_session):
        repo = UserRepository(async_session)
        user = await _create_test_user(repo, role=UserRole.ADMIN)

        assert await UserRepository.user_has_permission(user, Permission.SYSTEM_CONFIG) is True
        assert await UserRepository.user_has_permission(user, Permission.USER_DELETE) is True

    async def test_viewer_limited_permissions(self, async_session):
        repo = UserRepository(async_session)
        user = await _create_test_user(repo, role=UserRole.VIEWER)

        assert await UserRepository.user_has_permission(user, Permission.FARM_VIEW) is True
        assert await UserRepository.user_has_permission(user, Permission.SYSTEM_CONFIG) is False
        assert await UserRepository.user_has_permission(user, Permission.USER_DELETE) is False

    async def test_operator_permissions(self, async_session):
        repo = UserRepository(async_session)
        user = await _create_test_user(repo, role=UserRole.OPERATOR)

        assert await UserRepository.user_has_permission(user, Permission.DEVICE_CONTROL) is True
        assert await UserRepository.user_has_permission(user, Permission.DEVICE_DELETE) is False


# ===========================================================================
# SessionRepository
# ===========================================================================


@pytest.mark.unit
@pytest.mark.auth
class TestSessionRepository:
    async def test_create_session(self, async_session):
        user_repo = UserRepository(async_session)
        user = await _create_test_user(user_repo)

        session_repo = SessionRepository(async_session)
        sess = await session_repo.create_session(
            user_id=str(user.id),
            session_token="tok-abc-123",
            ip_address="192.168.1.1",
            user_agent="TestAgent/1.0",
        )

        assert sess.id is not None
        assert sess.session_token == "tok-abc-123"
        assert sess.is_active is True
        assert sess.expires_at > datetime.utcnow()

    async def test_update_session_activity(self, async_session):
        user_repo = UserRepository(async_session)
        user = await _create_test_user(user_repo)

        session_repo = SessionRepository(async_session)
        await session_repo.create_session(
            user_id=str(user.id),
            session_token="tok-xyz",
            ip_address="10.0.0.1",
            user_agent="Agent",
        )

        result = await session_repo.update_session_activity("tok-xyz")
        assert result is True

    async def test_update_session_activity_not_found(self, async_session):
        session_repo = SessionRepository(async_session)
        result = await session_repo.update_session_activity("nonexistent")
        assert result is False

    async def test_revoke_session(self, async_session):
        user_repo = UserRepository(async_session)
        user = await _create_test_user(user_repo)

        session_repo = SessionRepository(async_session)
        await session_repo.create_session(
            user_id=str(user.id),
            session_token="tok-revoke",
            ip_address="10.0.0.1",
            user_agent="Agent",
        )

        result = await session_repo.revoke_session("tok-revoke", str(user.id))
        assert result is True

    async def test_revoke_session_not_found(self, async_session):
        session_repo = SessionRepository(async_session)
        result = await session_repo.revoke_session("nonexistent")
        assert result is False

    async def test_revoke_user_sessions(self, async_session):
        user_repo = UserRepository(async_session)
        user = await _create_test_user(user_repo)

        session_repo = SessionRepository(async_session)
        for i in range(3):
            await session_repo.create_session(
                user_id=str(user.id),
                session_token=f"tok-{i}",
                ip_address="10.0.0.1",
                user_agent="Agent",
            )

        revoked = await session_repo.revoke_user_sessions(str(user.id))
        assert revoked == 3

    async def test_revoke_user_sessions_except_one(self, async_session):
        user_repo = UserRepository(async_session)
        user = await _create_test_user(user_repo)

        session_repo = SessionRepository(async_session)
        for i in range(3):
            await session_repo.create_session(
                user_id=str(user.id),
                session_token=f"tok-{i}",
                ip_address="10.0.0.1",
                user_agent="Agent",
            )

        revoked = await session_repo.revoke_user_sessions(str(user.id), except_session="tok-1")
        assert revoked == 2

    async def test_cleanup_expired_sessions(self, async_session):
        user_repo = UserRepository(async_session)
        user = await _create_test_user(user_repo)

        session_repo = SessionRepository(async_session)

        # Create an expired session by directly setting expires_at
        from src.auth.models import UserSession
        expired_sess = UserSession(
            user_id=user.id,
            session_token="tok-expired",
            ip_address="10.0.0.1",
            user_agent="Agent",
            expires_at=datetime.utcnow() - timedelta(hours=1),
            is_active=True,
        )
        async_session.add(expired_sess)
        await async_session.commit()

        cleaned = await session_repo.cleanup_expired_sessions()
        assert cleaned == 1


# ===========================================================================
# LoginAttemptRepository
# ===========================================================================


@pytest.mark.unit
@pytest.mark.auth
class TestLoginAttemptRepository:
    async def test_log_login_attempt_success(self, async_session):
        repo = LoginAttemptRepository(async_session)
        attempt = await repo.log_login_attempt(
            username="testuser",
            success=True,
            ip_address="192.168.1.1",
            user_agent="TestAgent/1.0",
        )

        assert attempt.id is not None
        assert attempt.username == "testuser"
        assert attempt.success is True

    async def test_log_login_attempt_failure(self, async_session):
        repo = LoginAttemptRepository(async_session)
        attempt = await repo.log_login_attempt(
            username="testuser",
            success=False,
            ip_address="192.168.1.1",
            failure_reason="invalid_credentials",
        )

        assert attempt.success is False
        assert attempt.failure_reason == "invalid_credentials"

    async def test_get_recent_attempts(self, async_session):
        repo = LoginAttemptRepository(async_session)
        for i in range(3):
            await repo.log_login_attempt(
                username="testuser",
                success=(i == 2),
                ip_address="192.168.1.1",
            )

        attempts = await repo.get_recent_attempts()
        assert len(attempts) == 3

    async def test_get_recent_attempts_by_username(self, async_session):
        repo = LoginAttemptRepository(async_session)
        await repo.log_login_attempt(username="alice", success=True, ip_address="1.1.1.1")
        await repo.log_login_attempt(username="bob", success=False, ip_address="2.2.2.2")
        await repo.log_login_attempt(username="alice", success=False, ip_address="1.1.1.1")

        alice_attempts = await repo.get_recent_attempts(username="alice")
        assert len(alice_attempts) == 2

    async def test_get_recent_attempts_by_ip(self, async_session):
        repo = LoginAttemptRepository(async_session)
        await repo.log_login_attempt(username="alice", success=True, ip_address="10.0.0.1")
        await repo.log_login_attempt(username="bob", success=False, ip_address="10.0.0.2")

        attempts = await repo.get_recent_attempts(ip_address="10.0.0.1")
        assert len(attempts) == 1


# ===========================================================================
# APIKeyRepository
# ===========================================================================


@pytest.mark.unit
@pytest.mark.auth
class TestAPIKeyRepository:
    async def test_create_api_key(self, async_session):
        user_repo = UserRepository(async_session)
        user = await _create_test_user(user_repo)

        repo = APIKeyRepository(async_session)
        api_key = await repo.create_api_key(
            name="Test Key",
            key_hash=get_password_hash("bsf_testprefix_secretpart"),
            key_prefix="testprefix",
            created_by=str(user.id),
            permissions=["data:view"],
        )

        assert api_key.id is not None
        assert api_key.name == "Test Key"
        assert api_key.key_prefix == "testprefix"
        assert api_key.is_active is True

    async def test_get_api_key_by_prefix(self, async_session):
        user_repo = UserRepository(async_session)
        user = await _create_test_user(user_repo)

        repo = APIKeyRepository(async_session)
        await repo.create_api_key(
            name="Key1",
            key_hash=get_password_hash("whatever"),
            key_prefix="pfx123",
            created_by=str(user.id),
        )

        found = await repo.get_api_key_by_prefix("pfx123")
        assert found is not None
        assert found.name == "Key1"

    async def test_get_api_key_by_prefix_not_found(self, async_session):
        repo = APIKeyRepository(async_session)
        found = await repo.get_api_key_by_prefix("nosuchprefix")
        assert found is None

    async def test_revoke_api_key(self, async_session):
        user_repo = UserRepository(async_session)
        user = await _create_test_user(user_repo)

        repo = APIKeyRepository(async_session)
        api_key = await repo.create_api_key(
            name="To Revoke",
            key_hash=get_password_hash("whatever"),
            key_prefix="rev123",
            created_by=str(user.id),
        )

        result = await repo.revoke_api_key(str(api_key.id))
        assert result is True

        # After revoking, it should not be findable by prefix (is_active=False)
        found = await repo.get_api_key_by_prefix("rev123")
        assert found is None

    async def test_revoke_api_key_not_found(self, async_session):
        repo = APIKeyRepository(async_session)
        result = await repo.revoke_api_key(str(uuid.uuid4()))
        assert result is False

    async def test_get_user_api_keys(self, async_session):
        user_repo = UserRepository(async_session)
        user = await _create_test_user(user_repo)

        repo = APIKeyRepository(async_session)
        await repo.create_api_key(
            name="Key A",
            key_hash=get_password_hash("a"),
            key_prefix="pfxA",
            created_by=str(user.id),
        )
        await repo.create_api_key(
            name="Key B",
            key_hash=get_password_hash("b"),
            key_prefix="pfxB",
            created_by=str(user.id),
        )

        keys = await repo.get_user_api_keys(str(user.id))
        assert len(keys) == 2

    async def test_get_user_api_keys_empty(self, async_session):
        repo = APIKeyRepository(async_session)
        keys = await repo.get_user_api_keys(str(uuid.uuid4()))
        assert keys == []
