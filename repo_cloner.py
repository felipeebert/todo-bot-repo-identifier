import json
import os
from datetime import datetime, timedelta

from pygit2 import clone_repository
from pygit2.errors import GitError


def clone_repos(settings, logger):
    """
        Clones repositories from repos in which todo[bot] has created at least one issue.
    """
    output_path = settings.get('download-output-path-repo')

    input_filename = settings.get('results-repos-output-file')
    with open(input_filename, newline='', encoding='utf-8') as input_file:
        repos = json.load(input_file)

    repo_start_time = datetime.now()
    logger.info(f"Repo cloning started at {repo_start_time}! Attempting to clone {len(repos)} repos.\nThis is the last step and will take the longest!\n")

    skip_until = None # Insert name of the last successfully cloned repo here
    skip_until = "baskeboler/cljs-karaoke-client"
    skip_until = "holisticware-xamarin/HolisticWare.DotNetNew.XamarinProjectsStructureTemplate"
    skip_until = "timvideos/linux-litex"
    has_seen_skip = (skip_until is None)

    # Sort the repo names (to ensure items are iterated the same way every time)
    logger.info(f"Sorting and filtering {len(repos)} repository names")
    sorted_repos = []
    for name, repo in repos.items():
        if not repo.get('skipped'):
            sorted_repos.append((name, repo.get('clone_url')))
        else:
            # Do not clone repositories for which we failed to fetch information earlier in the process
            logger.debug(f"Skipping {name} because of earlier error: {repo.get('error')}")
    sorted_repos.sort(key=lambda t: t[0])
    num_repos = len(sorted_repos)

    logger.info(f"Sorting and filtering finished. Left with {num_repos} repositories")

    cnt = 0
    fail_cnt = 0
    msg_cnt = 0
    last_successful_repo = None
    was_error = False
    try:
        for (repo_name, repo_clone_url) in sorted_repos:
            if msg_cnt >= 50:
                msg_cnt = 0
                logger.info(f"Finished cloning {cnt}/{num_repos} repositories...")

            if not has_seen_skip:
                if repo_name == skip_until:
                    logger.info(f"Successfully skipped until {skip_until}")
                    has_seen_skip = True
                cnt += 1
                msg_cnt += 1
                continue

            try:
                repo = clone_repository(repo_clone_url, os.path.join(output_path, repo_name))
                last_successful_repo = repo_name
                logger.debug(f"\t* Successfully cloned <{repo_name}>")
            except GitError as e:
                logger.error(f"\t* Unexpected {type(e)} (GitError) for <{repo_name}>! {e}")
                fail_cnt += 1
            cnt += 1
            msg_cnt += 1
    except Exception as e:
        logger.error(f"Unexpected {type(e)} (Exception)! {e}")
        logger.error(f"Last repo that was successfully cloned: {last_successful_repo}")
        was_error = True

    repo_end_time = datetime.now()
    logger.info(f"Cloning was ended at {repo_end_time}, and took {repo_end_time - repo_start_time} h:mm:ss!")
    logger.info(f"Cloning process failed for {fail_cnt} repositories.")
    logger.info(f"Obtained {cnt - fail_cnt}/{num_repos} unique repositories, which were output in {output_path}!")
