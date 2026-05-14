import csv
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
import sqlite3
from config import DB_PATH  # config.py에 DB_PATH = BASE_DIR / "mecom.db" 추가 필요
import pandas as pd

from config import CONTROL_COMMAND_JSON, HISTORY_CSV, HISTORY_COLUMNS, REALTIME_JSON

DEFAULT_BITS = [False] * 38
DEFAULT_WORDS = [0.0] * 11
CONTROL_DEFAULT = {
    "command": "none",
    "status": "idle",
    "requested_at": "",
    "executed_at": "",
    "message": "",
}
BIT_ALARM_LABELS = {
    30: "집수정1 고수위",
    31: "집수정1 저수위",
    32: "집수정2 고수위",
    33: "집수정2 저수위",
    34: "집수정3 고수위",
    35: "집수정3 저수위",
    36: "집수정4 고수위",
    37: "집수정4 저수위",
}
WORD_LABELS = {
    0: "지중공급온도(1동)",
    1: "지중환수온도(1동)",
    2: "지중공급온도(2동)",
    3: "지중환수온도(2동)",
    4: "2차공급온도(1동)",
    5: "2차환수온도(1동)",
    6: "2차공급온도(2동)",
    7: "2차환수온도(2동)",
    8: "1동유량",
    9: "2동유량",
    10: "생산열량",
}
WORD_ALARM_RULES = {
    0: {"min": 5.0, "max": 45.0, "low": "Low ground supply temperature", "high": "High ground supply temperature", "severity": "medium"},
    1: {"min": 5.0, "max": 45.0, "low": "Low ground supply temperature", "high": "High ground supply temperature", "severity": "medium"},
    2: {"min": 5.0, "max": 45.0, "low": "Low ground return temperature", "high": "High ground return temperature", "severity": "medium"},
    3: {"min": 5.0, "max": 45.0, "low": "Low ground return temperature", "high": "High ground return temperature", "severity": "medium"},
    4: {"min": 5.0, "max": 45.0, "low": "Low secondary supply temperature", "high": "High secondary supply temperature", "severity": "medium"},
    5: {"min": 5.0, "max": 45.0, "low": "Low secondary supply temperature", "high": "High secondary supply temperature", "severity": "medium"},
    6: {"min": 5.0, "max": 45.0, "low": "Low secondary return temperature", "high": "High secondary return temperature", "severity": "medium"},
    7: {"min": 5.0, "max": 45.0, "low": "Low secondary return temperature", "high": "High secondary return temperature", "severity": "medium"},
    8: {"min": 1.0, "max": 120.0, "low": "Low flow rate", "high": "High flow rate", "severity": "high"},
    10: {"min": 0.0, "max": 1000.0, "low": "Invalid heat generation", "high": "Excessive instantaneous heat", "severity": "medium"},
}
ALARM_HISTORY_CSV = HISTORY_CSV.with_name("alarm_history.csv")
ALARM_COLUMNS = ["timestamp", "alarm_type", "alarm_id", "message", "severity", "value"]

def get_default_realtime_data() -> Dict[str, Any]:
    return {
        "status": "disconnected",
        "timestamp": "",
        "bits": [False] * 38,
        "words": [0.0] * 11,
        "accum_heat": 0.0,
    }


def _safe_list(value: Any, length: int, default: Any) -> List[Any]:
    if isinstance(value, list):
        result = value[:length]
        if len(result) < length:
            result.extend([default] * (length - len(result)))
        return result
    return [default] * length


_last_realtime_data: Optional[Dict[str, Any]] = None

