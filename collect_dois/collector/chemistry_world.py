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


class ChemistryWorldCollector:
    NUM_WORKERS = 96
    def __init__(self):
        self.logger = GlobalLogger().get_logger(self.__class__)
        self.rss_urls = [
            "https://www.chemistryworld.com/409.rss",
            "https://www.chemistryworld.com/410.rss",
            "https://www.chemistryworld.com/411.rss",
            "https://www.chemistryworld.com/412.rss",
            "https://www.chemistryworld.com/413.rss",
            "https://www.chemistryworld.com/414.rss",
            "https://www.chemistryworld.com/415.rss",
            "https://www.chemistryworld.com/416.rss"
        ]
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 "
                "(compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
            )
        }
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
        article_links = []
        with ThreadPoolExecutor(max_workers=16) as executor:
            futures = {
                executor.submit(self.extract_links, rss): rss
                for rss in self.rss_urls
            }
            for future in tqdm(
                as_completed(futures),
                total=len(futures),
                desc="Collecting Chemistry World Links",
            ):
                article_links.extend(future.result())
        article_links = list(set(article_links))
        doi_set = set()
        with ThreadPoolExecutor(max_workers=self.NUM_WORKERS) as executor:
            futures = {
                executor.submit(self.process_article, url): url
                for url in article_links
            }
            for future in tqdm(
                as_completed(futures),
                total=len(futures),
                desc="Extracting Chemistry World DOIs",
            ):
                result = future.result()
                if result:
                    doi_set.update(result)
        self.data_submitter.submit_dois(doi_set)

    def extract_links(self, rss_url):
        try:
            response = self.session.get(
                rss_url,
                headers=self.headers,
                timeout=10,
            )
            response.raise_for_status()
            root = ET.fromstring(response.text)
            channel = root.find("channel")
            if channel is None:
                return []
            return [
                item.find("link").text.strip()
                for item in channel.findall("item")
                if item.find("link") is not None
            ]
        except Exception as e:
            self.logger.error(e)
            return []

    def process_article(self, url):
        try:
            page = self.session.get(
                url,
                headers=self.headers,
                timeout=10,
            )
            page.raise_for_status()
            matches = {
                m.rstrip(".,);]}>\"'")
                for m in self.DOI_REGEX.findall(page.text)
            }
            return matches
        except Exception as e:
            self.logger.error(e)
            return set()