#!/usr/bin/env python
"""
Test Local de Todas las Herramientas del Agente de Calendario
Ejecuta pruebas de: Create, List, Postpone, Delete
"""

import requests
import json
import time
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def print_test_header(test_name):
    print(f"\n{'='*60}")
    print(f"  TEST: {test_name}")
    print(f"{'='*60}\n")

def print_result(success, message):
    status = "[PASSED]" if success else "[FAILED]"
    print(f"{status}: {message}\n")

def test_health_check():
    print_test_header("Health Check")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        result = response.json()
        success = response.status_code == 200 and result.get("status") == "API is running"
        print_result(success, f"Health check response: {result}")
        return success
    except Exception as e:
        print_result(False, f"Error: {e}")
        return False

def test_create_event():
    print_test_header("Create Event")
    try:
        payload = {
            "user_input": "Create an event titled 'Test Event - Create' on January 26, 2026 at 10:00 AM for 2 hours"
        }
        response = requests.post(f"{BASE_URL}/invoke", json=payload, timeout=TIMEOUT)
        result = response.json()

        success = (
            response.status_code == 200 and
            result.get("status") == "success" and
            "Test Event - Create" in result.get("result", "")
        )

        print(f"Response: {result.get('result', 'No result')[:200]}")
        print_result(success, "Event created successfully" if success else "Failed to create event")
        return success
    except Exception as e:
        print_result(False, f"Error: {e}")
        return False

def test_list_events():
    print_test_header("List Events")
    try:
        payload = {
            "user_input": "List all events from January 25 to January 27, 2026"
        }
        response = requests.post(f"{BASE_URL}/invoke", json=payload, timeout=TIMEOUT)
        result = response.json()

        success = response.status_code == 200 and result.get("status") == "success"

        print(f"Response: {result.get('result', 'No result')[:300]}")
        print_result(success, "Events listed successfully" if success else "Failed to list events")
        return success
    except Exception as e:
        print_result(False, f"Error: {e}")
        return False

def test_postpone_event():
    print_test_header("Postpone Event")
    try:
        # First, create an event to postpone
        create_payload = {
            "user_input": "Create an event titled 'Test Event - Postpone' on January 26, 2026 at 3:00 PM for 1 hour"
        }
        requests.post(f"{BASE_URL}/invoke", json=create_payload, timeout=TIMEOUT)
        time.sleep(2)  # Wait a bit

        # Now postpone it
        postpone_payload = {
            "user_input": "Postpone the 'Test Event - Postpone' event from January 26 at 3 PM to January 27 at 4 PM"
        }
        response = requests.post(f"{BASE_URL}/invoke", json=postpone_payload, timeout=TIMEOUT)
        result = response.json()

        success = response.status_code == 200 and result.get("status") == "success"

        print(f"Response: {result.get('result', 'No result')[:300]}")
        print_result(success, "Event postponed successfully" if success else "Failed to postpone event")
        return success
    except Exception as e:
        print_result(False, f"Error: {e}")
        return False

def test_delete_event():
    print_test_header("Delete Event")
    try:
        # First, create an event to delete
        create_payload = {
            "user_input": "Create an event titled 'Test Event - Delete' on January 26, 2026 at 5:00 PM for 1 hour"
        }
        requests.post(f"{BASE_URL}/invoke", json=create_payload, timeout=TIMEOUT)
        time.sleep(2)  # Wait a bit

        # Now delete it
        delete_payload = {
            "user_input": "Delete the 'Test Event - Delete' event on January 26 at 5 PM"
        }
        response = requests.post(f"{BASE_URL}/invoke", json=delete_payload, timeout=TIMEOUT)
        result = response.json()

        success = response.status_code == 200 and result.get("status") == "success"

        print(f"Response: {result.get('result', 'No result')[:300]}")
        print_result(success, "Event deleted successfully" if success else "Failed to delete event")
        return success
    except Exception as e:
        print_result(False, f"Error: {e}")
        return False

def main():
    print("\n" + "="*60)
    print("  SUITE DE TESTS LOCAL - AGENTE DE CALENDARIO")
    print("  Zona Horaria: America/Tijuana (Pacific Time)")
    print("="*60)

    results = {
        "Health Check": test_health_check(),
        "Create Event": test_create_event(),
        "List Events": test_list_events(),
        "Postpone Event": test_postpone_event(),
        "Delete Event": test_delete_event(),
    }

    # Summary
    print("\n" + "="*60)
    print("  RESUMEN DE RESULTADOS")
    print("="*60)

    total = len(results)
    passed = sum(results.values())

    for test_name, result in results.items():
        status = "[PASSED]" if result else "[FAILED]"
        print(f"{status}: {test_name}")

    print(f"\n{'='*60}")
    print(f"  TOTAL: {passed}/{total} tests pasaron ({passed/total*100:.1f}%)")
    print(f"{'='*60}\n")

    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
