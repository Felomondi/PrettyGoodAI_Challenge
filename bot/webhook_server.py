import copy
import os
import re
import time
import threading

from flask import Flask, jsonify, request, render_template, redirect, url_for, Response

from bot.twiml_builder import build_gather_response, build_hangup_response, build_listen_response, build_retry_response
from bot.conversation_manager import manager
from bot.llm_patient import generate_patient_response
from analysis.transcript_store import save_transcript
import db.client as db

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "..", "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "..", "static"),
)

MAX_TURNS = int(os.getenv("MAX_TURNS_PER_CALL", "15"))
MAX_EMPTY = 5


# ── Simulation state ──────────────────────────────────────────────────────────

_public_url: str = ""
_sim_lock = threading.Lock()
_sim_state: dict = {
    "status": "idle",   # idle | running | complete | error
    "patient_name": "",
    "total": 0,
    "completed": 0,
    "calls": [],
}


def set_public_url(url: str) -> None:
    global _public_url
    _public_url = url


def _run_simulation(patient: dict, scenarios=None) -> None:
    """Background thread: run scenarios sequentially then analyze.

    Pass a list of PatientScenario objects to run a subset; defaults to all.
    """
    from scenarios.patient_scenarios import ALL_SCENARIOS
    from bot.caller import place_call
    from analysis.bug_analyzer import analyze_transcripts

    if scenarios is None:
        scenarios = ALL_SCENARIOS

    total = len(scenarios)
    spacing = int(os.getenv("CALLS_SPACING_SECONDS", "90"))

    with _sim_lock:
        _sim_state.update({
            "status": "running",
            "patient_name": patient["full_name"],
            "total": total,
            "completed": 0,
            "calls": [
                {
                    "scenario_name": s.name,
                    "scenario_id": s.id,
                    "status": "pending",
                    "call_sid": None,
                }
                for s in scenarios
            ],
        })

    for i, scenario in enumerate(scenarios):
        sid = None
        try:
            sid = place_call(scenario, _public_url, patient=patient)
            with _sim_lock:
                _sim_state["calls"][i]["status"] = "in_progress"
                _sim_state["calls"][i]["call_sid"] = sid
            print(f"[sim] [{i + 1}/{total}] {scenario.name}")
        except Exception as e:
            print(f"[sim] Failed: {scenario.name}: {e}")
            with _sim_lock:
                _sim_state["calls"][i]["status"] = "error"
                _sim_state["completed"] = i + 1
            continue

        # Wait until the call finishes OR the spacing window expires
        deadline = time.time() + spacing
        while time.time() < deadline:
            if manager.is_complete(sid):
                break
            time.sleep(3)

        with _sim_lock:
            if _sim_state["calls"][i]["status"] == "in_progress":
                _sim_state["calls"][i]["status"] = "complete"
            _sim_state["completed"] = i + 1

    # Post-call bug analysis
    print("[sim] Running bug analysis…")
    try:
        analyze_transcripts()
    except Exception as e:
        print(f"[sim] Analysis error: {e}")

    with _sim_lock:
        _sim_state["status"] = "complete"

    print("[sim] All done! Check outputs/bug_report.md")


# ── Twilio webhook routes ─────────────────────────────────────────────────────

@app.route("/voice", methods=["POST"])
def voice() -> Response:
    """Called the moment our outbound call connects. Athena speaks first — just listen."""
    call_sid = request.form.get("CallSid", "")
    session = manager.get_session(call_sid)

    if not session:
        return Response(
            build_hangup_response("I'm sorry, something went wrong. Goodbye."),
            content_type="text/xml",
        )

    # Don't speak — open a Gather so Athena's greeting is transcribed
    return Response(build_listen_response(), content_type="text/xml")


@app.route("/gather", methods=["POST"])
def gather() -> Response:
    call_sid = request.form.get("CallSid", "")
    speech_result = (request.form.get("SpeechResult") or "").strip()

    session = manager.get_session(call_sid)
    if not session:
        return Response(build_hangup_response("Goodbye."), content_type="text/xml")

    if not speech_result:
        session["consecutive_empty"] += 1
        if session["consecutive_empty"] >= MAX_EMPTY:
            _finalize(call_sid)
            return Response(
                build_hangup_response("I'm having trouble hearing you. Goodbye."),
                content_type="text/xml",
            )
        return Response(
            build_retry_response("Hello? I'm sorry, I didn't catch that. Could you repeat?"),
            content_type="text/xml",
        )

    # Record what the agent just said
    manager.add_turn(call_sid, "agent", speech_result)

    if session["turn_count"] >= MAX_TURNS:
        farewell = "Thank you so much for your help. I'll call back if I need anything. Goodbye."
        manager.add_turn(call_sid, "patient", farewell)
        _finalize(call_sid)
        return Response(build_hangup_response(farewell), content_type="text/xml")

    patient_reply, is_complete = generate_patient_response(
        session["scenario"],
        session["patient"],
        session["history"],
        speech_result,
    )

    # Empty reply = agent said something a human stays silent through (e.g. a
    # recording disclosure after identity verification).  Just keep listening.
    if not patient_reply:
        return Response(build_listen_response(), content_type="text/xml")

    manager.add_turn(call_sid, "patient", patient_reply)

    if is_complete:
        _finalize(call_sid)
        return Response(build_hangup_response(patient_reply), content_type="text/xml")

    return Response(build_gather_response(patient_reply), content_type="text/xml")


