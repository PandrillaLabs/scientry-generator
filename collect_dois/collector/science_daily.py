import json
import re
import requests
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from config.logger import GlobalLogger
from utils.data_submitter import DataSubmitter


class ScienceDailyCollector:
    NUM_WORKERS = 96
    def __init__(self):
        self.logger = GlobalLogger().get_logger(self.__class__)
        self.data_sources = [
            "https://www.sciencedaily.com/rss/health_medicine.xml",
            "https://www.sciencedaily.com/rss/mind_brain.xml",
            "https://www.sciencedaily.com/rss/living_well.xml",
            "https://www.sciencedaily.com/rss/space_time.xml",
            "https://www.sciencedaily.com/rss/matter_energy.xml",
            "https://www.sciencedaily.com/rss/computers_math.xml",
            "https://www.sciencedaily.com/rss/plants_animals.xml",
            "https://www.sciencedaily.com/rss/earth_climate.xml",
            "https://www.sciencedaily.com/rss/fossils_ruins.xml",
            "https://www.sciencedaily.com/rss/science_society.xml",
            "https://www.sciencedaily.com/rss/business_industry.xml",
            "https://www.sciencedaily.com/rss/education_learning.xml",
            "https://www.sciencedaily.com/rss/top/science.xml",
            "https://www.sciencedaily.com/rss/top/technology.xml",
            "https://www.sciencedaily.com/rss/top/health.xml"
        ]
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
                executor.submit(self.extract_pagelinks_from_rss, url): url
                for url in self.data_sources
            }
            for future in tqdm(
                as_completed(futures),
                total=len(futures),
                desc="Collecting ScienceDaily Article Links",
            ):
                article_links.extend(future.result())
        article_links = list(set(article_links))
        doi_set = self.extract_dois_from_articles(article_links)
        self.data_submitter.submit_dois(doi_set)

    def extract_pagelinks_from_rss(self, rss_url):
        try:
            r = self.session.get(rss_url, timeout=10)
            r.raise_for_status()
            root = ET.fromstring(r.text)
            return [
                link.text for item in root.findall(".//item")
                if (link := item.find("link")) is not None and link.text
            ]
        except Exception as e:
            self.logger.error(e)
            return []

    def extract_dois_from_articles(self, article_links):
        dois = set()
        with ThreadPoolExecutor(max_workers=self.NUM_WORKERS) as executor:
            futures = {
                executor.submit(self.extract_doi_from_page, url): url
                for url in article_links
            }
            for future in tqdm(
                as_completed(futures),
                total=len(futures),
                desc="Extracting DOIs from ScienceDaily Articles",
            ):
                doi = future.result()
                if doi:
                    dois.add(doi)
        return dois

    def extract_doi_from_page(self, url):
        try:
            r = self.session.get(url, timeout=10)
            r.raise_for_status()
            matches = self.DOI_REGEX.findall(r.text)
            if not matches:
                return None
            return next(iter(dict.fromkeys(matches)))
        except Exception as e:
            self.logger.error(e)
            return None