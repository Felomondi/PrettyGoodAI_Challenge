import os
from twilio.rest import Client
from bot.conversation_manager import manager
from scenarios.patient_scenarios import PatientScenario

TARGET_NUMBER = os.getenv("TARGET_PHONE_NUMBER", "+18054398008")
FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "")


def place_call(scenario: PatientScenario, webhook_base_url: str, patient: dict) -> str:
    """Place an outbound call for the given scenario. Returns the Twilio CallSid."""
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
