import requests

def test_health_check_endpoint_returns_api_status():
    base_url = "http://localhost:8000"
    url = f"{base_url}/health"
    headers = {
        "Accept": "application/json"
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        assert isinstance(data, dict), "Response is not a JSON object"
        assert "status" in data, "'status' key not found in response JSON"
        assert data["status"] == "API is running", f"Unexpected status message: {data['status']}"
    except requests.RequestException as e:
        assert False, f"Request to /health endpoint failed: {e}"

test_health_check_endpoint_returns_api_status()