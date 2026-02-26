import pytest
from app.models.user import User
from app.repositories.user_repository import user_repository

@pytest.mark.asyncio
async def test_base_repository_get_multi(db_session):
    # Create some dummy users directly in DB
    user1 = User(email="user1@example.com", hashed_password="pw", full_name="User One")
    user2 = User(email="user2@example.com", hashed_password="pw", full_name="User Two")
    db_session.add(user1)
    db_session.add(user2)
    await db_session.commit()

    # Use the repository's get_multi (since it inherits from BaseRepository)
    users = await user_repository.get_multi(db_session, limit=10)
    assert len(users) >= 2
    assert any(u.email == "user1@example.com" for u in users)
    assert any(u.email == "user2@example.com" for u in users)
