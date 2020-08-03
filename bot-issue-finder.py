import json

# Maximum number of entries that GitHub returns per search
# If we obtain more results than this value, our search space is too large
# and we need to narrow down. (GitHub only returns 1000 results per search)
MAX_RESULTS_PER_SEARCH = 1000

# Load search settings
settings = {}
with open('settings.json') as json_file:
    settings = json.load(json_file)

# Some settings only allow specific values
setting_allowed_values = {
    "type":     ["any", "pr", "issue"],
    "state":    ["any", "open", "closed"],
}

# Ensure that all settings have valid values
for setting, allowed_values in setting_allowed_values.items():
    if settings.get(setting) not in allowed_values:
        raise ValueError(   f"Invalid setting passed for <{setting}>. Got <{settings.get(setting)}>, "
                            f"but expected one of <{', '.join(allowed_values)}>")

# Shorthand notation for converting settings to GitHub search qualifiers
setting_to_qualifier = {
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

# Construct the search query
issue_query = ""
for setting, encode_setting in setting_to_qualifier.get('issue_level').items():
    issue_query += encode_setting(settings.get(setting))

print(issue_query)


# per_page=100 (to limit the number of API calls a bit further)
# https://github.com/PyGithub/PyGithub/issues/553#issuecomment-546378228
