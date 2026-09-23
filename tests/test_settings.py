import pytest

from app.services.business_settings_service import business_settings_service


@pytest.mark.asyncio
async def test_settings_created_with_defaults(db_session):
    settings = await business_settings_service.get_settings(db_session)
    assert settings.id == 1
    assert settings.name == "Bowling SaaS"


@pytest.mark.asyncio
async def test_settings_endpoint_public_get(db_session, client):
    res = await client.get("/api/v1/settings")
    assert res.status_code == 200
    body = res.json()
    assert body["id"] == 1
    assert body["name"] == "Bowling SaaS"
    assert body["address"] == "Calle 123, Centro Ciudad"


@pytest.mark.asyncio
async def test_update_settings_requires_staff(db_session, client):
    from app.core.security import create_access_token
    from app.models.user import User

    user = User(email="plain-settings@example.com", hashed_password="pw", full_name="Plain User")
    db_session.add(user)
    await db_session.commit()

    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    res = await client.put("/api/v1/settings", json={"name": "Hacked"}, headers=headers)
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_update_settings_endpoint(db_session, client):
    from app.core.security import create_access_token
    from app.models.user import User
    from app.models.enums import UserRole

    owner = User(email="owner-settings@example.com", hashed_password="pw", full_name="Owner Settings", role=UserRole.OWNER)
    db_session.add(owner)
    await db_session.commit()

    token = create_access_token({"sub": str(owner.id)})
    headers = {"Authorization": f"Bearer {token}"}

    res = await client.put(
        "/api/v1/settings",
        json={"name": "Strike Center", "address": "Av. Libertador 500", "phone": "+58 412 555 8899"},
        headers=headers,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["name"] == "Strike Center"
    assert body["address"] == "Av. Libertador 500"
    assert body["phone"] == "+58 412 555 8899"

    res = await client.get("/api/v1/settings")
    body = res.json()
    assert body["name"] == "Strike Center"