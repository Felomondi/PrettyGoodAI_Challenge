import os
from pyngrok import ngrok, conf
from twilio.rest import Client


def start_and_configure(port: int) -> str:
    """
    Start an ngrok tunnel on the given port, then update the Twilio
    phone number's voice webhook to point at the new public URL.
    Returns the public HTTPS URL.
    """
    auth_token = os.getenv("NGROK_AUTH_TOKEN")
    if auth_token:
        conf.get_default().auth_token = auth_token

    tunnel = ngrok.connect(port, "http")
    public_url: str = tunnel.public_url
    if public_url.startswith("http://"):
        public_url = "https://" + public_url[len("http://"):]

    print(f"[ngrok] Tunnel active: {public_url}")

    # Update Twilio voice webhook URL so calls route here
    from_number = os.getenv("TWILIO_FROM_NUMBER")
    twilio_client = Client(
        os.getenv("TWILIO_ACCOUNT_SID"),
        os.getenv("TWILIO_AUTH_TOKEN"),
    )

    numbers = twilio_client.incoming_phone_numbers.list(phone_number=from_number)
    if numbers:
        numbers[0].update(voice_url=f"{public_url}/voice", voice_method="POST")
        print(f"[ngrok] Twilio webhook updated → {public_url}/voice")
    else:
        print(f"[ngrok] Warning: Twilio number {from_number} not found in account")

    return public_url
