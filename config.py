from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# site identity
SITE_ID = "default"

# head-office communication
HEAD_ENABLED = True
HEAD_SERVER_URL = "http://본사서버주소:8000"
API_KEY = ""

# file paths
REALTIME_JSON = BASE_DIR / "realtime_data.json"
HISTORY_CSV = BASE_DIR / "history_data.csv"
SITE_DIR = BASE_DIR / "sites" / SITE_ID
DIAGRAM_HTML = SITE_DIR / "diagram.html"
BACKGROUND_IMAGE = SITE_DIR / "background.png"
LOG_FILE = BASE_DIR / "mecom_hmi.log"
CONTROL_COMMAND_JSON = BASE_DIR / "control_command.json"
CONTROL_ENABLED = True
COIL_ADDRESS = 1
CONTROL_WRITE_UNIT = 1

# Modbus
MODBUS_PORT = "com14"
MODBUS_BAUDRATE = 9600
MODBUS_SLAVE_ID = 1
POLL_INTERVAL = 0.5
BIT_READ_START = 0
BIT_WRITE_START = 500
WORD_READ_START = 0

# history columns
HISTORY_COLUMNS = [
    "날짜",
    "지중공급온도(1동)",
    "지중환수온도(1동)",
    "지중공급온도(2동)",
    "지중환수온도(2동)",
    "2차공급온도(1동)",
    "2차환수온도(1동)",
    "2차공급온도(2동)",
    "2차환수온도(2동)",
    "1동유량",
    "2동유량",
    "생산열량",
    "누적열량"
]
HISTORY_RECORD_INTERVAL_SEC = 60

DB_PATH = BASE_DIR / "mecom_data.db"
ADMIN_PASSWORD = "1234"
PASSWORD_FILE = BASE_DIR / "password.json"
TEST_MODE = False
