import logging
import os
from datetime import datetime

os.makedirs("logs", exist_ok=True)
_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s - %(message)s")
_file = logging.FileHandler(f"logs/{datetime.now():%Y%m%d}.log", encoding="utf-8")
_file.setFormatter(_fmt)
_console = logging.StreamHandler()
_console.setFormatter(_fmt)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        logger.addHandler(_file)
        logger.addHandler(_console)
    return logger
