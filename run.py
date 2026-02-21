#!/usr/bin/env python3
"""
PrettyGoodAI Voice Bot

Usage:
  python run.py

Starts the server and opens the registration form.
Fill in the patient details — calls start automatically on submit.
"""
import os
from dotenv import load_dotenv

load_dotenv()

PORT = int(os.getenv("PORT", "5000"))


def main() -> None:
    from bot.ngrok_manager import start_and_configure
    import bot.webhook_server as ws

    # Start ngrok tunnel and point Twilio webhook at it
    public_url = start_and_configure(PORT)
    ws.set_public_url(public_url)

    print(f"\n[run] Ready → http://localhost:{PORT}/register")
    print("[run] Fill out the registration form to begin the call simulation.\n")

    from bot.webhook_server import app
    app.run(host="0.0.0.0", port=PORT, use_reloader=False, threaded=True)


if __name__ == "__main__":
    main()
