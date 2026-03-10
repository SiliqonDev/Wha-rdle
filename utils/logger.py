import logging
from utils.shared_functions import get_traceback
from datetime import datetime

class Logger():
    def __init__(self,
                   name : str,
                   filepath : str,
                   level : int = logging.INFO,
                   print_level : int = logging.INFO,
                   format : str = "%(asctime)s:%(name)s: [%(levelname)s] %(message)s",
                   colors : bool = True
    ):
        self.name = name
        self.filepath = filepath
        self.level = level
        self.print_level = print_level
        self.format = format
        self.colors = colors

        self._handler = logging.FileHandler(filepath, encoding="utf-8", mode='a')
        self._handler.setFormatter(logging.Formatter(format))
        self._logger = logging.getLogger(name)
        self._logger.setLevel(level)
        self._logger.addHandler(self._handler)
    
    def _log(self, *args : str, level : int = 0, printToConsole : bool = False, **kwargs):
        msg = " ".join(str(arg) for arg in args)

        # level changed?
        logLevel = self.level
        if level:
            logLevel = level
        # write log
        self._logger.log(logLevel, msg, **kwargs)
        if printToConsole:
            self._printToConsole(level, msg)
    
    # Log an info message
    def info(self, *args : str, printToConsole : bool = False, **kwargs):
        self._log(*args, level=logging.INFO, **kwargs)
        if printToConsole: self._printToConsole(logging.INFO, *args)

    # Log a warning message
    def warning(self, *args : str, printToConsole : bool = False, **kwargs):
        self._log(*args, level=logging.WARNING, **kwargs)
        if printToConsole: self._printToConsole(logging.WARNING, *args)

    # Log an error message
    def error(self, *args : str, printToConsole : bool = False, **kwargs):
        self._log(*args, level=logging.ERROR, **kwargs)
        if printToConsole: self._printToConsole(logging.ERROR, *args)
    
    # Log a critical message
    def critical(self, *args : str, printToConsole : bool = False, **kwargs):
        self._log(*args, level=logging.CRITICAL, **kwargs)
        if printToConsole: self._printToConsole(logging.CRITICAL, *args)
    
    # Log a debug message
    def debug(self, *args : str, printToConsole : bool = False, **kwargs):
        self._log(*args, level=logging.DEBUG, **kwargs)
        if printToConsole: self._printToConsole(logging.DEBUG, *args)
    
    # Log an exception
    def exception(self, exception: Exception, **kwargs):
        self._logger.error(get_traceback(exception), **kwargs)
        if self.print_level <= logging.ERROR:
            print(get_traceback(exception))
    
    # Log directly to console 
    def _printToConsole(self, level, msg):
        msg = f"[{self.name.upper()}] [{datetime.now().strftime('%H:%M:%S')}] [{logging.getLevelName(level)}] {msg}"
        
        if self.colors:
            if level == logging.WARNING:
                msg = f"\033[0;33m{msg}\033[0m" # Yellow
                
            elif level == logging.ERROR:
                msg = f"\033[0;31m{msg}\033[0m" # Red
                
            elif level == logging.CRITICAL:
                msg = f"\033[1;31m{msg}\033[0m" # Bold red
                
            elif level == logging.DEBUG:
                msg = f"\033[0;30m{msg}\033[0m" # Black
                
        print(msg)