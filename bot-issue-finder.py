import csv
import json
import logging
import os

from datetime import datetime, timedelta
from github import Github, enable_console_debug_logging
from github.GithubObject import _NotSetType as NotSet
from math import inf
from rate_limit_retry import rate_limited_retry_search


# Prints PyGithub API requests in a shorter form
class ShortRequestPrinter(logging.Filter):
    def filter(self, record):
        short_msg = ' '.join(record.getMessage().split()[:2])
        if '/rate_limit' not in short_msg:
            print(f"*** API REQUEST: {short_msg}")
        return False


# Maximum number of entries that GitHub returns per search
# If we obtain more results than this value, our search space is too large
# and we need to narrow down. (GitHub only returns 1000 results per search)
MAX_RESULTS_PER_SEARCH = 1000

# Standard GitHub API endpoint
STANDARD_API_ENDPOINT = "https://api.github.com"

# Some settings only allow specific values
SETTING_ALLOWED_VALUES = {
    "type":     ["any", "pr", "issue"],
    "state":    ["any", "open", "closed"],
}

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

SETTING_TO_VALID_PROPERTY = {
    "min-stars":                lambda val, repo: val < 0 or repo.stargazers_count >= val,
    "min-forks":                lambda val, repo: val < 0 or repo.forks_count >= val,
    "min-watchers":             lambda val, repo: val < 0 or repo.watchers_count >= val,
    "ignore-forks":             lambda val, repo: not val or not repo.fork,
    "ignore-private-repos":     lambda val, repo: not val or not repo.private,
    "ignore-archived-repos":    lambda val, repo: not val or not repo.archived,
}

def load_settings(filename):
    # Load search settings
    settings = {}
    with open(filename) as settings_file:
        settings = json.load(settings_file)
    assert settings, "Settings file could not be loaded!"
    return settings

def verify_settings_values(setting_allowed_values):
    # Ensure that all settings have valid values
    for setting, allowed_values in setting_allowed_values.items():
        if settings.get(setting) not in allowed_values:
            raise ValueError(   f"Invalid setting passed for <{setting}>. Got <{settings.get(setting)}>, "
                                f"but expected one of <{', '.join(allowed_values)}>")
    
    if settings.get("additional-issue-query"):
        print("Additional query parameters were provided, but these were not checked for syntax!")

def construct_issue_search_query(settings, setting_to_qualifier):
    # Construct the search query
    issue_query = ""
    for setting, encode_setting in setting_to_qualifier.get('issue_level').items():
        issue_query += encode_setting(settings.get(setting))

    return issue_query

def repo_adheres_to_settings(repo, settings):
    for setting, is_valid in SETTING_TO_VALID_PROPERTY.items():
        if not is_valid(settings.get(setting), repo):
            return False
    return True

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

