from dotenv import load_dotenv
import os
import sys

from config.logger import GlobalLogger

load_dotenv()


class EnvConfig:
    logger = GlobalLogger().get_logger(__name__)

    # API URLS
    BASE_BACKEND_URL = os.getenv("BASE_BACKEND_URL")
    REQUEST_PAPERS_URL = f"{BASE_BACKEND_URL}/paper/request"

    # API KEYS
    BACKEND_API_KEY = os.getenv("BACKEND_API_KEY")