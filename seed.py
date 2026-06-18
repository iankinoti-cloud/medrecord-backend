import asyncio
import bcrypt
import sys
import os
from datetime import date

sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.user import User
from app.models.patient import Patient


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


STAFF = [
    {
        "full_name": "Ian Kinoti",
        "email": "ian.kinoti@student.moringaschool.com",
        "role": "Admin",
    },
    {
        "full_name": "Erika Gwiyo",
        "email": "erika.gwiyo@student.moringaschool.com",
        "role": "Doctor",
    },
    {
        "full_name": "Jane Nyasoro",
        "email": "jane.nyasoro@student.moringaschool.com",
        "role": "LabTechnician",
    },
    {
        "full_name": "Jason Mumo",
        "email": "jason.mumo@student.moringaschool.com",
        "role": "Admin",
    },
]

PATIENTS = [
    {
        "patient_id": "P-00001",
        "full_name": "Alice Mwangi",
        "date_of_birth": date(1985, 3, 14),
        "gender": "Female",
        "blood_type": "A+",
        "contact_phone": "+254712345678",
        "contact_email": "alice.mwangi@email.com",
        "address": "Nairobi, Kenya",
        "emergency_contact": "James Mwangi +254722345678",
        "status": "Active",
    },
    {
        "patient_id": "P-00002",
        "full_name": "Brian Otieno",
        "date_of_birth": date(1990, 7, 22),
        "gender": "Male",
        "blood_type": "O+",
        "contact_phone": "+254723456789",
        "contact_email": "brian.otieno@email.com",
        "address": "Kisumu, Kenya",
        "emergency_contact": "Mary Otieno +254733456789",
        "status": "Active",
    },
    {
        "patient_id": "P-00003",
        "full_name": "Catherine Njeri",
        "date_of_birth": date(1978, 11, 5),
        "gender": "Female",
        "blood_type": "B-",
        "contact_phone": "+254734567890",
        "contact_email": "catherine.njeri@email.com",
        "address": "Mombasa, Kenya",
        "emergency_contact": "Peter Njeri +254744567890",
        "status": "Active",
    },
    {
        "patient_id": "P-00004",
        "full_name": "David Kamau",
        "date_of_birth": date(2001, 1, 30),
        "gender": "Male",
        "blood_type": "AB+",
        "contact_phone": "+254745678901",
        "contact_email": "david.kamau@email.com",
        "address": "Nakuru, Kenya",
        "emergency_contact": "Grace Kamau +254755678901",
        "status": "Active",
    },
    {
        "patient_id": "P-00005",
        "full_name": "Esther Wanjiku",
        "date_of_birth": date(1965, 6, 18),
        "gender": "Female",
        "blood_type": "O-",
        "contact_phone": "+254756789012",
        "contact_email": "esther.wanjiku@email.com",
        "address": "Eldoret, Kenya",
        "emergency_contact": "Samuel Wanjiku +254766789012",
        "status": "Admitted",
    },
]


async def seed():
    async with AsyncSessionLocal() as db:
        # Staff accounts
        for member in STAFF:
            exists = await db.scalar(select(User).where(User.email == member["email"]))
            if exists:
                print(f"  ~ skip (exists) {member['full_name']}")
                continue
            user = User(
                full_name=member["full_name"],
                email=member["email"],
                password_hash=hash_password("MedRecord2024!"),
                role=member["role"],
                is_active=True,
            )
            db.add(user)
            print(f"  + {member['role']:15s} {member['full_name']} ({member['email']})")

        await db.flush()

        # Patients
        for p in PATIENTS:
            exists = await db.scalar(select(Patient).where(Patient.patient_id == p["patient_id"]))
            if exists:
                print(f"  ~ skip (exists) {p['patient_id']}")
                continue
            patient = Patient(**p)
            db.add(patient)
            print(f"  + Patient      {p['patient_id']} — {p['full_name']}")

        await db.commit()
        print("\nAll done. Default password for all staff: MedRecord2024!")


asyncio.run(seed())
