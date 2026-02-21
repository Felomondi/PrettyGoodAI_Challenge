import os
import json
from datetime import datetime

TRANSCRIPTS_DIR = "transcripts"


def save_transcript(call_sid: str, session_info: dict, history: list[dict]) -> tuple[str, str]:
    """
    Save the conversation transcript as both a human-readable .txt and a
    machine-readable .json. Also persists the call record to Supabase.
    Returns (txt_path, json_path).
    """
    os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)

    scenario_id = session_info.get("scenario_id", "unknown")
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    base_name = f"{scenario_id}_{timestamp}"

    # ── Plain text (human-readable, for repo submission) ─────────────────────
    txt_path = os.path.join(TRANSCRIPTS_DIR, f"{base_name}.txt")
    with open(txt_path, "w") as f:
        f.write(f"CALL:     {session_info.get('scenario_name', 'Unknown')}\n")
        f.write(f"PATIENT:  {session_info.get('patient_name', 'Unknown')}\n")
        f.write(f"DATE:     {datetime.utcnow().isoformat()}Z\n")
        f.write(f"CALL SID: {call_sid}\n")
        f.write(f"DURATION: {session_info.get('elapsed_seconds', 0)}s\n")
        f.write(f"TURNS:    {session_info.get('turn_count', 0)}\n")
        f.write("\n--- TRANSCRIPT ---\n\n")
        for turn in history:
            label = "[PATIENT]" if turn["role"] == "patient" else "[AGENT]  "
            f.write(f"{label} {turn['text']}\n\n")
        f.write("--- END TRANSCRIPT ---\n")

    # ── JSON (for bug analysis) ───────────────────────────────────────────────
    json_path = os.path.join(TRANSCRIPTS_DIR, f"{base_name}.json")
    with open(json_path, "w") as f:
        json.dump(
            {
                "call_sid": call_sid,
                "scenario_id": scenario_id,
                "scenario_name": session_info.get("scenario_name"),
                "patient_name": session_info.get("patient_name"),
                "timestamp": datetime.utcnow().isoformat(),
                "elapsed_seconds": session_info.get("elapsed_seconds", 0),
                "turn_count": session_info.get("turn_count", 0),
                "transcript": history,
            },
            f,
            indent=2,
        )

    print(f"[transcript] Saved → {txt_path}")

    # ── Persist to Supabase ───────────────────────────────────────────────────
    try:
        import db.client as db
        db.save_call(call_sid, session_info, history, txt_path=txt_path)
        print(f"[transcript] Synced to Supabase → calls/{scenario_id}")
    except Exception as e:
        print(f"[transcript] Supabase sync failed (local files still saved): {e}")

    return txt_path, json_path
