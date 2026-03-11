import copy
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from src import app as app_module


@pytest.fixture
def client():
    return TestClient(app_module.app)


@pytest.fixture(autouse=True)
def restore_activities_state():
    original = copy.deepcopy(app_module.activities)
    yield
    app_module.activities.clear()
    app_module.activities.update(original)


def test_root_redirects_to_static_index(client):
    # Arrange + Act
    response = client.get("/", follow_redirects=False)

    # Assert
    assert response.status_code in (302, 307)
    assert response.headers["location"] == "/static/index.html"


def test_get_activities_returns_expected_shape(client):
    # Arrange + Act
    response = client.get("/activities")

    # Assert
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, dict)
    assert len(payload) > 0

    for details in payload.values():
        assert {"description", "schedule", "max_participants", "participants"}.issubset(details.keys())
        assert isinstance(details["participants"], list)


def test_signup_success_adds_participant(client):
    # Arrange
    activity_name = "Chess Club"
    encoded_activity = quote(activity_name, safe="")
    email = "newstudent@mergington.edu"

    # Act
    response = client.post(f"/activities/{encoded_activity}/signup", params={"email": email})

    # Assert
    assert response.status_code == 200
    assert response.json()["message"] == f"Signed up {email} for {activity_name}"
    assert email in app_module.activities[activity_name]["participants"]


def test_signup_fails_for_missing_activity(client):
    # Arrange + Act
    response = client.post(
        f"/activities/{quote('Unknown Club', safe='')}/signup",
        params={"email": "student@mergington.edu"},
    )

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_signup_fails_for_duplicate_email(client):
    # Arrange
    activity_name = "Chess Club"
    encoded_activity = quote(activity_name, safe="")
    existing_email = app_module.activities[activity_name]["participants"][0]

    # Act
    response = client.post(f"/activities/{encoded_activity}/signup", params={"email": existing_email})

    # Assert
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already signed up for this activity"


def test_unregister_success_removes_participant(client):
    # Arrange
    activity_name = "Chess Club"
    encoded_activity = quote(activity_name, safe="")
    email = app_module.activities[activity_name]["participants"][0]

    # Act
    response = client.delete(f"/activities/{encoded_activity}/participants", params={"email": email})

    # Assert
    assert response.status_code == 200
    assert response.json()["message"] == f"Unregistered {email} from {activity_name}"
    assert email not in app_module.activities[activity_name]["participants"]


def test_unregister_fails_for_missing_activity(client):
    # Arrange + Act
    response = client.delete(
        f"/activities/{quote('Unknown Club', safe='')}/participants",
        params={"email": "student@mergington.edu"},
    )

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_unregister_fails_for_missing_participant(client):
    # Arrange
    activity_name = "Chess Club"
    encoded_activity = quote(activity_name, safe="")

    # Act
    response = client.delete(
        f"/activities/{encoded_activity}/participants",
        params={"email": "not-registered@mergington.edu"},
    )

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Participant not found for this activity"
