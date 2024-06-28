import logging
from sys import stdout

logging.basicConfig(
    level=logging.INFO,
    datefmt='%H:%M',
    format='%(asctime)s - %(message)s',
    handlers=[logging.StreamHandler(stdout)]
)
