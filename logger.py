import logging
import re

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


# SO-008: Sanitise user-controlled strings before interpolating them into log
# messages to prevent log injection / log forging attacks.
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


def sanitize_for_log(value: str, max_length: int = 300) -> str:
    """
    Strip control characters (including newlines) and truncate to max_length.
    Use this for any value that originates from user input or LLM output
    before including it in a log message.
    """
    sanitized = _CONTROL_CHARS.sub(" ", str(value))
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "…"
    return sanitized