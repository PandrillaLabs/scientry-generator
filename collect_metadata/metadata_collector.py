from config.logger import GlobalLogger

class MetadataCollector:
    def __init__(self):
        self.logger = GlobalLogger().get_logger(self.__class__)

    def collect_metadata(self, rounds: int = 1):
        pass