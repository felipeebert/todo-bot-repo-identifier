# todo-bot-repo-identifier
This repository contains the scraping code that was used to identify and clone all repositories for which Jason Etcovitch's [todo[bot]](https://github.com/apps/todo) has created at least one issue.

This is done in three phases:
1. Identify the issues using GitHub's search API.
1. Identify the repositories correpsonding to these issues, and extract additional information (such as the number of stars), using the GitHub standard API.
1. Clone these repositories.

Which issues and repositories are identified, and which repositories are cloned is affected by the settings.

# How to Run
1. Clone the repository
1. Create a new Virtual Environment using `python -m venv myvenv`
1. Activate the Virtual Environment that you just created using `myvenv\Scripts\activate` on Windows, or `venv/bin/activate` on POSIX
1. Install the dependencies using `pip install -r requirements.txt`
1. Run the code using `python main.py`

NB: In case this code was run earlier, then the issue identification and/or repository identification steps might have already been completed. In this case, these phases are skipped and the results from the relevant files are used instead of fetching them again from GitHub's API.

# Settings
The `settings.json` contains the following information:
- `bot-name`: The name of the bot or GitHub user of which we want to fetch its created issues.
- `min-stars`: The minimum number of stars a repository should have before it is cloned.
- `min-forks`: The minimum number of forks a repository should have before it is cloned.
- `ignore-forks`: Whether repositories that are a fork should not be cloned.
- `ignore-private-repos`: Whether private repositories should not be cloned.
- `ignore-archieved-repos`: Whether archived repositories should not be cloned.
- `type`: Either `issue`, `pr`, or `any`. Can be used to limit the fetching to only issues/PRs.
- `state`: Either `open`, `closed`, or `any`. Can be used to limit the fetching to only open/closed issues/PRs.
- `results-issues-output-file`: The file in which the identified issues/PRs should be placed. Output is in CSV file format.
- `results-repos-output-file`: The file in which the identified repositories should be placed. Output is in JSON file format.
- `results-todo-comments-pre-bot-output-file`: The file containing issues that would have been created for TODO-comments made before todo\[bot] was introduced to a repository. Output is in CSV file format.
- `download-output-path-repo`: The location in which cloned repositories should be placed.
- `skip-cloning`: Whether the cloning step should be skipped.
- `results-clone-info-output-file`: File containing some information of the cloned repositories.
- `results-merged-output-file`: File containing information on the identified repositories. **This is the final output.**
- `fake-testcase-path`: Folder in which generated 'testcases' will be placed. These 'testcases' are not actually used, but (given enough processing time) could signify which issues would be created for a certain diff.
- `diffs-output-path`: Output folder for diffs of commits of repositories in which at least one TODO-issue was created.
- `modified-todo-bot-install-path`: Location in which the modified todo\[bot] is installed. This is needed to identify issues for TODO-comments made before the bot was introduced to a repository.
- `language`: Filters the issue/PR search to repositories that use this language. Use `any` for any language.
- `start-date`: The date from which we start identifying issues/PRs. Providing a tighter timeframe makes the code run faster.
- `end-date`: The date at which we stop identifying issues/PRs.
- `additional-issue-query`: Additional query using GitHub's search syntax to limit the issue/PRs search even further. E.g. `assignee:EricTRL`
- `max-results`: The maximum number of issues/PRs to identify.
- `loglevels`: Dictionary containing the loglevels for each of the three phases (issue identifying, repository identifying, repository cloning).
- `logoutputs`: File path to where the logs should be stored for each of the three phases. Can be `null` to output to the terminal.
- `log-pygithub-requests`: If `true`, outputs the requests that PyGithub makes to the GitHub API. Can be useful for debugging.
- `shorten-pytightub-requests`: If `true`, reduces the amount of information that is logged for PyGithubs API requests, limiting it to just the accessed API endpoint.

# Modified copy of todo\[bot]
In case you wish to reproduce the results, extract the included zip to a folder of choice and set `modified-todo-bot-install-path` to that same location.

NB: If changing the `diffs-output-path` setting or `results-todo-comments-pre-bot-output-file` setting, then also change Line 15 in `bin/todo.js` and Line 21 in `lib/utils/get_diff.js` of the modified todo\[bot]-code respectively, as these do not pull these values from the settings.


# Login Settings
The GitHub API provides a larger rate limit for authenticated requests. See `/login-examples` for examples to authenticate. This login data is passed to PyGithub.
