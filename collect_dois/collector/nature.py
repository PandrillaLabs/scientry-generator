import re
from urllib.parse import parse_qs, unquote, urlparse

import requests
from xml.etree import ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed

from bs4 import BeautifulSoup
from tqdm import tqdm
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config.logger import GlobalLogger
from utils.data_submitter import DataSubmitter


class NatureCollector:
    NUM_WORKERS = 96
    def __init__(self):
        self.logger = GlobalLogger().get_logger(self.__class__)
        self.rss_url = "https://www.nature.com/nature.rss"
        self.rdf_namespace = {
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
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
        try:
            resp = self.session.get(self.rss_url, timeout=10)
            resp.raise_for_status()
            root = ET.fromstring(resp.text)
        except Exception as e:
            self.logger.error(e)
            return
        article_links = [
            li.attrib.get("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource")
            for li in root.findall(".//rdf:li", self.rdf_namespace)
            if li.attrib.get("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource")
        ]
        if not article_links:
            return
        doi_set = set()
        with ThreadPoolExecutor(max_workers=self.NUM_WORKERS) as executor:
            futures = {
                executor.submit(self.process_article, url): url
                for url in article_links
            }
            for future in tqdm(
                as_completed(futures),
                total=len(futures),
                desc="Extracting DOIs from Nature Articles",
            ):
                dois = future.result()
                if dois:
                    doi_set.update(dois)
        self.data_submitter.submit_dois(doi_set)

    def process_article(self, url):
        try:
            page = self.session.get(url, timeout=10)
            page.raise_for_status()
            soup = BeautifulSoup(page.text, "lxml")
            reference_block = soup.find("div", id="references")
            if reference_block is None:
                return None
            dois = set(self.DOI_REGEX.findall(reference_block.text))
            if dois:
                return list(dois)
            for link in reference_block.find_all("a", href=True):
                doi = link.get("data-doi")
                if doi:
                    dois.add(doi)
                    continue
                label = link.get("data-track-label")
                if label and label.startswith("10."):
                    dois.add(label)
                    continue
                item = link.get("data-track-item_id")
                if item and item.startswith("10."):
                    dois.add(item)
                    continue
                href = unquote(link["href"])
                if "doi.org/" in href:
                    doi = href.split("doi.org/")[-1].split("?")[0]
                    if doi.startswith("10."):
                        dois.add(doi)
                        continue
                if "scholar_lookup" in href:
                    query = parse_qs(urlparse(href).query)
                    doi = query.get("doi")
                    if doi:
                        dois.add(doi[0])
            return list(set(dois))
        except Exception:
            self.logger.error(f"Error processing article: {url}", exc_info=True)
            return None