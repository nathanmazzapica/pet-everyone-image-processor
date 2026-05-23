import logging
import warnings
from typing import Optional

from src.security.virus_scanner import VirusScanner

class MockVirusScanner(VirusScanner):
    def __init__(self):
        RED = "\033[91m"
        YELLOW = "\033[93m"
        BOLD = "\033[1m"
        RESET = "\033[0m"
        logging.basicConfig(format=f"{RED}{BOLD}[%(asctime)s] {YELLOW}%(levelname)s{RESET} %(message)s")
        logging.critical("[-] WARNING: Using mock virus scanner")
        logging.critical("[-] WARNING: This is not a production environment")
        logging.critical("[-] WARNING: Do not use this in production")

    def scan(self, stream: bytes) -> Optional[str]:
        return None