import csv
import json
import logging
import os

from bot_issue_finder import load_settings, verify_settings_values, SETTING_ALLOWED_VALUES

if __name__ == "__main__":
    print("======SETTINGS======")
    settings = load_settings('settings.json')
    verify_settings_values(settings, SETTING_ALLOWED_VALUES)

    print("====================\n")

    input_filename = settings.get('results-repo-output-file')
    with open(input_filename, newline='', encoding='utf-8') as input_file:
        repos = json.load(input_file)

    attribute_fn = lambda repo: repo.get('stars')

    most_stars = [
        ('<PLACEHOLDER>', -1), ('<PLACEHOLDER>', -1), ('<PLACEHOLDER>', -1),
        ('<PLACEHOLDER>', -1), ('<PLACEHOLDER>', -1), ('<PLACEHOLDER>', -1),
        ('<PLACEHOLDER>', -1), ('<PLACEHOLDER>', -1), ('<PLACEHOLDER>', -1),
        ('<PLACEHOLDER>', -1), ('<PLACEHOLDER>', -1), ('<PLACEHOLDER>', -1),
        ('<PLACEHOLDER>', -1), ('<PLACEHOLDER>', -1), ('<PLACEHOLDER>', -1),
        ('<PLACEHOLDER>', -1), ('<PLACEHOLDER>', -1), ('<PLACEHOLDER>', -1),
        ('<PLACEHOLDER>', -1), ('<PLACEHOLDER>', -1), ('<PLACEHOLDER>', -1),
        ('<PLACEHOLDER>', -1), ('<PLACEHOLDER>', -1), ('<PLACEHOLDER>', -1),
        ('<PLACEHOLDER>', -1), ('<PLACEHOLDER>', -1), ('<PLACEHOLDER>', -1),
        ('<PLACEHOLDER>', -1), ('<PLACEHOLDER>', -1), ('<PLACEHOLDER>', -1),
    ]

    for name, repo in repos.items():
        if not repo.get('skipped'):
            for i in range(len(most_stars)):
                star_repo, stars = most_stars[i]
                if stars < attribute_fn(repo):
                    most_stars.insert(i, (name, attribute_fn(repo)))
                    del most_stars[-1]
                    break

    
    for (name, stars) in most_stars:
        print(f'{name}: {stars}')
