from loguru import logger
import inspect
from functools import wraps


class CustomLogger:
    def __init__(self):
        # Настраиваем логгер для записи в файлы
        logger.add("logs/logfile.log", format="{time} {level} {message}", level="DEBUG")
        logger.add("logs/errorfile.log", format="{time} {level} {message}", level="ERROR")
        
        # Добавляем вывод в стандартный поток (stdout) для Docker
        logger.add("sys.stdout", format="{time} {level} {message}", level="INFO")

    def _get_caller_info(self):
        frame = inspect.stack()[2]
        module = inspect.getmodule(frame[0])
        filename = module.__file__ if module else "unknown"
        return filename

    def info(self, message):
        filename = self._get_caller_info()
        logger.info(f"{filename} - INFO - {message}")

    def debug(self, message):
        filename = self._get_caller_info()
        logger.debug(f"{filename} - DEBUG - {message}")

    def error(self, message, exc_info=False):
        filename = self._get_caller_info()
        if exc_info:
            # Для ошибок с трассировкой
            logger.opt(exception=True).error(f"{filename} - ERROR - {message}")
        else:
            logger.error(f"{filename} - ERROR - {message}")

    def warning(self, message):
        filename = self._get_caller_info()
        logger.warning(f"{filename} - WARNING - {message}")

    def critical(self, message, exc_info=False):
        filename = self._get_caller_info()
        if exc_info:
            # Для критических ошибок с трассировкой
            logger.opt(exception=True).critical(f"{filename} - CRITICAL - {message}")
        else:
            logger.critical(f"{filename} - CRITICAL - {message}")

    def log_exceptions(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                self.error(f"Exception in {func.__name__}: {e}")
                raise

        return wrapper


main_logger = CustomLogger()