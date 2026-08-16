from collect_metadata.collectors.doi_org import DoiOrg
from collect_metadata.collectors.open_alex import OpenAlex
from config.logger import GlobalLogger

class MetadataCollector:
    def __init__(self):
        self.logger = GlobalLogger().get_logger(self.__class__)
        self.doi_org = DoiOrg()
        self.open_alex = OpenAlex()

    def collect_metadata_for_doi(self, doi: str):
        try:
            json_metadata = self.doi_org.get_json_citation(doi)
            if not json_metadata:
                self.logger.error(f"Failed to retrieve metadata for DOI: {doi}")
                return None
            apa_citation = self.doi_org.get_apa_citation(json_metadata)
            if not apa_citation:
                self.logger.error(f"Failed to generate APA citation for DOI: {doi}")
                return None
            metadata_dto = self.open_alex.get_doi_metadata(doi, json_metadata, apa_citation)
            if not metadata_dto:
                self.logger.error(f"Failed to retrieve OpenAlex metadata for DOI: {doi}")
                return None
            return metadata_dto.json()
        except Exception as e:
            self.logger.error(f"Error collecting metadata for DOI {doi}: {e}")
            return None