from datetime import datetime

_job_status = {
    "running": False,
    "message": "Idle",
    "progress": 0,
    "total": 0,
    "phase": "",
    "started_at": None,
}

def set_status(running: bool, message: str, phase: str = "", progress: int = 0, total: int = 0):
    _job_status["running"] = running
    _job_status["message"] = message
    _job_status["phase"] = phase
    _job_status["progress"] = progress
    _job_status["total"] = total
    if running and not _job_status["started_at"]:
        _job_status["started_at"] = datetime.now().isoformat()
    if not running:
        _job_status["started_at"] = None

def get_status() -> dict:
    return {**_job_status}