def load_realtime_data() -> Dict[str, Any]:
    global _last_realtime_data

    if not REALTIME_JSON.exists():
        result = get_default_realtime_data()
        _last_realtime_data = result
        return result

    try:
        with REALTIME_JSON.open("r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        if _last_realtime_data is not None:
            return _last_realtime_data
        result = get_default_realtime_data()
        _last_realtime_data = result
        return result

    status = raw.get("status", "disconnected")
    timestamp = raw.get("timestamp", "")
    bits = _safe_list(raw.get("bits", DEFAULT_BITS.copy()), 38, False)
    words = _safe_list(raw.get("words", DEFAULT_WORDS.copy()), 11, 0.0)
    accum_heat = raw.get("accum_heat", 0.0)

    if not isinstance(accum_heat, (int, float)):
        accum_heat = 0.0

    result = {
        "status": status,
        "timestamp": timestamp,
        "bits": bits,
        "words": words,
        "accum_heat": accum_heat,
    }
    _last_realtime_data = result
    return result


def save_realtime_data(data: Dict[str, Any]) -> bool:
    try:
        temp_path = REALTIME_JSON.with_suffix(".tmp")
        with temp_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        temp_path.replace(REALTIME_JSON)
        return True
    except Exception:
        return False


def load_control_command() -> Dict[str, Any]:
    if not CONTROL_COMMAND_JSON.exists():
        return CONTROL_DEFAULT.copy()

    try:
        with CONTROL_COMMAND_JSON.open("r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        return CONTROL_DEFAULT.copy()

    result = CONTROL_DEFAULT.copy()
    result.update({k: raw.get(k, v) for k, v in CONTROL_DEFAULT.items()})
    return result


def save_control_command(
    command: Optional[str] = None,
    status: Optional[str] = None,
    message: Optional[str] = None,
    requested_at: Optional[str] = None,
    executed_at: Optional[str] = None,
) -> bool:
    current = load_control_command()
    if command is not None:
        current["command"] = command
    if status is not None:
        current["status"] = status
    if message is not None:
        current["message"] = message
    if requested_at is not None:
        current["requested_at"] = requested_at
    if executed_at is not None:
        current["executed_at"] = executed_at

    if current["requested_at"] == "" and current["command"] != "none":
        current["requested_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        temp_path = CONTROL_COMMAND_JSON.with_suffix(".tmp")
        with temp_path.open("w", encoding="utf-8") as f:
            json.dump(current, f, ensure_ascii=False, indent=2)
        temp_path.replace(CONTROL_COMMAND_JSON)
        return True
    except Exception:
        return False


def evaluate_alarms(realtime: Dict[str, Any]) -> List[Dict[str, Any]]:
    alarms: List[Dict[str, Any]] = []
    status = realtime.get("status", "disconnected")
    timestamp = realtime.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    if status != "connected":
        alarms.append({
            "timestamp": timestamp,
            "alarm_type": "connection",
            "alarm_id": "PLC_CONN",
            "message": "PLC disconnected or no valid data.",
            "severity": "high",
            "value": None,
        })

    bits = realtime.get("bits", [])
    for index in range(30, 38):
        if index < len(bits) and bits[index]:
            alarms.append({
                "timestamp": timestamp,
                "alarm_type": "bit",
                "alarm_id": f"BIT{index}",
                "message": BIT_ALARM_LABELS.get(index, f"Bit {index} alarm"),
                "severity": "high",
                "value": True,
            })

    words = realtime.get("words", [])
    for index, rule in WORD_ALARM_RULES.items():
        if index < len(words):
            value = float(words[index])
            if value < rule["min"]:
                alarms.append({
                    "timestamp": timestamp,
                    "alarm_type": "value",
                    "alarm_id": f"WORD{index}",
                    "message": f"{WORD_LABELS.get(index, f'W{index}')} {rule['low']} ({value:.1f})",
                    "severity": rule["severity"],
                    "value": value,
                })
            elif value > rule["max"]:
                alarms.append({
                    "timestamp": timestamp,
                    "alarm_type": "value",
                    "alarm_id": f"WORD{index}",
                    "message": f"{WORD_LABELS.get(index, f'W{index}')} {rule['high']} ({value:.1f})",
                    "severity": rule["severity"],
                    "value": value,
                })

    return alarms


def load_alarm_history() -> pd.DataFrame:
    if not ALARM_HISTORY_CSV.exists():
        return pd.DataFrame(columns=ALARM_COLUMNS)

    try:
        df = pd.read_csv(ALARM_HISTORY_CSV, encoding="utf-8-sig")
        return df
    except Exception:
        return pd.DataFrame(columns=ALARM_COLUMNS)


def append_alarm_history(alarms: List[Dict[str, Any]]) -> bool:
    if not alarms:
        return True

    try:
        exists = ALARM_HISTORY_CSV.exists()
        with ALARM_HISTORY_CSV.open("a", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            if not exists:
                writer.writerow(ALARM_COLUMNS)
            for alarm in alarms:
                writer.writerow([
                    alarm.get("timestamp", ""),
                    alarm.get("alarm_type", ""),
                    alarm.get("alarm_id", ""),
                    alarm.get("message", ""),
                    alarm.get("severity", ""),
                    alarm.get("value", ""),
                ])
        return True
    except Exception:
        return False


def load_history_data() -> pd.DataFrame:
    if not HISTORY_CSV.exists():
        return pd.DataFrame(columns=HISTORY_COLUMNS)

    try:
        df = pd.read_csv(HISTORY_CSV, encoding="utf-8-sig")
        return df
    except Exception:
        return pd.DataFrame(columns=HISTORY_COLUMNS)


def append_history_row(values: List[float], accum_heat: float = 0.0, timestamp: Optional[str] = None) -> bool:
    if timestamp is None:
        timestamp = datetime.now().strftime("%y/%m/%d %H:%M")

    safe_values = [float(v) if isinstance(v, (int, float)) else 0.0 for v in values[:11]]
    while len(safe_values) < 11:
        safe_values.append(0.0)

    row = [timestamp] + safe_values + [float(accum_heat) if isinstance(accum_heat, (int, float)) else 0.0]
    if len(row) != len(HISTORY_COLUMNS):
        return False

    try:
        exists = HISTORY_CSV.exists()
        with HISTORY_CSV.open("a", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            if not exists:
                writer.writerow(HISTORY_COLUMNS)
            writer.writerow(row)
        return True
    except Exception:
        return False
def init_db():
    """시스템 시작 시 호출하여 DB 테이블이 없으면 생성합니다."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # 1. 실시간 상태 테이블 (가장 최신 상태 1줄만 유지하거나 기록)
        cursor.execute('''CREATE TABLE IF NOT EXISTS realtime_logs (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                            data_json TEXT
                        )''')
        # 2. 센서 데이터 이력 테이블 (트렌드 분석용)
        cursor.execute('''CREATE TABLE IF NOT EXISTS history_logs (
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                            w0 REAL, w1 REAL, w2 REAL, w3 REAL, w4 REAL, 
                            w5 REAL, w6 REAL, w7 REAL, w8 REAL, w9 REAL, w10 REAL,
                            accum_heat REAL
                        )''')
        conn.commit()

def save_history_to_db(words, accum_heat):
    """PLC 데이터를 DB 이력 테이블에 저장합니다."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO history_logs 
                              (w0, w1, w2, w3, w4, w5, w6, w7, w8, w9, w10, accum_heat) 
                              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                           (*words, accum_heat))
            conn.commit()
    except Exception as e:
        print(f"DB 저장 오류: {e}")