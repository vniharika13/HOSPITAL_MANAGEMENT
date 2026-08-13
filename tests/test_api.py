from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.services.appointment_service import AppointmentService

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_hospital.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


@pytest.fixture
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_create_and_get_patient(client):
    response = client.post(
        "/api/v1/patients",
        json={
            "name": "Alice Johnson",
            "email": "alice@example.com",
            "phone": "1234567890",
        },
    )
    assert response.status_code == 201
    patient = response.json()
    assert patient["name"] == "Alice Johnson"

    response = client.get(f"/api/v1/patients/{patient['id']}")
    assert response.status_code == 200
    assert response.json()["email"] == "alice@example.com"


def test_create_and_get_doctor(client):
    response = client.post(
        "/api/v1/doctors",
        json={
            "name": "Dr. Smith",
            "specialization": "Cardiology",
        },
    )
    assert response.status_code == 201
    doctor = response.json()
    assert doctor["specialization"] == "Cardiology"

    response = client.get(f"/api/v1/doctors/{doctor['id']}")
    assert response.status_code == 200
    assert response.json()["name"] == "Dr. Smith"


def test_create_appointment_successfully(client):
    patient = client.post(
        "/api/v1/patients",
        json={
            "name": "Bob",
            "email": "bob@example.com",
            "phone": "1111111111",
        },
    ).json()
    doctor = client.post(
        "/api/v1/doctors",
        json={"name": "Dr. White", "specialization": "Neurology"},
    ).json()

    start = datetime(2026, 1, 10, 9, 0, 0)
    end = datetime(2026, 1, 10, 10, 0, 0)

    response = client.post(
        "/api/v1/appointments",
        json={
            "patient_id": patient["id"],
            "doctor_id": doctor["id"],
            "appointment_start": start.isoformat(),
            "appointment_end": end.isoformat(),
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["patient_id"] == patient["id"]
    assert data["doctor_id"] == doctor["id"]


def test_reject_overlapping_appointments(client):
    patient = client.post(
        "/api/v1/patients",
        json={
            "name": "Carol",
            "email": "carol@example.com",
            "phone": "2222222222",
        },
    ).json()
    doctor = client.post(
        "/api/v1/doctors",
        json={"name": "Dr. Brown", "specialization": "Dermatology"},
    ).json()

    first_start = datetime(2026, 2, 10, 14, 0, 0)
    first_end = datetime(2026, 2, 10, 15, 0, 0)
    second_start = datetime(2026, 2, 10, 14, 30, 0)
    second_end = datetime(2026, 2, 10, 15, 30, 0)

    first = client.post(
        "/api/v1/appointments",
        json={
            "patient_id": patient["id"],
            "doctor_id": doctor["id"],
            "appointment_start": first_start.isoformat(),
            "appointment_end": first_end.isoformat(),
        },
    )
    assert first.status_code == 201

    second = client.post(
        "/api/v1/appointments",
        json={
            "patient_id": patient["id"],
            "doctor_id": doctor["id"],
            "appointment_start": second_start.isoformat(),
            "appointment_end": second_end.isoformat(),
        },
    )
    assert second.status_code == 409
    assert "overlap" in second.json()["detail"].lower()


def test_get_all_endpoints_and_missing_resources(client):
    client.post(
        "/api/v1/patients",
        json={
            "name": "Dana",
            "email": "dana@example.com",
            "phone": "3333333333",
        },
    )
    client.post(
        "/api/v1/doctors",
        json={
            "name": "Dr. Green",
            "specialization": "Pediatrics",
        },
    )

    patients = client.get("/api/v1/patients")
    doctors = client.get("/api/v1/doctors")
    appointments = client.get("/api/v1/appointments")

    assert patients.status_code == 200
    assert doctors.status_code == 200
    assert appointments.status_code == 200

    missing_patient = client.get("/api/v1/patients/999")
    missing_doctor = client.get("/api/v1/doctors/999")
    missing_appointment = client.get("/api/v1/appointments/999")

    assert missing_patient.status_code == 404
    assert missing_doctor.status_code == 404
    assert missing_appointment.status_code == 404


def test_appointment_service_crud_and_db_dependency():
    db = TestingSessionLocal()
    patient = Patient(name="Eve", email="eve@example.com", phone="444")
    doctor = Doctor(name="Dr. King", specialization="Oncology")
    db.add_all([patient, doctor])
    db.commit()
    db.refresh(patient)
    db.refresh(doctor)

    service = AppointmentService(db)
    start = datetime(2026, 3, 1, 8, 0, 0)

    appointment = service.create(
        patient.id,
        doctor.id,
        start,
        start.replace(hour=start.hour + 1),
    )
    assert appointment.patient_id == patient.id
    assert service.get_by_id(appointment.id).id == appointment.id
    assert len(service.get_all()) == 1
    assert service.delete(appointment.id) is True
    assert service.get_by_id(appointment.id) is None
    db.close()

    database_generator = get_db()
    session = next(database_generator)
    assert session is not None
    database_generator.close()
