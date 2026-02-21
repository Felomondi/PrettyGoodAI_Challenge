import os
from supabase import create_client, Client

_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env")
        _client = create_client(url, key)
    return _client


# ── Patients ──────────────────────────────────────────────────────────────────

def register_patient(full_name: str, email: str, phone: str, dob: str) -> dict:
    res = get_client().table("patients").insert({
        "full_name": full_name,
        "email": email,
        "phone": phone,
        "dob": dob,
    }).execute()
    return res.data[0]


def get_patient_by_phone(phone: str) -> dict | None:
    res = (
        get_client()
        .table("patients")
        .select("*")
        .eq("phone", phone)
        .maybe_single()
        .execute()
    )
    return res.data


def get_all_patients() -> list[dict]:
    res = (
        get_client()
        .table("patients")
        .select("*")
        .order("created_at")
        .execute()
    )
    return res.data


def delete_patient(patient_id: int) -> None:
    get_client().table("patients").delete().eq("id", patient_id).execute()


# ── Calls ─────────────────────────────────────────────────────────────────────

def save_call(
    call_sid: str,
    session_info: dict,
    transcript: list[dict],
    txt_path: str | None = None,
    patient_id: int | None = None,
) -> dict:
    """Upsert a completed call record into the calls table."""
    res = (
        get_client()
        .table("calls")
        .upsert({
            "call_sid": call_sid,
            "scenario_id": session_info.get("scenario_id", "unknown"),
            "scenario_name": session_info.get("scenario_name", ""),
            "patient_name": session_info.get("patient_name", ""),
            "patient_id": patient_id,
            "elapsed_seconds": session_info.get("elapsed_seconds", 0),
            "turn_count": session_info.get("turn_count", 0),
            "transcript": transcript,
            "txt_path": txt_path,
        }, on_conflict="call_sid")
        .execute()
    )
    return res.data[0] if res.data else {}


def get_all_calls() -> list[dict]:
    res = (
        get_client()
        .table("calls")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )
    return res.data


# ── Bugs ──────────────────────────────────────────────────────────────────────

def save_bugs(bugs: list[dict]) -> None:
    """Insert a batch of bug records (skips empty lists)."""
    if not bugs:
        return
    get_client().table("bugs").insert(bugs).execute()


def get_all_bugs() -> list[dict]:
    res = (
        get_client()
        .table("bugs")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )
    return res.data
