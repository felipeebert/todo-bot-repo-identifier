import csv
import json
from datetime import datetime

from github import BadCredentialsException, UnknownObjectException, GithubException

from util import rate_limited_retry_search


SETTING_TO_VALID_PROPERTY = {
    "min-stars":                lambda val, repo: val < 0 or repo.stargazers_count >= val,
    "min-forks":                lambda val, repo: val < 0 or repo.forks_count >= val,
    "min-watchers":             lambda val, repo: val < 0 or repo.watchers_count >= val,
    "ignore-forks":             lambda val, repo: not val or not repo.fork,
    "ignore-private-repos":     lambda val, repo: not val or not repo.private,
    "ignore-archived-repos":    lambda val, repo: not val or not repo.archived,
}

def repo_adheres_to_settings(repo, settings):
    for setting, is_valid in SETTING_TO_VALID_PROPERTY.items():
        if not is_valid(settings.get(setting), repo):
            return False
    return True

def find_repos(github, settings, logger):
    @rate_limited_retry_search(github)
    def run_repo_query(repo_name):
        results = github.get_repo(repo_name)
        return results

    repo_start_time = datetime.now()
    was_error = False
    succ_cnt = 0
    skip_cnt = 0
    del_cnt = 0
    misc_error_cnt = 0

    logger.info(f"====================")
    logger.info(f"Repo Filtering was started at {repo_start_time}!")
    logger.info(f"NB: This might take an even longer while, so grab two drinks and relax twice as much!\n")

    repos = {}
    try:
        with open(settings.get('results-issues-output-file'), newline='', encoding='utf-8') as issue_file:
            csv_reader = csv.DictReader(issue_file)
            for row in csv_reader:
                repo_name = row['repo']
                if repo_name not in repos:
                    try:
                        repo = run_repo_query(repo_name)

                        if repo_adheres_to_settings(repo, settings):
                            repos[repo_name] = {
                                'issues': [],
                                'stars': repo.stargazers_count,
                                'forks': repo.forks_count,
                                'watchers': repo.subscribers_count,
                                'is_fork': repo.fork,
                                'is_private': repo.private,
                                'is_archived': repo.archived,
                                'estimated_size': repo.size,
                                'created_at': repo.created_at.isoformat(),
                                'updated_at': repo.updated_at.isoformat(),
                                'clone_url': repo.clone_url,
                                'skipped': False,
                                'error': None,
                            }
                            logger.debug(f"Fetched Information of <{repo_name}>")
                            succ_cnt += 1
                        else:
                            repos[repo_name] = {
                                'skipped': True,
                                'error': None,
                            }
                            logger.debug(f"Skipped Information of <{repo_name}> as it did not adhere to the settings")
                            skip_cnt += 1
                    except (BadCredentialsException, UnknownObjectException) as e:
                        repos[repo_name] = {
                            'skipped': True,
                            'error': e.status,
                        }
                        logger.warning(f"Could not fetch information of <{repo_name}>; it might have been deleted or made private!")
                        del_cnt += 1
                    except GithubException as e:
                        logger.warning(f"Could not fetch information of <{repo_name}> for another reason!")
                        repos[repo_name] = {
                            'skipped': True,
                            'error': {'status': e.status, 'data': e.data},
                        }
                        misc_error_cnt += 1

                if not repos[repo_name]['skipped']:
                    repos[repo_name]['issues'].append({'number': row['number'], 'created_at': row['created_at'], 'state': row['state']})
    except Exception as e:
        logger.error(f"Unexpected {type(e)} (Exception): {e}")
        was_error = True

    output_filename = settings.get('results-repos-output-file')
    with open(output_filename, 'w', newline='', encoding='utf-8') as output_file:
        output_file.write(json.dumps(repos))

    repo_end_time = datetime.now()
    logger.info(f"====================")
    logger.info(f"Search was ended at {repo_end_time}, and took {repo_end_time - repo_start_time} h:mm:ss!")
    logger.info(f"> Identified {succ_cnt} unique repositries")
    logger.info(f"> Skipped {skip_cnt} unique repositories")
    logger.info(f"> Failed (deleted/privatised) {del_cnt} unique repositories")
    logger.info(f"> Failed (other) {misc_error_cnt} unique repositories")
    logger.info(f"Fetched {len(repos)} unique repositories, which were output in {output_filename}!")

    return was_error
