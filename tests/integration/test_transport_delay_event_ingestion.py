"""S1: exercise the actual event HTTP route and its persistence boundary.

Schema-rejection cases work without a server or a database. The positive case
uses only an explicitly configured, migrated TEST_DATABASE_URL; it writes and
cleans up events in a fresh scope, never in a development/production database.
"""

from __future__ import annotations

import hashlib
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from logistics_backend.api.errors import install_handlers
from logistics_backend.bootstrap import CredentialGrant, Settings, create_app, schema_app
from logistics_backend.persistence.event_models import events
from logistics_domain.states import ActorRole, RuntimeMode

pytestmark = pytest.mark.integration

TOKEN = "s1-event-ingestion-test-token"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


def _grant() -> CredentialGrant:
    return CredentialGrant(
        actor_id=uuid4(),
        role=ActorRole.OPERATOR,
        token_sha256=hashlib.sha256(TOKEN.encode()).hexdigest(),
    )


def _event() -> dict:
    task_id = str(uuid4())
    return {
        "schema_version": "2.0.0",
        "source": "s1-ingestion-test",
        "source_event_id": f"s1-{uuid4()}",
        "kind": "transport_delay",
        "occurred_at_utc": "2026-01-01T00:00:00Z",
        "simulation_id": None,
        "payload": {
            "kind": "transport_delay",
            "entity_ref": {"kind": "transport_task", "id": task_id, "revision": None},
            "effective_at_s": 0,
            "reason": "vehicle held at gate",
            "transport_task_id": task_id,
            "additional_seconds": 60,
        },
    }


@pytest.fixture
def schema_client():
    """Run the real routing/auth/schema layer; no database service is installed."""
    app = schema_app()
    app.state.settings = SimpleNamespace(scope_id=uuid4(), credentials=(_grant(),))
    app.state.events = object()  # Invalid envelopes must be rejected before service.ingest.
    install_handlers(app)
    with TestClient(app) as client:
        yield client


def test_health_route_has_api_prefix(schema_client: TestClient):
    response = schema_client.get("/api/v1/health")
    assert response.status_code == 200, response.text
    assert response.json()["schema_version"] == "2.0.0"
    assert schema_client.get("/health").status_code == 404


def test_vehicle_delay_cannot_enter_through_http(schema_client: TestClient):
    request = _event()
    request["kind"] = "vehicle_delay"
    request["payload"]["kind"] = "vehicle_delay"
    response = schema_client.post("/api/v1/events", json=request, headers=AUTH)
    assert response.status_code == 422, response.text
    assert response.json()["code"] == "invalid_input"


def test_payload_discriminator_must_match_event_kind(schema_client: TestClient):
    request = _event()
    request["payload"]["kind"] = "vehicle_delay"
    response = schema_client.post("/api/v1/events", json=request, headers=AUTH)
    assert response.status_code == 422, response.text
    assert response.json()["code"] == "invalid_input"


@pytest.mark.requires_postgres
def test_transport_delay_post_get_and_database_round_trip(database_url: str):
    """A real EventService, PostgreSQL transaction, HTTP POST and GET are all used."""
    settings = Settings(
        mode=RuntimeMode.TEST,
        database_url=database_url,
        scope_id=uuid4(),
        credentials=(_grant(),),
    )
    app = create_app(settings)
    request = _event()

    with TestClient(app) as client:
        try:
            unauthenticated = client.post("/api/v1/events", json=request)
            assert unauthenticated.status_code == 401, unauthenticated.text

            inserted = client.post("/api/v1/events", json=request, headers=AUTH)
            assert inserted.status_code == 202, inserted.text
            receipt = inserted.json()
            event_id = UUID(receipt["event_id"])
            assert receipt["status"] == "received"
            assert receipt["duplicate"] is False
            assert receipt["sequence"] >= 1

            loaded = client.get(f"/api/v1/events/{event_id}", headers=AUTH)
            assert loaded.status_code == 200, loaded.text
            view = loaded.json()
            assert view["event_id"] == receipt["event_id"]
            assert view["kind"] == "transport_delay"
            assert view["status"] == "received"
            assert view["source_event_id"] == request["source_event_id"]
            assert view["sequence"] == receipt["sequence"]

            with app.state.engine.connect() as connection:
                persisted = (
                    connection.execute(
                        select(events.c.kind, events.c.payload, events.c.source_event_id).where(
                            events.c.id == event_id, events.c.scope_id == settings.scope_id
                        )
                    )
                    .mappings()
                    .one()
                )
            assert persisted["kind"] == "transport_delay"
            assert persisted["source_event_id"] == request["source_event_id"]
            assert persisted["payload"]["transport_task_id"] == request["payload"]["transport_task_id"]
            assert persisted["payload"]["additional_seconds"] == 60

            replay = client.post("/api/v1/events", json=request, headers=AUTH)
            assert replay.status_code == 202, replay.text
            assert replay.json()["duplicate"] is True
            assert replay.json()["event_id"] == receipt["event_id"]

            invalid = _event()
            invalid["payload"]["additional_seconds"] = 0
            rejected = client.post("/api/v1/events", json=invalid, headers=AUTH)
            assert rejected.status_code == 422, rejected.text
            assert rejected.json()["code"] == "invalid_input"

            with app.state.engine.connect() as connection:
                rows = (
                    connection.execute(select(events.c.source_event_id).where(events.c.scope_id == settings.scope_id))
                    .scalars()
                    .all()
                )
            assert rows == [request["source_event_id"]], "invalid/replayed events must not create rows"
        finally:
            # The random scope belongs only to this test; no other rows are touched.
            with app.state.engine.begin() as connection:
                connection.execute(delete(events).where(events.c.scope_id == settings.scope_id))