@app.route("/gather_timeout", methods=["POST"])
def gather_timeout() -> Response:
    call_sid = request.form.get("CallSid", "")
    session = manager.get_session(call_sid)

    if not session:
        return Response(build_hangup_response("Goodbye."), content_type="text/xml")

    session["consecutive_empty"] += 1
    if session["consecutive_empty"] >= MAX_EMPTY:
        _finalize(call_sid)
        return Response(
            build_hangup_response("I'll try calling again later. Goodbye."),
            content_type="text/xml",
        )

    return Response(
        build_retry_response("Hello? Are you still there?"),
        content_type="text/xml",
    )


@app.route("/status", methods=["POST"])
def status() -> tuple[str, int]:
    call_sid = request.form.get("CallSid", "")
    call_status = request.form.get("CallStatus", "")

    if call_status == "completed" and call_sid:
        session = manager.get_session(call_sid)
        if session and not session.get("is_complete"):
            _finalize(call_sid)

    return "", 204


def _finalize(call_sid: str) -> None:
    if not manager.is_complete(call_sid):
        manager.mark_complete(call_sid)
        session_info = manager.get_session_info(call_sid)
        history = manager.get_transcript(call_sid)
        if history:
            save_transcript(call_sid, session_info, history)


# ── Registration & UI routes ──────────────────────────────────────────────────

@app.route("/")
def index():
    from scenarios.patient_scenarios import ALL_SCENARIOS
    patient = _get_active_patient()
    return render_template("index.html", patient=patient, scenarios=ALL_SCENARIOS)


@app.route("/simulate", methods=["POST"])
def simulate():
    patient = _get_active_patient()
    if not patient:
        return redirect(url_for("index"))

    with _sim_lock:
        already_running = _sim_state["status"] == "running"

    if not already_running:
        t = threading.Thread(target=_run_simulation, args=(patient,), daemon=True)
        t.start()

    return redirect(url_for("progress"))


@app.route("/simulate/<scenario_id>", methods=["POST"])
def simulate_one(scenario_id: str):
    from scenarios.patient_scenarios import ALL_SCENARIOS
    patient = _get_active_patient()
    if not patient:
        return redirect(url_for("index"))

    scenario = next((s for s in ALL_SCENARIOS if s.id == scenario_id), None)
    if not scenario:
        return redirect(url_for("index"))

    with _sim_lock:
        already_running = _sim_state["status"] == "running"

    if not already_running:
        t = threading.Thread(target=_run_simulation, args=(patient, [scenario]), daemon=True)
        t.start()

    return redirect(url_for("progress"))


@app.route("/register", methods=["GET", "POST"])
def register():
    from_number = os.getenv("TWILIO_FROM_NUMBER", "")

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        dob = request.form.get("dob", "").strip()

        error = _validate_registration(full_name, email, phone, dob)
        if error:
            return render_template(
                "register.html", error=error, values=request.form, from_number=from_number
            )

        try:
            db.register_patient(full_name, email, phone, dob)
        except Exception as e:
            err = str(e).lower()
            if "unique" in err or "duplicate" in err or "already exists" in err:
                error = "A patient with that email or phone number is already registered."
            else:
                error = f"Registration failed: {e}"
            return render_template(
                "register.html", error=error, values=request.form, from_number=from_number
            )

        return redirect(url_for("index"))

    return render_template("register.html", error=None, values={}, from_number=from_number)


def _get_active_patient() -> dict | None:
    """Return the first registered patient, or None if none exist."""
    try:
        patients = db.get_all_patients()
        return patients[0] if patients else None
    except Exception:
        return None


@app.route("/progress")
def progress():
    return render_template("progress.html")


@app.route("/api/status")
def api_status():
    with _sim_lock:
        return jsonify(copy.deepcopy(_sim_state))


@app.route("/patients")
def patients():
    all_patients = db.get_all_patients()
    return render_template("patients.html", patients=all_patients)


@app.route("/patients/<int:patient_id>/delete", methods=["POST"])
def delete_patient(patient_id: int):
    db.delete_patient(patient_id)
    return redirect(url_for("patients"))


def _validate_registration(
    full_name: str, email: str, phone: str, dob: str
) -> str | None:
    if not full_name:
        return "Full name is required."
    if not email or "@" not in email:
        return "A valid email address is required."
    if not re.match(r"^\+1\d{10}$", phone):
        return "Phone must be in E.164 format: +1XXXXXXXXXX (10 digits after +1)."
    if not dob:
        return "Date of birth is required."
    return None
