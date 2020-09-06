"""Contains Utility functions for the bot issue identifier"""

import json
import logging
import time

from datetime import datetime, timezone
from github import RateLimitExceededException


LOGLEVEL_NAMES = ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]

# Standard GitHub API endpoint
STANDARD_API_ENDPOINT = "https://api.github.com"

# Some settings only allow specific values
SETTING_ALLOWED_VALUES = {
    "type":     ["any", "pr", "issue"],
    "state":    ["any", "open", "closed"],
}

g_logger = None

# Prints PyGithub API requests in a shorter form
class ShortRequestPrinter(logging.Filter):
    def filter(self, record):
        short_msg = ' '.join(record.getMessage().split()[:2])
        if '/rate_limit' not in short_msg:
            print(f"> PYGITHUB API REQUEST: {short_msg}")
        return False

# Creates a logger using a given name and level.
# Outputs to the terminal if no output_file_path is given, otherwise outputs to said file
def create_logger(name, level, output_file_path=None):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    handler = None
    if output_file_path is None:
        handler = logging.StreamHandler()
    else:
        handler = logging.FileHandler(output_file_path)
    handler.setFormatter(logging.Formatter('%(asctime)s (%(name)-12s) [%(levelname)s] %(message)s'))
    logger.addHandler(handler)
    return logger

# Loads the settings from a file with a given filename
def load_settings(filename):
    # Load search settings
    settings = {}
    with open(filename) as settings_file:
        settings = json.load(settings_file)
    return settings

def verify_loglevels(loggers):
    for loggername, level in loggers.items():
        if level not in LOGLEVEL_NAMES:
            raise ValueError(   f"Invalid loglevel passed for <{loggername}>. Got <{level}>, "
                                f"but expected one of <{', '.join(LOGLEVEL_NAMES)}>")

def verify_settings(settings):
    # Ensure that all settings have valid values
    for setting, allowed_values in SETTING_ALLOWED_VALUES.items():
        if settings.get(setting) not in allowed_values:
            raise ValueError(   f"Invalid setting passed for <{setting}>. Got <{settings.get(setting)}>, "
                                f"but expected one of <{', '.join(allowed_values)}>")
    if settings.get("additional-issue-query"):
        g_logger.info("Additional query parameters were provided, but these were not checked for syntax!")

def load_gh_logger(shorten_log_output):
    # Log-settings
    if shorten_log_output:
        g_logger.info('Simple PyGithub logging enabled')
        handler = logging.StreamHandler()
        handler.addFilter(ShortRequestPrinter())

        gh_logger = logging.getLogger("github")
        gh_logger.setLevel(logging.DEBUG)
        gh_logger.addHandler(handler)
    else:
        g_logger.info("Extended PyGithub logging enabled")
        enable_console_debug_logging()

def rate_limited_retry_search(github):
    """
    Abstracts away from the GitHub API rate limit
    Source: https://github.com/PyGithub/PyGithub/issues/553#issuecomment-546378228
    """
    def decorator(func):
        def ret(*args, **kwargs):
            for _ in range(3):
                try:
                    return func(*args, **kwargs)
                except RateLimitExceededException:
                    limits = github.get_rate_limit()
                    search_reset = limits.search.reset.replace(tzinfo=timezone.utc)
                    core_reset = limits.core.reset.replace(tzinfo=timezone.utc)

                    reset_time = search_reset
                    if limits.core.remaining <= 0:
                        reset_time = core_reset
                        if limits.search.remaining <= 0:
                            reset_time = max(search_reset, core_reset)

                    now = datetime.now(timezone.utc)
                    seconds = (reset_time - now).total_seconds()
                    print(f"> GitHub Search and/or Core Rate limit exceeded")
                    print(f"> Reset is in {seconds:.3g} seconds.")
                    if seconds < 0:
                        seconds = 1

                    if seconds > 0.0:
                        print(f"> Waiting for {seconds:.3g} seconds...")
                        time.sleep(seconds)
                        print("> Done waiting - resume!")
            raise Exception("Failed too many times")
        return ret
    return decorator
