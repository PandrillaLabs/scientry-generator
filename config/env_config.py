from dotenv import load_dotenv
import os

load_dotenv(override=True)

class EnvConfig:
    BASE_BACKEND_URL = os.environ["BASE_BACKEND_URL"]
    COOKIE_ID = os.environ["COOKIE_ID"]
    CLIENT_IP = os.environ["CLIENT_IP"]

    REQUEST_PAPERS_URL = f"{BASE_BACKEND_URL}/papers/request"
    REQUESTED_PAPERS_URL = f"{BASE_BACKEND_URL}/papers/requested"
    COLLECT_PAPER_METADATA_URL = f"{BASE_BACKEND_URL}/papers/collect"
