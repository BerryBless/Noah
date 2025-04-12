# ----------------------
# file   : app/utils/logger.py
# function: 로깅 설정 및 logger 인스턴스 제공
# ----------------------

import logging
import sys

# ----------------------
# function: 로깅 포맷 지정
# ----------------------
LOG_FORMAT = "[%(asctime)s] [%(levelname)s] %(name)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ----------------------
# function: 로거 설정
# ----------------------
logger = logging.getLogger("noah-server")
logger.setLevel(logging.DEBUG)  # DEBUG, INFO, WARNING, ERROR, CRITICAL

# 핸들러 중복 방지
if not logger.hasHandlers():
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    logger.addHandler(console_handler)
