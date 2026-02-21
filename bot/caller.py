import os
from twilio.rest import Client
import db.client as db
from bot.conversation_manager import manager
from scenarios.patient_scenarios import PatientScenario

TARGET_NUMBER = os.getenv("TARGET_PHONE_NUMBER", "+18054398008")
FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "")


def place_call(
    scenario: PatientScenario,
    webhook_base_url: str,
    patient: dict | None = None,
) -> str:
    """
    Place an outbound call for the given scenario.
    If patient is not provided, looks up by TWILIO_FROM_NUMBER.
    Returns the Twilio CallSid.
    """
    if patient is None:
        patient = db.get_patient_by_phone(FROM_NUMBER)
        if not patient:
            raise ValueError(
                f"No patient registered for {FROM_NUMBER}. "
                "Visit http://localhost:5000/register to register a patient."
            )

    twilio_client = Client(
        os.getenv("TWILIO_ACCOUNT_SID"),
        os.getenv("TWILIO_AUTH_TOKEN"),
    )

    call = twilio_client.calls.create(
        to=TARGET_NUMBER,
        from_=FROM_NUMBER,
        url=f"{webhook_base_url}/voice",
        status_callback=f"{webhook_base_url}/status",
        status_callback_method="POST",
    )

    manager.create_session(call.sid, scenario, patient)
    print(f"[caller] Call placed — SID: {call.sid} | Scenario: {scenario.name}")
    return call.sid
