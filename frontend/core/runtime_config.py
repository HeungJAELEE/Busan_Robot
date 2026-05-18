import os
from pathlib import Path


def _load_dotenv_file(path):
    values = {}
    if not path.exists():
        return values
    try:
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key:
                values[key] = value
    except Exception:
        return values
    return values


PROJECT_ROOT = Path(__file__).resolve().parents[2]
_FILE_ENV = {}
_FILE_ENV.update(_load_dotenv_file(PROJECT_ROOT / ".env"))
_FILE_ENV.update(_load_dotenv_file(PROJECT_ROOT / "backend" / ".env"))


def _lookup(name):
    value = os.getenv(name)
    if value is not None and value != "":
        return value
    return _FILE_ENV.get(name)


def env_str(name, default=""):
    value = _lookup(name)
    if value is None or value == "":
        return default
    return value


def env_int(name, default):
    value = _lookup(name)
    if value is None or value == "":
        return int(default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def env_float(name, default):
    value = _lookup(name)
    if value is None or value == "":
        return float(default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def env_bool(name, default=False):
    value = _lookup(name)
    if value is None or value == "":
        return bool(default)
    return value.strip().lower() in ("1", "true", "yes", "on")


def env_first(names, default=""):
    for name in names:
        value = _lookup(name)
        if value is not None and value != "":
            return value
    return default


def env_first_int(names, default):
    for name in names:
        value = _lookup(name)
        if value is not None and value != "":
            try:
                return int(value)
            except (TypeError, ValueError):
                break
    return int(default)


def robot_defaults():
    return {
        "Robot A": {
            "ip": env_first(("ROBOT_A_IP", "ROBOT_IP"), "192.168.3.7"),
            "plc_ip": env_first(("ROBOT_A_PLC_IP", "PLC_PROCESS_IP", "PLC_IP"), "192.168.3.150"),
        },
        "Robot B": {
            "ip": env_str("ROBOT_B_IP", "192.168.3.6"),
            "plc_ip": env_first(("ROBOT_B_PLC_IP", "PLC_B_IP"), "192.168.3.140"),
        },
        "Robot C": {
            "ip": env_str("ROBOT_C_IP", "192.168.3.5"),
            "plc_ip": env_first(("ROBOT_C_PLC_IP", "PLC_C_IP"), "192.168.3.120"),
        },
    }


def default_new_robot_ip():
    return env_str("DEFAULT_NEW_ROBOT_IP", "")


def robot_model():
    return env_first(("ROBOT_MODEL", "ROBOT_NAME"), "NRMK-Indy7")


def mqtt_config():
    return {
        "broker": env_first(("HMI_MQTT_BROKER", "MQTT_BROKER"), "127.0.0.1"),
        "port": env_first_int(("HMI_MQTT_PORT", "MQTT_PORT"), 1883),
        "autoconnect": env_bool("HMI_MQTT_AUTOCONNECT", True),
    }


def plc_config():
    return {
        "process_ip": env_first(("PLC_PROCESS_IP", "PLC_IP"), "192.168.3.150"),
        "process_port": env_first_int(("PLC_PROCESS_PORT", "PLC_PORT"), 2000),
        "monitor_ip": env_str("PLC_MONITOR_IP", "192.168.3.160"),
        "monitor_port": env_int("PLC_MONITOR_PORT", 2000),
        "start_device": env_str("PLC_PROCESS_START_DEVICE", "X11"),
        "stop_device": env_str("PLC_PROCESS_STOP_DEVICE", "X12"),
        "complete_device": env_str("PLC_ROBOT_COMPLETE_DEVICE", "X145"),
        "robot_start_output": env_str("PLC_ROBOT_START_OUTPUT", "Y160"),
        "done_signal_map": env_str("PLC_DONE_SIGNAL_MAP", "PLC150:M1150,PLC130:M1130,PLC120:M1120"),
    }


def mysql_config():
    return {
        "host": env_first(("DB_HOST", "MYSQL_HOST"), "192.168.3.141"),
        "port": env_first_int(("DB_PORT", "MYSQL_PORT"), 3306),
        "user": env_first(("DB_USER", "MYSQL_USER"), "guest"),
        "password": env_first(("DB_PASS", "MYSQL_PASSWORD"), "guest1234"),
        "db": env_first(("DB_NAME", "MYSQL_DATABASE"), "faictory_mes"),
        "charset": "utf8mb4",
        "autocommit": True,
        "use_unicode": True,
        "init_command": "SET NAMES utf8mb4",
    }


def mes_url():
    return env_str("MES_URL", "http://127.0.0.1:8080/api/v1/telemetry")
