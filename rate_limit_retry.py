import time

from datetime import datetime, timezone
from github import RateLimitExceededException

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
                    reset = limits.search.reset.replace(tzinfo=timezone.utc)
                    now = datetime.now(timezone.utc)
                    seconds = (reset - now).total_seconds()
                    print(f"> GitHub Search Rate limit exceeded")
                    print(f"> Reset is in {seconds:.3g} seconds.")
                    if seconds > 0.0:
                        print(f"> Waiting for {seconds:.3g} seconds...")
                        time.sleep(seconds)
                        print("> Done waiting - resume!")
            raise Exception("Failed too many times")
        return ret
    return decorator
