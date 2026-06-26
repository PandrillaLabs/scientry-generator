from collect_dois.collector.chemistry_world import ChemistryWorldCollector
from collect_dois.collector.futurity import FuturityCollector
from collect_dois.collector.live_science import LiveScienceCollector
from collect_dois.collector.nature import NatureCollector
from collect_dois.collector.science_daily import ScienceDailyCollector
from config.logger import GlobalLogger


class DoiCollector:
    def __init__(self):
        self.logger = GlobalLogger().get_logger(self.__class__)
        self.sdc = ScienceDailyCollector()
        self.nc = NatureCollector()
        self.lsc = LiveScienceCollector()
        self.fc = FuturityCollector()
        self.cwc = ChemistryWorldCollector()

    def collect_dois(self):
        try:
            self.sdc.collect_dois()
            self.nc.collect_dois()
            self.lsc.collect_dois()
            self.fc.collect_dois()
            self.cwc.collect_dois()
        except Exception as e:
            self.logger.error(f"Error collecting DOIs: {e}")