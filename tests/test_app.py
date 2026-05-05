"""
Test suite for the Mergington High School Activities API
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to initial state between tests"""
    original_activities = {
        "Chess Club": {
            "description": "Learn strategies and compete in chess tournaments",
            "schedule": "Fridays, 3:30 PM - 5:00 PM",
            "max_participants": 12,
            "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
        },
        "Programming Class": {
            "description": "Learn programming fundamentals and build software projects",
            "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
            "max_participants": 20,
            "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
        },
        "Gym Class": {
            "description": "Physical education and sports activities",
            "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
            "max_participants": 30,
            "participants": ["john@mergington.edu", "olivia@mergington.edu"]
        },
    }

    # Arrange
    activities.clear()
    activities.update(original_activities)

    yield

    # Cleanup
    activities.clear()
    activities.update(original_activities)


class TestGetActivities:
    """Tests for GET /activities endpoint"""

    def test_get_activities_returns_all_activities(self, client, reset_activities):
        """Test that GET /activities returns all activities"""
        # Arrange
        expected_activity_names = {"Chess Club", "Programming Class", "Gym Class"}

        # Act
        response = client.get("/activities")
        data = response.json()

        # Assert
        assert response.status_code == 200
        assert expected_activity_names == set(data.keys())

    def test_get_activities_contains_required_fields(self, client, reset_activities):
        """Test that activity objects contain all required fields"""
        # Act
        response = client.get("/activities")
        data = response.json()
        activity = data["Chess Club"]

        # Assert
        assert "description" in activity
        assert "schedule" in activity
        assert "max_participants" in activity
        assert "participants" in activity

    def test_get_activities_participants_list(self, client, reset_activities):
        """Test that participants list is returned correctly"""
        # Act
        response = client.get("/activities")
        data = response.json()

        # Assert
        assert "michael@mergington.edu" in data["Chess Club"]["participants"]
        assert "daniel@mergington.edu" in data["Chess Club"]["participants"]


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""

    def test_signup_successful(self, client, reset_activities):
        """Test successful signup for an activity"""
        # Arrange
        email = "newstudent@mergington.edu"
        url = f"/activities/Chess%20Club/signup?email={email}"

        # Act
        response = client.post(url)
        data = response.json()

        # Assert
        assert response.status_code == 200
        assert "Signed up" in data["message"]
        assert email in activities["Chess Club"]["participants"]

    def test_signup_activity_not_found(self, client, reset_activities):
        """Test signup to non-existent activity"""
        # Arrange
        url = "/activities/Nonexistent%20Activity/signup?email=test@mergington.edu"

        # Act
        response = client.post(url)
        data = response.json()

        # Assert
        assert response.status_code == 404
        assert data["detail"] == "Activity not found"

    def test_signup_duplicate_student(self, client, reset_activities):
        """Test that duplicate signup is rejected"""
        # Arrange
        email = "michael@mergington.edu"
        url = f"/activities/Chess%20Club/signup?email={email}"

        # Act
        response = client.post(url)
        data = response.json()

        # Assert
        assert response.status_code == 400
        assert data["detail"] == "Student already signed up"

    def test_signup_adds_participant_to_list(self, client, reset_activities):
        """Test that signup correctly adds participant to the list"""
        # Arrange
        activity_name = "Programming Class"
        email = "new@mergington.edu"
        initial_count = len(activities[activity_name]["participants"])
        url = f"/activities/{activity_name.replace(' ', '%20')}/signup?email={email}"

        # Act
        response = client.post(url)

        # Assert
        assert response.status_code == 200
        assert len(activities[activity_name]["participants"]) == initial_count + 1
        assert email in activities[activity_name]["participants"]

    def test_signup_multiple_participants(self, client, reset_activities):
        """Test signup of multiple different participants"""
        # Arrange
        emails = ["student1@mergington.edu", "student2@mergington.edu", "student3@mergington.edu"]
        url_template = "/activities/Gym%20Class/signup?email={}"

        # Act
        for email in emails:
            response = client.post(url_template.format(email))
            assert response.status_code == 200

        # Assert
        assert all(email in activities["Gym Class"]["participants"] for email in emails)


class TestRemoveParticipant:
    """Tests for DELETE /activities/{activity_name}/participants/{email} endpoint"""

    def test_remove_participant_successful(self, client, reset_activities):
        """Test successful removal of a participant"""
        # Arrange
        url = "/activities/Chess%20Club/participants/michael@mergington.edu"

        # Act
        response = client.delete(url)
        data = response.json()

        # Assert
        assert response.status_code == 200
        assert "Removed" in data["message"]
        assert "michael@mergington.edu" not in activities["Chess Club"]["participants"]

    def test_remove_participant_activity_not_found(self, client, reset_activities):
        """Test removal from non-existent activity"""
        # Arrange
        url = "/activities/Nonexistent%20Activity/participants/test@mergington.edu"

        # Act
        response = client.delete(url)
        data = response.json()

        # Assert
        assert response.status_code == 404
        assert data["detail"] == "Activity not found"

    def test_remove_participant_not_found(self, client, reset_activities):
        """Test removal of non-existent participant"""
        # Arrange
        url = "/activities/Chess%20Club/participants/notregistered@mergington.edu"

        # Act
        response = client.delete(url)
        data = response.json()

        # Assert
        assert response.status_code == 404
        assert data["detail"] == "Participant not found"

    def test_remove_participant_decreases_count(self, client, reset_activities):
        """Test that removal decreases participant count"""
        # Arrange
        activity_name = "Programming Class"
        initial_count = len(activities[activity_name]["participants"])
        url = "/activities/Programming%20Class/participants/emma@mergington.edu"

        # Act
        response = client.delete(url)

        # Assert
        assert response.status_code == 200
        assert len(activities[activity_name]["participants"]) == initial_count - 1

    def test_remove_and_signup_same_participant(self, client, reset_activities):
        """Test removing and re-signing up a participant"""
        # Arrange
        email = "michael@mergington.edu"
        remove_url = f"/activities/Chess%20Club/participants/{email}"
        signup_url = f"/activities/Chess%20Club/signup?email={email}"

        # Act
        response1 = client.delete(remove_url)
        response2 = client.post(signup_url)

        # Assert
        assert response1.status_code == 200
        assert email not in activities["Chess Club"]["participants"]
        assert response2.status_code == 200
        assert email in activities["Chess Club"]["participants"]


class TestIntegration:
    """Integration tests combining multiple operations"""

    def test_signup_removes_duplicate_signup_error(self, client, reset_activities):
        """Test that duplicate signup is properly prevented"""
        # Arrange
        email = "test@mergington.edu"
        url = f"/activities/Chess%20Club/signup?email={email}"

        # Act
        response1 = client.post(url)
        response2 = client.post(url)

        # Assert
        assert response1.status_code == 200
        assert response2.status_code == 400

    def test_participant_count_after_operations(self, client, reset_activities):
        """Test participant count after signup and removal"""
        # Arrange
        activity_name = "Gym Class"
        email = "new@mergington.edu"
        initial_count = len(activities[activity_name]["participants"])
        signup_url = f"/activities/{activity_name.replace(' ', '%20')}/signup?email={email}"
        remove_url = f"/activities/{activity_name.replace(' ', '%20')}/participants/{email}"

        # Act
        signup_response = client.post(signup_url)
        remove_response = client.delete(remove_url)

        # Assert
        assert signup_response.status_code == 200
        assert remove_response.status_code == 200
        assert len(activities[activity_name]["participants"]) == initial_count
