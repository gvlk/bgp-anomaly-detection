from logging import basicConfig, getLogger, StreamHandler, INFO
from sys import stdout


class Logger:
    @staticmethod
    def setup_logging(level: int = INFO) -> None:
        """
        Sets up the logging configuration.
        """

        basicConfig(
            level=level,
            datefmt='%H:%M',
            format='%(asctime)s - %(message)s',
            handlers=[StreamHandler(stdout)]
        )

    @staticmethod
    def get_logger(name: str):
        """
        Returns a logger with the specified name.

        :param name: The name of the logger.
        :return: A logger instance.
        """

        return getLogger(name)
