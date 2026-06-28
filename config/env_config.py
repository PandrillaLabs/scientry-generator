from dotenv import load_dotenv
import os

load_dotenv(override=True)

class EnvConfig:
    BASE_BACKEND_URL = os.environ["BASE_BACKEND_URL"]
    REQUEST_PAPERS_URL = f"{BASE_BACKEND_URL}/paper/request"
    BACKEND_API_KEY = os.environ["BACKEND_API_KEY"]