if __name__ == "__main__":
    print("======SETTINGS======")
    settings = load_settings('settings.json')
    verify_settings_values(SETTING_ALLOWED_VALUES)
    issue_query = construct_issue_search_query(settings, SETTING_TO_QUALIFIER)

    # Log-settings
    if settings.get('log-pygithub-requests'):
        if settings.get('log-pygithub-requests-shorten'):
            print('Simple PyGithub logging enabled')
            handler = logging.StreamHandler()
            handler.addFilter(ShortRequestPrinter())

            logger = logging.getLogger("github")
            logger.setLevel(logging.DEBUG)
            logger.addHandler(handler)
        else:
            print("Extended PyGithub logging enabled")
            enable_console_debug_logging()
    else:
        print("PyGithub logging disabled")

    # Load GitHub Login information
    login_settings = load_settings('login.json')

    token_or_username = login_settings.get('login_or_token')
    if token_or_username and login_settings.get('password'):
        # Someone logged in with their username/password combination
        print(f"Logged in as {token_or_username}")
    elif not token_or_username:
        # No user was logged in
        print("No login was made; all reqests will be anonymous (NB: Less requests can be made per minute as an anonymous user!)")
    else:
        # Token login
        print("Logged in using an access token")

    base_url = login_settings.get("base_url")
    if base_url is not None and base_url != STANDARD_API_ENDPOINT:
        print(f"Using Github Enterprise with custom hostname: {base_url}")
    else:
        print(f"Using the standard API endpoint at {STANDARD_API_ENDPOINT}")

    # Initialize PyGithub
    github = Github(per_page=100, **login_settings)
    
    print(f"You provided the following query: {issue_query}")
    print("====================\n")

    @rate_limited_retry_search(github)
    def run_repo_query(repo_name):
        results = github.get_repo(repo_name)
        return results
    
    @rate_limited_retry_search(github)
    def run_search_query(query):
        results = github.search_issues(query)
        return results, results.totalCount

    @rate_limited_retry_search(github)
    def process_search_results(search_results, csv_writer, max_results_to_process):
        for result in search_results[:max_results_to_process]:
            csv_writer.writerow(["/".join(result.url.split("/")[-4:-2]), result.number, result.title, result.state,
                    "issue" if is_issue(result) else "pr",
                    result.created_at, result.updated_at,
                    result.closed_at, result.comments, result.body])

    if not os.path.isfile(settings.get('results-output-file')):
        max_results = settings.get("max-results")
        num_results_so_far = 0
        if max_results < 0:
            max_results = inf

        search_start_time = datetime.now()
        print(f"Search was started at {search_start_time}! \nNB: This might take a while, so grab a drink and relax!\n")

        output_filename = settings.get('results-output-file')
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
                    print(f"Searching for issues created between {current_start_date} and {current_end_date}")
                    # print(f"Starting the search with the following query: {issue_query + date_qualifier}")

                    lazy_results, num_results = run_search_query(issue_query + date_qualifier)
                    
                    if num_results < MAX_RESULTS_PER_SEARCH:
                        max_results_to_process = min(num_results, max_results - num_results_so_far)
                        print(f"> Query returned {num_results} search results! Processing {max_results_to_process} of them...")
                        process_search_results(lazy_results, csv_writer, max_results_to_process)
                        num_results_so_far += max_results_to_process
                        break

                    print("> Query returned too many search results... Halving search space...")
                    
                    new_end_date = current_start_date + (current_end_date - current_start_date)/2

                    if new_end_date == current_end_date:
                        print("> HELP; could not limit query further but there were still >1000 results! D:")
                        exit(1)

                    current_end_date = new_end_date
                
                if current_end_date == final_end_date:
                    break

                # Add 1 second as the created:<datetime>..<datetime> syntax is inclusive for both the start AND end date
                # that's annoying...
                current_start_date = current_end_date + timedelta(seconds=1)
                current_end_date = final_end_date
        
        search_end_time = datetime.now()
        print(f"\nSearch was ended at {search_end_time}, and took {search_end_time - search_start_time} h:mm:ss!")
        print(f"Obtained {num_results_so_far} results, which were output in {output_filename}!")
    
    repo_start_time = datetime.now()
    print(f"Repo Filtering was started at {repo_start_time}! \nNB: This might take an even longer while, so grab two drinks and relax twice as much!\n")

    repos = {}
    with open(settings.get('results-output-file'), newline='', encoding='utf-8') as issue_file:
        csv_reader = csv.DictReader(issue_file)
        for row in csv_reader:
            repo_name = row['repo']
            if repo_name not in repos:
                repo = run_repo_query(repo_name)

                if repo_adheres_to_settings(repo, settings):
                    repos[repo_name] = {
                        'issues': [],
                        'stars': repo.stargazers_count,
                        'forks': repo.forks_count,
                        'watchers': repo.watchers_count,
                        'is_fork': repo.fork,
                        'is_private': repo.private,
                        'is_archived': repo.archived,
                        'estimated_size': repo.size,
                        'created_at': repo.created_at,
                        'updated_at': repo.updated_at,
                        'skipped': False,
                    }
                else:
                    repos[repo_name] = {
                        'skipped': True,
                    }

            if not repos[repo_name]['skipped']:
                repos[repo_name]['issues'].append({'number': row['number'], 'created_at': row['created_at']})

    output_filename = settings.get('results-output-file')
    with open(output_filename, 'w', newline='', encoding='utf-8') as output_file:
        file.write(json.dumps(repos))

    repo_end_time = datetime.now()
    print(f"\nSearch was ended at {repo_end_time}, and took {repo_end_time - repo_end_time} h:mm:ss!")
    print(f"Obtained {len(repos)} unique repositories, which were output in {output_filename}!")
