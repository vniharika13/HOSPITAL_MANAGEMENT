from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.schemas.appointment import AppointmentCreate, AppointmentResponse

router = APIRouter()


@router.get("", response_model=list[AppointmentResponse])
async def get_appointments(db: Session = Depends(get_db)):
    return db.query(Appointment).all()


@router.post(
    "",
    response_model=AppointmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_appointment(
    appointment: AppointmentCreate,
    db: Session = Depends(get_db),
):
    patient = (
        db.query(Patient)
        .filter(Patient.id == appointment.patient_id)
        .first()
    )
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    doctor = (
        db.query(Doctor)
        .filter(Doctor.id == appointment.doctor_id)
        .first()
    )
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    if appointment.appointment_start >= appointment.appointment_end:
        raise HTTPException(
            status_code=400,
            detail="Appointment end must be after start",
        )

    overlapping = (
        db.query(Appointment)
        .filter(Appointment.doctor_id == appointment.doctor_id)
        .filter(Appointment.appointment_start < appointment.appointment_end)
        .filter(Appointment.appointment_end > appointment.appointment_start)
        .first()
    )
    if overlapping:
        raise HTTPException(
            status_code=409,
            detail=(
                "Appointment overlaps with an existing booking for this "
                "doctor"
            ),
        )

    new_appointment = Appointment(**appointment.model_dump())
    db.add(new_appointment)
    db.commit()
    db.refresh(new_appointment)
    return new_appointment


@router.get("/{appointment_id}", response_model=AppointmentResponse)
async def get_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
):
    appointment = (
        db.query(Appointment)
        .filter(Appointment.id == appointment_id)
        .first()
    )
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appointment
