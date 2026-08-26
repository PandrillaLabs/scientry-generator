from concurrent.futures import ThreadPoolExecutor, as_completed

from tqdm import tqdm

from collect_metadata.collectors.doi_org import DoiOrg
from collect_metadata.collectors.open_alex import OpenAlex
from collect_metadata.metadata_dto import MetadataDto
from config.logger import GlobalLogger
from utils.data_submitter import DataSubmitter

class MetadataCollector:
    def __init__(self):
        self.NUM_WORKERS = 10
        self.logger = GlobalLogger().get_logger(self.__class__)
        self.doi_org = DoiOrg()
        self.open_alex = OpenAlex()
        self.submitter = DataSubmitter()

    def collect_metadata_for_doi(self, doi: str) -> MetadataDto | None:
        try:
            json_metadata = self.doi_org.get_json_citation(doi)
            apa_citation = self.doi_org.get_apa_citation(json_metadata)
            return self.open_alex.get_doi_metadata(doi, json_metadata, apa_citation)
        except Exception as e:
            self.logger.error(f"Error collecting metadata for DOI {doi}: {e}")
            error_message = str(e)
            # TODO: MARK PAPER AS UNPUBLISHED WITH REASON -> ^
            return None

    def collect_submit_metadata_for_doi(self, doi: str):
        metadata_dto = self.collect_metadata_for_doi(doi)
        if metadata_dto:
            self.submitter.submit_metadata(metadata_dto)
        else:
            # TODO: MARK PAPER AS UNPUBLISHED WITH REASON -> ^
            self.logger.error(f"Metadata collection failed for DOI: {doi}")

    def collect_submit_metadata_for_dois(self):
        doi_set = self.submitter.get_requested_dois()
        if not doi_set:
            self.logger.info("No DOIs to process.")
            return
        with ThreadPoolExecutor(max_workers=self.NUM_WORKERS) as executor:
            futures = { executor.submit(self.collect_submit_metadata_for_doi, doi): doi for doi in doi_set }
            for future in as_completed(futures):
                dois = future.result()
                if dois:
                    doi_set.update(dois)