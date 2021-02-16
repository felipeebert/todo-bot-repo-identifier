import csv
from datetime import datetime, timedelta
from math import inf

from github.GithubObject import _NotSetType as NotSet

from util import rate_limited_retry_search


# Maximum number of entries that GitHub returns per search
# If we obtain more results than this value, our search space is too large
#   and we need to narrow down. (GitHub only returns 1000 results per search)
MAX_RESULTS_PER_SEARCH = 1000

# Shorthand notation for converting settings to GitHub search qualifiers
SETTING_TO_QUALIFIER = {
    'issue_level': {
        "bot-name":                 lambda x: f"author:{x} ",
        "ignore-private-repos":     lambda x: "is:public " if x else "",
        "ignore-archived-repos":    lambda x: "archived:false " if x else "",
        "type":                     lambda x: f"type:{x} " if x not in ["any", None] else "",
        "state":                    lambda x: f"state:{x} " if x not in ["any", None] else "",
        "language":                 lambda x: f"language:{x} " if x not in ["any", None] else "",
        "additional-issue-query":   lambda x: f"{x} " if x != "" else ""
    },
}

def construct_issue_search_query(settings):
    # Construct the search query
    issue_query = ""
    for setting, encode_setting in SETTING_TO_QUALIFIER.get('issue_level').items():
        issue_query += encode_setting(settings.get(setting))

    return issue_query

def is_issue(issue_or_pr):
    # PyGithub makes an API request if attempting to obtain PR-data of an issue with the pull_request-field
    # However, this is the only way to find out whether something is an issue or PR! yikes...
    #
    # If the data for the pull_request attribute is not set, we know it must be an issue (as otherwise we'd have
    # obtained the relevant PR-data for free in our earlier request!)
    if isinstance(issue_or_pr._pull_request, NotSet):
        return True

    # If the data is set, then we can just find out what it is
    return issue_or_pr.pull_request is not None


def find_issues(github, settings, logger):
    issue_query = construct_issue_search_query(settings)
    logger.info(f"Searching using the following query: {issue_query}")

    @rate_limited_retry_search(github)
    def run_search_query(query):
        results = github.search_issues(query)
        return results, results.totalCount

    @rate_limited_retry_search(github)
    def process_search_results(search_results, csv_writer, max_results_to_process):
        # !!! TODO: If the rate limit runs out during this loop, we will re-fetch all the issues of this
        #   loop, even if they were already processed before. As a result, duplicates can occur in the output !!!
        for result in search_results[:max_results_to_process]:
            logger.debug(f"ISSUE PRINTED TO CSV: {'/'.join(result.url.split('/')[-4:-2])} ({result.number})")

            csv_writer.writerow(["/".join(result.url.split("/")[-4:-2]), result.number, result.title, result.state,
                    "issue" if is_issue(result) else "pr",
                    result.created_at, result.updated_at,
                    result.closed_at, result.comments, result.body])

    max_results = settings.get("max-results")
    num_results_so_far = 0
    if max_results < 0:
        max_results = inf

    search_start_time = datetime.now()
    logger.info(f"====================")
    logger.info(f"Search was started at {search_start_time}!")
    logger.info(f"NB: This might take a while, so grab a drink and relax!\n")

    output_filename = settings.get('results-issues-output-file')
    with open(output_filename, 'w', newline='', encoding='utf-8') as output_file:
        csv_writer = csv.writer(output_file, quoting=csv.QUOTE_MINIMAL, escapechar="\\")
        csv_writer.writerow(["repo", "number", "title", "state", "type", "created_at", "updated_at",
                "closed_at", "num_comments", "body"])

        current_start_date = datetime.fromisoformat(settings.get("start-date"))
        final_end_date = datetime.fromisoformat(settings.get("end-date"))
        current_end_date = final_end_date

        # Ensure we obtain all repositories from the start to end time
        while num_results_so_far < max_results:
            # Repeatedly halve the search space if we obtain too many results
            while True:
                date_qualifier = f"created:{current_start_date.isoformat()}..{current_end_date.isoformat()}"
                logger.info(f"Searching for issues created between {current_start_date} and {current_end_date}")

                lazy_results, num_results = run_search_query(issue_query + date_qualifier)

                if num_results < MAX_RESULTS_PER_SEARCH:
                    max_results_to_process = min(num_results, max_results - num_results_so_far)
                    logger.info(f"> Query returned {num_results} search results! Processing {max_results_to_process} of them...")
                    process_search_results(lazy_results, csv_writer, max_results_to_process)
                    num_results_so_far += max_results_to_process
                    break

                logger.info("> Query returned too many search results... Halving search space...")

                new_end_date = current_start_date + (current_end_date - current_start_date)/2

                if new_end_date == current_end_date:
                    msg = "> HELP; could not limit query further but there were still >1000 results! D:"
                    logger.error(msg)
                    raise ValueError(msg)

                current_end_date = new_end_date

            if current_end_date == final_end_date:
                break

            # Add 1 second as the Github created:<datetime>..<datetime> syntax is inclusive for both the start AND end date
            # that's annoying...
            current_start_date = current_end_date + timedelta(seconds=1)
            current_end_date = final_end_date

    search_end_time = datetime.now()
    logger.info(f"====================")
    logger.info(f"Search was ended at {search_end_time}, and took {search_end_time - search_start_time} h:mm:ss!")
    logger.info(f"Obtained {num_results_so_far} results, which were output in {output_filename}!")
    logger.warning("These results might contain duplicate issues! Please filter these out before continueing.")
