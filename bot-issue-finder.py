import json
from github import Github
from rate_limit_retry import rate_limited_retry_search

# Maximum number of entries that GitHub returns per search
# If we obtain more results than this value, our search space is too large
# and we need to narrow down. (GitHub only returns 1000 results per search)
MAX_RESULTS_PER_SEARCH = 1000

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
        "type":                     lambda x: f"type:{x} " if x != "any" else "",
        "state":                    lambda x: f"state:{x} " if x != "any" else "",
        "language":                 lambda x: f"language:{x} " if x != "any" else "",
        "additional-issue-query":   lambda x: f"{x} " if x != "" else ""
    },
    'repo_level': {
        # TODO
    }
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


# per_page=100 (to limit the number of API calls a bit further)
# https://github.com/PyGithub/PyGithub/issues/553#issuecomment-546378228


if __name__ == "__main__":
    settings = load_settings('settings.json')
    verify_settings_values(SETTING_ALLOWED_VALUES)
    issue_query = construct_issue_search_query(settings, SETTING_TO_QUALIFIER)

    # Load GitHub Login information
    login_settings = load_settings('login.json')

    token_or_username = login_settings.get('login_or_token')
    if token_or_username and login_settings.get('password'):
        # Someone logged in with their username/password combination
        print(f"Logged in as {token_or_username}")
    elif not token_or_username:
        # No user was logged in
        print("No login was made; all reqests will be anonymous (NB: Less requests can be made per minute)")
    else:
        # Token login
        print("Logged in using an access token")

    base_url = login_settings.get("base_url")
    if base_url is not None and base_url != "https://api.github.com":
        print(f"Using Github Enterprise with custom hostname: {base_url}")
    else:
        print("Using the standard API endpoint at https://api.github.com")

    # Initialize PyGithub
    github = Github(per_page=100, **login_settings)

    @rate_limited_retry_search(github)
    def run_search_query(query):
        return github.search_issues(query)

    @rate_limited_retry_search(github)
    def process_search_results(search_results):
        for result in search_results:
            print(result)

    print(f"Starting the search with the following query: {issue_query}")
    lazy_results = run_search_query(issue_query)

    # TODO: Handle cases where the totalcount >= 1000 (as this means we're missing info; limit the search space!)
    print(lazy_results.totalCount)

    process_search_results(lazy_results)
    
