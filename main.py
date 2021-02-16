import logging
import os

from github import Github, enable_console_debug_logging

import util
from bot_issue_finder import find_issues
from repo_finder import find_repos
from repo_cloner import clone_repos
import pre_bot_issue_finder

if __name__ == "__main__":
    settings = util.load_settings('settings.json')
    util.verify_loglevels(settings.get('loglevels'))
    loglevels = settings.get('loglevels')
    logoutputs = settings.get('logoutputs')

    # General logger
    logger = util.create_logger('bot_issue_finder', loglevels.get('general'), logoutputs.get('general'))
    util.g_logger = logger

    logger.info("======SETTINGS======")
    util.verify_settings(settings)

    if settings.get('log-pygithub-requests'):
        util.load_gh_logger(settings.get('shorten-pygithub-requests'))

    # Load GitHub Login information
    login_settings = util.load_settings('login.json')

    token_or_username = login_settings.get('login_or_token')
    if token_or_username and login_settings.get('password'):
        # Someone logged in with their username/password combination
        logger.info(f"Logged in as {token_or_username}")
    elif not token_or_username:
        # No user was logged in
        logger.info("No login was made; all reqests will be anonymous (NB: Less requests can be made per minute as an anonymous user!)")
    else:
        # Token login
        logger.info("Logged in using an access token")

    base_url = login_settings.get("base_url")
    if base_url is not None and base_url != util.STANDARD_API_ENDPOINT:
        logger.info(f"Using Github Enterprise with custom hostname: {base_url}")
    else:
        logger.info(f"Using the standard API endpoint at {util.STANDARD_API_ENDPOINT}")

    # Initialize PyGithub
    github = Github(per_page=100, **login_settings)

    logger.info("====================\n")

    # Issue finder logger
    if_logger = util.create_logger('issue_finder', loglevels.get('issue_finder'), logoutputs.get('issue_finder'))
    util.g_logger = if_logger

    # Find issues
    has_already_found_repos = os.path.isfile(settings.get('results-repos-output-file'))
    if has_already_found_repos:
        # Repositories were already fetched
        if_logger.info("Repositories were already fetched. Skipping the issue fetching phase!")
    elif os.path.isfile(settings.get('results-issues-output-file')):
        # Issues were already fetched
        if_logger.info("Found an existing issues file; using that instead!")
    else:
        # Issues were not yet fetched
        find_issues(github, settings, if_logger)

    # Repo finder logger
    rf_logger = util.create_logger('repo_finder', loglevels.get('repo_finder'), logoutputs.get('repo_finder'))
    util.g_logger = rf_logger

    # Find repositories
    if has_already_found_repos:
        rf_logger.info("Found an existing repo file; using that instead!")
    else:
        was_error = find_repos(github, settings, rf_logger)
        if was_error:
            msg = "An error occurred while fetching repositories!"
            if_logger.error(msg)
            raise ValueError(msg)


    # Repo cloner logger
    rc_logger = util.create_logger('repo_cloner', loglevels.get('repo_cloner'), logoutputs.get('repo_cloner'))
    util.g_logger = rc_logger

    if not settings.get('skip-cloning'):
        # Clone repositories
        clone_repos(settings, rc_logger)


    # Pre-bot issue logger
    pef_logger = util.create_logger('pre_issue_finder', loglevels.get('pre_issue_finder'), logoutputs.get('pre_issue_finder'))
    util.g_logger = pef_logger

    if True:
        pre_bot_issue_finder.find_pre_bot_issues(settings, pef_logger)
        pre_bot_issue_finder.remove_pre_duplicates(settings, logger)

    if True:
        pre_bot_issue_finder.obtain_pre_post_data(settings, logger)
        pre_bot_issue_finder.obtain_cloned_repos(settings, logger)

