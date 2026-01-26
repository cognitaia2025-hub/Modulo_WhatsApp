import requests
import datetime
import time

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def test_create_calendar_event_with_required_and_optional_parameters():
    # Prepare event data
    now = datetime.datetime.utcnow()
    start_datetime = (now + datetime.timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%S")
    end_datetime = (now + datetime.timedelta(minutes=31)).strftime("%Y-%m-%dT%H:%M:%S")
    summary = "Test Event TC003"
    location = "Sala de reunión virtual"
    description = "Este evento se crea como parte de la prueba automatizada TC003."

    # Construct natural language user input in Spanish, as per PRD
    user_input = (
        f"Crea un evento que empiece el {start_datetime} y termine el {end_datetime} "
        f"titulado '{summary}', en la ubicación '{location}' y con descripción '{description}'."
    )

    headers = {"Content-Type": "application/json"}

    # Create the event by invoking the calendar agent
    response = requests.post(
        f"{BASE_URL}/invoke",
        json={"user_input": user_input},
        headers=headers,
        timeout=TIMEOUT,
    )
    try:
        response.raise_for_status()
    except Exception as e:
        raise AssertionError(f"HTTP request failed: {e}")

    data = response.json()

    # Validate response structure and content
    assert "status" in data, "Response missing 'status' field"
    assert data["status"] == "success", f"Unexpected status: {data['status']}"
    assert "result" in data, "Response missing 'result' field"
    result = data["result"]

    # Check that result is a string containing confirmation message with event link
    assert isinstance(result, str), f"Expected 'result' to be string, got {type(result)}"
    assert summary in result, f"Event summary '{summary}' not found in confirmation message"
    assert "http" in result.lower(), "Event link not found in confirmation message"

    # Cleanup - delete the created event to avoid clutter
    user_query = (
        f"Elimina el evento titulado '{summary}' que empieza el {start_datetime} y termina el {end_datetime}."
    )
    try:
        cleanup_response = requests.post(
            f"{BASE_URL}/invoke",
            json={"user_input": user_query},
            headers=headers,
            timeout=TIMEOUT,
        )
        cleanup_response.raise_for_status()
        cleanup_data = cleanup_response.json()
        assert cleanup_data.get("status") == "success", "Failed to delete the test event in cleanup"
    except Exception as cleanup_exc:
        print(f"Cleanup failed: {cleanup_exc}")


test_create_calendar_event_with_required_and_optional_parameters()
