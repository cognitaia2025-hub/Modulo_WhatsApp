import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def test_invoke_calendar_agent_with_natural_language_request():
    url = f"{BASE_URL}/invoke"
    headers = {
        'Content-Type': 'application/json',
    }
    payloads = [
        # create event request example
        {"user_input": "Crea una reunión mañana a las 9 am sobre el proyecto X"},
        # list events example
        {"user_input": "Muéstrame los eventos del próximo lunes a viernes"},
        # postpone event example
        {"user_input": "Pospone la reunión del martes a las 3 pm para el jueves a las 4 pm"},
        # delete event example
        {"user_input": "Elimina la reunión con Juan de mañana"},
    ]

    for payload in payloads:
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=TIMEOUT)
        except requests.RequestException as e:
            assert False, f"Request to /invoke failed: {e}"

        assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
        
        try:
            resp_json = response.json()
        except ValueError:
            assert False, "Response is not valid JSON"

        assert "status" in resp_json, "'status' field missing in response JSON"
        assert resp_json["status"] == "success", f"Expected status 'success', got '{resp_json['status']}'"
        assert "result" in resp_json, "'result' field missing in response JSON"
        assert isinstance(resp_json["result"], dict), "'result' field is not an object/dict"

test_invoke_calendar_agent_with_natural_language_request()