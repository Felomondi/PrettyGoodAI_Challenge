import threading
from datetime import datetime
from typing import Optional


class ConversationManager:
    def __init__(self) -> None:
        self._sessions: dict[str, dict] = {}
        self._lock = threading.Lock()

    def create_session(self, call_sid: str, scenario, patient: dict) -> None:
        with self._lock:
            self._sessions[call_sid] = {
                "scenario": scenario,
                "patient": patient,
                "history": [],
                "turn_count": 0,
                "start_time": datetime.utcnow(),
                "is_complete": False,
                "consecutive_empty": 0,
            }

    def get_session(self, call_sid: str) -> Optional[dict]:
        with self._lock:
            return self._sessions.get(call_sid)

    def add_turn(self, call_sid: str, role: str, text: str) -> None:
        with self._lock:
            session = self._sessions.get(call_sid)
            if not session:
                return
            session["history"].append({"role": role, "text": text})
            if role == "agent":
                session["turn_count"] += 1
            if text.strip():
                session["consecutive_empty"] = 0
            else:
                session["consecutive_empty"] += 1

    def mark_complete(self, call_sid: str) -> None:
        with self._lock:
            session = self._sessions.get(call_sid)
            if session:
                session["is_complete"] = True

    def is_complete(self, call_sid: str) -> bool:
        with self._lock:
            session = self._sessions.get(call_sid)
            # If session doesn't exist treat as complete (already cleaned up)
            return session.get("is_complete", True) if session else True

    def get_transcript(self, call_sid: str) -> list[dict]:
        with self._lock:
            session = self._sessions.get(call_sid)
            return list(session["history"]) if session else []

    def get_session_info(self, call_sid: str) -> dict:
        with self._lock:
            session = self._sessions.get(call_sid)
            if not session:
                return {}
            elapsed = int((datetime.utcnow() - session["start_time"]).total_seconds())
            return {
                "scenario_id": session["scenario"].id,
                "scenario_name": session["scenario"].name,
                "patient_name": session["patient"]["full_name"],
                "turn_count": session["turn_count"],
                "elapsed_seconds": elapsed,
                "is_complete": session["is_complete"],
            }

    def all_complete(self, call_sids: list[str]) -> bool:
        with self._lock:
            return all(
                self._sessions.get(sid, {}).get("is_complete", True)
                for sid in call_sids
            )


# Global singleton shared across Flask routes and caller
manager = ConversationManager()
