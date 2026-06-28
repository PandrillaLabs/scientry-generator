import os
import re

import requests
from requests.adapters import HTTPAdapter
from urllib3 import Retry

from config.env_config import EnvConfig
from config.logger import GlobalLogger


class DataSubmitter:
    def __init__(self):
        self.logger = GlobalLogger().get_logger(self.__class__)
        self.data_sources = "sources/sciencedaily.json"
        self.add_dois_endpoint = EnvConfig.REQUEST_PAPERS_URL
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
        self.DOI_REGEX = re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", re.IGNORECASE)

    def normalize_doi(self, text: str) -> str | None:
        if not text:
            return None
        text = text.strip()
        text = text.replace("https://doi.org/", "")
        text = text.replace("http://doi.org/", "")
        text = text.replace("doi:", "")
        text = text.split("?")[0]
        text = text.split("#")[0]
        text = text.rstrip(".,;:)]}>\"'")
        match = self.DOI_REGEX.search(text)
        return match.group(0) if match else None

    def submit_dois(self, doi_set):
        if not doi_set:
            self.logger.info("No DOIs to submit.")
            return
        cleaned_dois = set()
        for doi in doi_set:
            normalized_doi = self.normalize_doi(doi)
            if normalized_doi:
                cleaned_dois.add(normalized_doi)
        with open("dois.txt", "w") as f:
            for doi in sorted(cleaned_dois):
                f.write(doi + "\n")
        try:
            self.logger.info(f"Submitting {len(cleaned_dois)} DOIs to backend.")
            resp = self.session.post(
                self.add_dois_endpoint,
                json={"doiIds": list(cleaned_dois)},
                headers={"Authorization": f"Bearer {EnvConfig.BACKEND_API_KEY}"},
            )
            resp.raise_for_status()
            if (resp.json().get("code") == 0):
                self.logger.info(resp.json().get("message") or f"Successfully submitted {len(cleaned_dois)} DOIs.")
            else:
                self.logger.error(resp.json().get("message") or f"Failed to submit DOIs: {resp.json().get('message')}")
        except requests.Timeout as e:
            message = e.response.json().get("message") if e.response else str(e)
            self.logger.error(f"Timeout occurred while submitting DOIs: {message}")
        except requests.ConnectionError as e:
            message = e.response.json().get("message") if e.response else str(e)
            self.logger.error(f"Connection error occurred while submitting DOIs: {message}")
        except requests.HTTPError as e:
            message = e.response.json().get("message") if e.response else str(e)
            self.logger.error(f"HTTP error occurred while submitting DOIs: {message}")
        except requests.RequestException as e:
            message = e.response.json().get("message") if e.response else str(e)
            self.logger.error(f"Error submitting DOIs: {message}")
        except Exception as e:
            message = e.response.json().get("message") if e.response else str(e)
            self.logger.error(f"Unexpected error occurred while submitting DOIs: {message}")