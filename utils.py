import json
import os
from typing import List

from session import Session


def save_sessions_to_file(sessions: List[Session]):
    with open("sessions.json", "w", encoding="utf-8") as f:
        sessions_dict = [
            session.to_dict() for session in sessions
            if session.user_id != -1
        ]
        json.dump(sessions_dict, f, indent=4, ensure_ascii=False)


def load_sessions_for_file() -> List[Session]:
    if os.path.exists("sessions.json"):
        with open("sessions.json", "r", encoding="utf-8") as f:
            sessions_dict = json.load(f)
            return [Session(source_dict=session_dict) for session_dict in sessions_dict]
    else:
        return []
