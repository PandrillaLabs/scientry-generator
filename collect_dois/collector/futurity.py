import json
import re
import requests
import xml.etree.ElementTree as ET

from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tqdm import tqdm

from config.env_config import EnvConfig
from config.logger import GlobalLogger
from utils.data_submitter import DataSubmitter


class FuturityCollector:
    NUM_WORKERS = 32
    def __init__(self):
        self.logger = GlobalLogger().get_logger(self.__class__)
        self.data_sources = [
            "https://www.futurity.org/category/science-technology/feed/",
            "https://www.futurity.org/category/health-medicine/feed/",
            "https://www.futurity.org/category/earth-environment/feed/"
        ]
        self.session = requests.Session()
        adapter = HTTPAdapter(
            pool_connections=64,
            pool_maxsize=64,
            max_retries=Retry(
                total=2,
                backoff_factor=0.2,
                status_forcelist=[429, 500, 502, 503, 504],
            ),
        )
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.data_submitter = DataSubmitter()
        self.xml_namespace = {
            "content": "http://purl.org/rss/1.0/modules/content/"
        }
        self.DOI_REGEX = re.compile(
            r"(?<!\w)(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+?)(?=[\"'<>\s]|$)",
            re.IGNORECASE,
        )

    def collect_dois(self):
        doi_set = set()
        with ThreadPoolExecutor(max_workers=self.NUM_WORKERS) as executor:
            futures = {
                executor.submit(self.process_feed, url): url
                for url in self.data_sources
            }
            for future in tqdm(
                as_completed(futures),
                total=len(futures),
                desc="Extracting DOIs from Futurity RSS Feeds",
            ):
                result = future.result()
                if result:
                    doi_set.update(result)
        self.data_submitter.submit_dois(doi_set)

    def process_feed(self, rss_url):
        try:
            response = self.session.get(rss_url, timeout=10)
            response.raise_for_status()
            root = ET.fromstring(response.text)
            channel = root.find("channel")
            if channel is None:
                return set()
            dois = set()
            for item in channel.findall("item"):
                content = item.find(
                    "content:encoded",
                    self.xml_namespace,
                )
                if content is None or not content.text:
                    continue
                matches = self.DOI_REGEX.findall(content.text)
                if matches:
                    dois.update(m.rstrip(".,);]}>\"'") for m in matches)
            return dois
        except Exception as e:
            self.logger.error(e)
            return set()