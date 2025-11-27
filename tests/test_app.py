"""
Tests for the Mergington High School API
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app, activities

# Create test client
client = TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to initial state before each test"""
    # Store original state
    original_activities = {
        k: {
            "description": v["description"],
            "schedule": v["schedule"],
            "max_participants": v["max_participants"],
            "participants": v["participants"].copy()
        }
        for k, v in activities.items()
    }
    
    yield
    
    # Restore original state
    for activity_name, activity_data in original_activities.items():
        activities[activity_name]["participants"] = activity_data["participants"].copy()


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities(self, reset_activities):
        """Test retrieving all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert len(data) == 9
    
    def test_get_activities_contains_required_fields(self, reset_activities):
        """Test that activities contain required fields"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_data in data.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_for_activity_success(self, reset_activities):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": "newtestuser@mergington.edu"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "Signed up" in data["message"]
        
        # Verify participant was added
        assert "newtestuser@mergington.edu" in activities["Chess Club"]["participants"]
    
    def test_signup_for_nonexistent_activity(self, reset_activities):
        """Test signup for a non-existent activity"""
        response = client.post(
            "/activities/Nonexistent Club/signup",
            params={"email": "test@mergington.edu"}
        )
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Activity not found"
    
    def test_duplicate_signup(self, reset_activities):
        """Test that duplicate signups are prevented"""
        # Try to sign up someone already registered
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": "michael@mergington.edu"}
        )
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"]
    
    def test_multiple_signups(self, reset_activities):
        """Test multiple different students can sign up"""
        emails = ["test1@mergington.edu", "test2@mergington.edu", "test3@mergington.edu"]
        
        for email in emails:
            response = client.post(
                "/activities/Gym Class/signup",
                params={"email": email}
            )
            assert response.status_code == 200
        
        # Verify all were added
        for email in emails:
            assert email in activities["Gym Class"]["participants"]


class TestUnregisterFromActivity:
    """Tests for DELETE /activities/{activity_name}/signup endpoint"""
    
    def test_unregister_success(self, reset_activities):
        """Test successful unregistration from an activity"""
        # Verify student is registered
        assert "michael@mergington.edu" in activities["Chess Club"]["participants"]
        
        # Unregister
        response = client.delete(
            "/activities/Chess Club/signup",
            params={"email": "michael@mergington.edu"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "Unregistered" in data["message"]
        
        # Verify participant was removed
        assert "michael@mergington.edu" not in activities["Chess Club"]["participants"]
    
    def test_unregister_from_nonexistent_activity(self, reset_activities):
        """Test unregister from a non-existent activity"""
        response = client.delete(
            "/activities/Nonexistent Club/signup",
            params={"email": "test@mergington.edu"}
        )
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Activity not found"
    
    def test_unregister_not_registered_student(self, reset_activities):
        """Test unregister for a student not registered"""
        response = client.delete(
            "/activities/Chess Club/signup",
            params={"email": "notregistered@mergington.edu"}
        )
        assert response.status_code == 400
        data = response.json()
        assert "not signed up" in data["detail"]
    
    def test_unregister_multiple_participants(self, reset_activities):
        """Test unregistering one participant doesn't affect others"""
        original_count = len(activities["Chess Club"]["participants"])
        
        response = client.delete(
            "/activities/Chess Club/signup",
            params={"email": "michael@mergington.edu"}
        )
        assert response.status_code == 200
        
        # Verify correct number of participants remains
        assert len(activities["Chess Club"]["participants"]) == original_count - 1
        # Verify other participant is still there
        assert "daniel@mergington.edu" in activities["Chess Club"]["participants"]


class TestIntegration:
    """Integration tests for complete workflows"""
    
    def test_signup_and_unregister_workflow(self, reset_activities):
        """Test complete signup and unregister workflow"""
        email = "integration@mergington.edu"
        activity = "Tennis Club"
        
        # Sign up
        response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response.status_code == 200
        assert email in activities[activity]["participants"]
        
        # Get activities to verify
        response = client.get("/activities")
        data = response.json()
        assert email in data[activity]["participants"]
        
        # Unregister
        response = client.delete(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response.status_code == 200
        assert email not in activities[activity]["participants"]
        
        # Get activities to verify removal
        response = client.get("/activities")
        data = response.json()
        assert email not in data[activity]["participants"]
