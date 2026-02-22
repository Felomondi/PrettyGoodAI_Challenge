import os


def get_active_patient() -> dict | None:
    """Return patient identity from environment variables."""
    name = os.getenv("PATIENT_FULL_NAME", "").strip()
    dob = os.getenv("PATIENT_DOB", "").strip()
    phone = os.getenv("TWILIO_FROM_NUMBER", "").strip()
    if not name or not dob:
        return None
    return {"full_name": name, "dob": dob, "phone": phone}
