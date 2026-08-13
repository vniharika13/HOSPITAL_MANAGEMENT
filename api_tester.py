#!/usr/bin/env python3
"""
smoke/integration tester for the Hospital Appointment API.

Usage:
    python api_tester.py http://127.0.0.1:8000

Optional:
    python api_tester.py http://127.0.0.1:8000 --timeout 5
"""
from __future__ import annotations

import argparse
import sys
import uuid
from datetime import datetime, timedelta, timezone

import requests


def fail(message: str) -> None:
    print(f"FAIL  {message}")


def ok(message: str) -> None:
    print(f"PASS  {message}")


def get_id(data):
    if isinstance(data, dict):
        if "id" in data:
            return data["id"]
        for key in ("patient", "doctor", "appointment", "data"):
            if isinstance(data.get(key), dict) and "id" in data[key]:
                return data[key]["id"]
    raise AssertionError(f"Could not find an id in response: {data!r}")


def expect(response, allowed=(200, 201), label="request"):
    if response.status_code not in allowed:
        raise AssertionError(
            f"{label}: HTTP {response.status_code}; response={response.text[:500]}"
        )
    return response


def main() -> int:
    parser = argparse.ArgumentParser(description="Test Hospital Appointment API")
    parser.add_argument("base_url", help="API base URL, e.g. http://127.0.0.1:8000")
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    session = requests.Session()
    tag = uuid.uuid4().hex[:8]

    patient = {"name": f"Test Patient {tag}", "email": f"test-{tag}@example.com", "phone": "9999999999"}
    doctor = {"name": f"Test Doctor {tag}", "specialization": "General Medicine"}

    start = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(days=1)
    end = start + timedelta(minutes=30)
    overlap_start = start + timedelta(minutes=10)
    overlap_end = end + timedelta(minutes=20)

    print(f"Testing {base}\n")

    try:
        # Patient
        r = session.get(f"{base}/patients", timeout=args.timeout)
        expect(r, (200,), "GET /patients")
        ok("GET /patients")
        patient_list = r.json()
        if not isinstance(patient_list, list):
            raise AssertionError("GET /patients should return a JSON list")

        r = session.post(f"{base}/patients", json=patient, timeout=args.timeout)
        expect(r, (200, 201), "POST /patients")
        patient_id = get_id(r.json())
        ok("POST /patients")

        r = session.get(f"{base}/patients/{patient_id}", timeout=args.timeout)
        expect(r, (200,), "GET /patients/{id}")
        ok("GET /patients/{id}")

        # Doctor
        r = session.get(f"{base}/doctors", timeout=args.timeout)
        expect(r, (200,), "GET /doctors")
        ok("GET /doctors")

        r = session.post(f"{base}/doctors", json=doctor, timeout=args.timeout)
        expect(r, (200, 201), "POST /doctors")
        doctor_id = get_id(r.json())
        ok("POST /doctors")

        r = session.get(f"{base}/doctors/{doctor_id}", timeout=args.timeout)
        expect(r, (200,), "GET /doctors/{id}")
        ok("GET /doctors/{id}")

        # Appointment
        appointment = {
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "appointment_start": start.isoformat(),
            "appointment_end": end.isoformat(),
        }

        r = session.get(f"{base}/appointments", timeout=args.timeout)
        expect(r, (200,), "GET /appointments")
        ok("GET /appointments")

        r = session.post(f"{base}/appointments", json=appointment, timeout=args.timeout)
        expect(r, (200, 201), "POST /appointments")
        appointment_id = get_id(r.json())
        ok("POST /appointments")

        r = session.get(f"{base}/appointments/{appointment_id}", timeout=args.timeout)
        expect(r, (200,), "GET /appointments/{id}")
        ok("GET /appointments/{id}")

        # Business rule: overlapping appointment for the same doctor must fail.
        overlapping = {
            **appointment,
            "appointment_start": overlap_start.isoformat(),
            "appointment_end": overlap_end.isoformat(),
        }
        r = session.post(
            f"{base}/appointments", json=overlapping, timeout=args.timeout
        )
        if r.status_code < 400:
            raise AssertionError(
                "Overlapping appointment was accepted; expected a 4xx response"
            )
        ok("Overlapping appointment is rejected")

        print("\nAll API checks passed.")
        return 0

    except (requests.RequestException, AssertionError, ValueError) as exc:
        fail(str(exc))
        print("\nAPI checks failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
