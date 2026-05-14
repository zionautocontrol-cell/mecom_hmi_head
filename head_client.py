import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

from config import (
    API_KEY,
    HEAD_ENABLED,
    HEAD_SERVER_URL,
    HISTORY_CSV,
    REALTIME_JSON,
    SITE_ID,
)

logger = logging.getLogger("head_client")

_previous_alarms: set = set()


def send_daily_report() -> bool:
    if not HEAD_ENABLED:
        return False
    if not HISTORY_CSV.exists():
        logger.warning("No history CSV found.")
        return False
    try:
        url = f"{HEAD_SERVER_URL}/api/daily-report"
        files = {"file": ("history.csv", HISTORY_CSV.read_bytes(), "text/csv")}
        resp = requests.post(url, files=files, headers={"X-API-Key": API_KEY, "X-Site-ID": SITE_ID}, timeout=30)
        if resp.status_code == 200:
            logger.info("Daily report sent successfully.")
            return True
        logger.warning(f"Daily report failed: {resp.status_code} {resp.text}")
    except requests.RequestException as e:
        logger.error(f"Daily report error: {e}")
    return False


def send_alarm(alarm_type: str, alarm_id: str, message: str, severity: str, value: float) -> bool:
    if not HEAD_ENABLED:
        return False
    key = (alarm_type, alarm_id)
    if key in _previous_alarms:
        return False
    _previous_alarms.add(key)
    try:
        payload = {
            "site_id": SITE_ID,
            "alarm_type": alarm_type,
            "alarm_id": alarm_id,
            "message": message,
            "severity": severity,
            "value": value,
            "timestamp": datetime.now().isoformat(),
        }
        resp = requests.post(
            f"{HEAD_SERVER_URL}/api/alarm",
            json=payload,
            headers={"X-API-Key": API_KEY, "X-Site-ID": SITE_ID},
            timeout=10,
        )
        if resp.status_code == 200:
            logger.info(f"Alarm sent: {alarm_id} {message}")
            return True
        logger.warning(f"Alarm send failed: {resp.status_code}")
    except requests.RequestException as e:
        logger.error(f"Alarm send error: {e}")
    return False


def send_realtime(words: list, bits: list, accum_heat: float) -> bool:
    if not HEAD_ENABLED:
        return False
    try:
        payload = {
            "site_id": SITE_ID,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "connected",
            "bits": bits[:38],
            "words": words[:11],
            "accum_heat": accum_heat,
        }
        resp = requests.post(
            f"{HEAD_SERVER_URL}/api/realtime",
            json=payload,
            headers={"X-API-Key": API_KEY, "X-Site-ID": SITE_ID},
            timeout=5,
        )
        return resp.status_code == 200
    except requests.RequestException:
        return False
