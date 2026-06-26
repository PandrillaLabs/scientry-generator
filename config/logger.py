import logging
import os
from datetime import datetime


class GlobalLogger:
    """
    Singleton-style global logger for consistent use across modules.
    Logs to both console (with colors) and a rotating file.
    Automatically includes class and method context in every log line.
    """

    _instance = None

    def __new__(cls, log_dir: str = "logs", log_level=logging.INFO):
        if cls._instance is None:
            cls._instance = super(GlobalLogger, cls).__new__(cls)
            cls._instance._init_logger(log_dir, log_level)
        return cls._instance

    def _init_logger(self, log_dir: str, log_level: int):
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_file_path = os.path.join(log_dir, f"scientry_{timestamp}.log")

        # Root logger
        self.logger = logging.getLogger("Scientry")
        self.logger.setLevel(log_level)
        self.logger.propagate = False  # avoid duplicate console logs

        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s.%(funcName)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # File handler
        file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        # Console handler with colors
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(ColorFormatter("%(asctime)s | %(levelname)-8s | %(name)s.%(funcName)s | %(message)s"))
        self.logger.addHandler(console_handler)

        self.logger.info(f"Logger initialized — writing logs to {log_file_path}")

    def get_logger(self, cls=None):
        """
        Returns a child logger tagged with the class name (if provided).
        Example: logger = GlobalLogger().get_logger(MyClass)
        """
        if isinstance(cls, str):
            return self.logger.getChild(cls)
        elif cls is not None:
            return self.logger.getChild(cls.__name__)
        return self.logger


class ColorFormatter(logging.Formatter):
    """
    Adds terminal color codes for log levels in console output.
    """
    COLORS = {
        "DEBUG": "\033[94m",    # Blue
        "INFO": "\033[92m",     # Green
        "WARNING": "\033[93m",  # Yellow
        "ERROR": "\033[91m",    # Red
        "CRITICAL": "\033[95m"  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelname, "")
        message = super().format(record)
        return f"{color}{message}{self.RESET}"