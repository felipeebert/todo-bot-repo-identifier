import json
import os
from datetime import datetime, timedelta

from pygit2 import clone_repository

from bot_issue_finder import load_settings, verify_settings_values, SETTING_ALLOWED_VALUES

if __name__ == "__main__":
    print("======SETTINGS======")
    settings = load_settings('settings.json')
    verify_settings_values(settings, SETTING_ALLOWED_VALUES)
    print("====================\n")
    output_path = settings.get('download-output-path-repo')

    input_filename = settings.get('results-repo-output-file')
    with open(input_filename, newline='', encoding='utf-8') as input_file:
        repos = json.load(input_file)

    repo_start_time = datetime.now()
    print(f"Repo cloning started at {repo_start_time}! Attempting to clone {len(repos)} repos.\nThis is the last step and will take the longest!\n")

    cnt = 0
    msg_cnt = 0
    last_successful_repo = None
    try:
        for name, repo in repos.items():
            if not repo.get('skipped'):
                repo = clone_repository(repo.get('clone_url'), os.path.join(output_path, name))
                cnt += 1
                msg_cnt += 1
                last_successful_repo = name

                if msg_cnt >= 50:
                    msg_cnt = 0
                    print(f"Finished cloning {cnt}/{len(repos)} repositories...")

    except Exception as e:
        print(f"Unexpected Exception! {e}")
        print(type(e))
        print(f"Last repo that was successfully cloned: {last_successful_repo}")

    repo_end_time = datetime.now()
    print(f"\nCloning was ended at {repo_end_time}, and took {repo_end_time - repo_start_time} h:mm:ss!")
    print(f"Obtained {len(repos)} unique repositories, which were output in {output_path}!")
