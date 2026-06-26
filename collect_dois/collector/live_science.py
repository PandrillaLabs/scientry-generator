import re
import requests
from xml.etree import ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed

from bs4 import BeautifulSoup
from tqdm import tqdm
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config.env_config import EnvConfig
from config.logger import GlobalLogger
from utils.data_submitter import DataSubmitter

class LiveScienceCollector:
    NUM_WORKERS = 96
    def __init__(self):
        self.logger = GlobalLogger().get_logger(self.__class__)
        self.rss_url = "https://www.livescience.com/feeds.xml"
        self.session = requests.Session()
        adapter = HTTPAdapter(
            pool_connections=128,
            pool_maxsize=128,
            max_retries=Retry(
                total=2,
                backoff_factor=0.2,
                status_forcelist=[429, 500, 502, 503, 504],
            ),
        )
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.data_submitter = DataSubmitter()
        self.DOI_REGEX = re.compile(
            r"(?<!\w)(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+?)(?=[\"'<>\s]|$)",
            re.IGNORECASE,
        )

    def collect_dois(self):
        try:
            resp = self.session.get(self.rss_url, timeout=10)
            resp.raise_for_status()
            root = ET.fromstring(resp.text)
        except Exception as e:
            self.logger.error(e)
            return
        text = " ".join(
            t.strip()
            for t in root.itertext()
            if t and t.strip()
        )
        doi_set = set(self.DOI_REGEX.findall(text))
        self.data_submitter.submit_dois(doi_set)
