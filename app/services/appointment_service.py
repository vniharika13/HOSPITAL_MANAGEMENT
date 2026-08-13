from datetime import datetime

from sqlalchemy.orm import Session

from app.models.appointment import Appointment


class AppointmentService:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> list[Appointment]:
        return self.db.query(Appointment).all()

    def get_by_id(self, appointment_id: int) -> Appointment | None:
        return (
            self.db.query(Appointment)
            .filter(Appointment.id == appointment_id)
            .first()
        )

    def create(
        self,
        patient_id: int,
        doctor_id: int,
        appointment_start: datetime,
        appointment_end: datetime,
    ) -> Appointment:
        appointment = Appointment(
            patient_id=patient_id,
            doctor_id=doctor_id,
            appointment_start=appointment_start,
            appointment_end=appointment_end,
        )
        self.db.add(appointment)
        self.db.commit()
        self.db.refresh(appointment)
        return appointment

    def delete(self, appointment_id: int) -> bool:
        appointment = self.get_by_id(appointment_id)
        if not appointment:
            return False
        self.db.delete(appointment)
        self.db.commit()
        return True
