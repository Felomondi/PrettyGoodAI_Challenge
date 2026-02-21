from twilio.twiml.voice_response import VoiceResponse, Gather

VOICE = "Polly.Joanna"
LANGUAGE = "en-US"

_GATHER_KWARGS = dict(
    input="speech",
    action="/gather",
    method="POST",
    speech_timeout="auto",
    speech_model="phone_call",
    enhanced="true",
    timeout=8,
)


def build_listen_response() -> str:
    """
    Called the moment the outbound call connects.
    Say nothing — just open a Gather so we can hear Athena's opening greeting.
    """
    response = VoiceResponse()
    gather = Gather(**_GATHER_KWARGS)
    response.append(gather)
    response.redirect("/gather_timeout", method="POST")
    return str(response)


def build_gather_response(patient_text: str, action: str = "/gather") -> str:
    """Speak patient_text then listen for the agent's reply."""
    response = VoiceResponse()
    response.say(patient_text, voice=VOICE, language=LANGUAGE)
    gather = Gather(**{**_GATHER_KWARGS, "action": action})
    response.append(gather)
    # Fallback if Gather times out with no speech detected
    response.redirect("/gather_timeout", method="POST")
    return str(response)


def build_hangup_response(patient_text: str = "") -> str:
    """Optionally say a farewell then hang up."""
    response = VoiceResponse()
    if patient_text:
        response.say(patient_text, voice=VOICE, language=LANGUAGE)
    response.hangup()
    return str(response)


def build_retry_response(patient_text: str) -> str:
    """Re-prompt the agent when no speech was detected."""
    return build_gather_response(patient_text)
