import logging
from typing import Any
from datetime import datetime
from utils.shared_functions import get_traceback, flatten

class Logger():
    def __init__(self,
                   name : str,
                   filepath : str,
                   level : int = logging.INFO,
                   print_level : int = logging.ERROR,
                   format : str = "[%(asctime)s][%(name)s][%(levelname)s]: %(message)s",
                   colored : bool = True,
                   debug_mode : bool = False
    ):
        self.name = name
        self.filepath = filepath
        self.level = level
        self.print_level = print_level
        self.colored = colored
        self.setDebugMode(debug_mode)

        formatter = logging.Formatter(format)
        filehandler = logging.FileHandler(filepath, encoding="utf-8", mode='a')
        consolehandler = logging.StreamHandler()

        filehandler.setFormatter(formatter)
        filehandler.setLevel(self.level)
        consolehandler.setFormatter(formatter)
        consolehandler.setLevel(self.print_level)

        self._logger = logging.getLogger(name)
        self._logger.setLevel(min(self.level, self.print_level))
        self._logger.addHandler(filehandler)
        self._logger.addHandler(consolehandler)
    
    def setDebugMode(self, debug : bool):
        if debug:
            self.level = logging.DEBUG
        self.debug_mode = debug

    def _log(self, *args : str, level : int, force_print : bool = False, **kwargs):
        msg = " ".join(str(arg) for arg in args)
        self._logger.log(level, msg, **kwargs)

        if force_print and level < self.print_level:
            self._printToConsole(level, msg)
    
    # Log a debug message
    def debug(self, *args : str, **kwargs):
        self._log(*args, level=logging.DEBUG, **kwargs)

    # Log an info message
    def info(self, *args : str, force_print : bool = False, **kwargs):
        self._log(*args, level=logging.INFO, force_print=force_print, **kwargs)

    # Log a warning message
    def warning(self, *args : str, force_print : bool = False, **kwargs):
        self._log(*args, level=logging.WARNING, force_print=force_print, **kwargs)

    # Log an error message
    def error(self, *args : str, force_print : bool = False, **kwargs):
        self._log(*args, level=logging.ERROR, force_print=force_print, **kwargs)

    # Log an exception
    def exception(self, exception: Exception, **kwargs):
        self._logger.error(get_traceback(exception), **kwargs)

    # Log a critical message
    def critical(self, *args : str, **kwargs):
        self._log(*args, level=logging.CRITICAL, **kwargs)
    
    # Log directly to console 
    def _printToConsole(self, level, msg):
        msg = f"[{datetime.now().strftime('%H:%M:%S')}][{self.name.upper()}][{logging.getLevelName(level)}]: {msg}"
        
        if self.colored:
            if level == logging.WARNING:
                msg = f"\033[0;33m{msg}\033[0m" # Yellow
                
            elif level == logging.ERROR:
                msg = f"\033[0;31m{msg}\033[0m" # Red
                
            elif level == logging.CRITICAL:
                msg = f"\033[1;31m{msg}\033[0m" # Bold red
                
            elif level == logging.DEBUG:
                msg = f"\033[0;30m{msg}\033[0m" # Black
                
        print(msg)

class Cache:
    """
    A class to allow easy creation and handling of a cache
    """
    def __init__(self, logger : Logger, initial_data : dict = {}):
        """
        Parameters
        ----------
        logger: utils.logger.Logger
            the logger object that the cache will utilise
        initial_data : dict, optional
            cache data at initialisation, `{}` if None
        """
        self._logger = logger
        self._cache = initial_data
    
    def isEmpty(self) -> bool:
        """
        Returns true if cache is empty, else False
        """
        return len(self._cache) == 0

    def put(self, *path : str | int | list[str | int] | tuple[str | int], key : Any, value : Any) -> None:
        """
        puts a specified key:value pair in the cache at a given path

        Parameters
        ----------
        *path : str | int | list[str|int] | tuple[str|int]
            The path inside the cache at which to insert the key:value pair.\n
            Example paths: `"my_data"`, `["previous_games", "round_data", 1]`, `("items", "legendary")`
        key : Any
            The key. Must be an immutable object
        value : Any
            The value to put.
        """
        if not path: # set at root
            self._cache[key] = value
            return None
        # support nested sequences in given path
        flatpath = flatten(path)
        # follow path
        curLoc : dict = self._cache
        try:
            for loc in flatpath:
                # account for keys in the path that do not exist
                if loc not in curLoc.keys():
                    curLoc[loc] = {}
                curLoc = curLoc[loc]  
            # successfully found location
            curLoc[key] = value  
        except Exception as e:
            self._logger.exception(e)

    def get(self, *path : str | int | list[str | int] | tuple[str | int]) -> Any | None:
        """
        returns the value present in the cache at a given path\n
        returns whole cache if no path specified

        Parameters
        ----------
        *path : str | int | list[str|int] | tuple[str|int]
            The path inside the cache from which to return the value.\n
            Example paths: `"my_data"`, `["previous_games", "round_data", 1]`, `("items", "legendary")`
        
        Returns
        -------
        value : Any | None
            The retrieved value if any, else None
        """
        if not path: return self._cache
        # support nested sequences in given path
        flatpath = flatten(path)
        # follow path
        curLoc : dict = self._cache.copy()
        try:
            for loc in flatpath:
                # wanted key doesnt exist in cache
                if loc not in curLoc.keys():
                    return None
                curLoc = curLoc[loc]
            # successfully found
            return curLoc
        except Exception as e:
            self._logger.exception(e)
            return None
    
    def exists(self, *path : str | int | list[str | int] | tuple[str | int]) -> bool:
        """
        checks whether any data is stored in the cache at a given path

        Parameters
        ----------
        *path : str | int | list[str|int] | tuple[str|int]
            The path inside the cache from which to return the value.\n
            Example paths: `"my_data"`, `["previous_games", "round_data", 1]`, `("items", "legendary")`
        
        Returns
        -------
        exists : bool
            True if value assigned, else False
        """
        obj : Any = self.get(*path)
        return obj is not None