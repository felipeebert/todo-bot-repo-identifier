import json
import datetime
import os
import itertools

from string import Template

import pandas as pd
from pygit2 import Repository, Commit, GIT_SORT_TIME, GIT_SORT_REVERSE
from pygit2.errors import GitError


def obtain_pre_post_data(settings, logger):
    """
        Merge repository characteristics and TODO-comment numbers together in a single
        file for easy usage
    """
    # Obtain amount of pre issues per repo
    pre_filename = settings.get('results-todo-comments-pre-bot-output-file')
    df_pre = pd.read_csv(pre_filename)
    df_pre = df_pre.groupby(by=["repo"]).size().reset_index(name='num_pre_issues')

    # Obtain post issues per repo
    post_filename = settings.get('results-issues-output-file')
    df_post = pd.read_csv(post_filename)
    df_post = df_post.drop_duplicates()
    df_post = df_post.groupby(by=["repo"]).size().reset_index(name='num_post_issues')

    # Merge the pre/post-issue info into a single dataframe
    df_merged = df_pre.merge(df_post, on="repo", how="right", sort=True)
    df_merged = df_merged.fillna(0)

    # Obtain star, fork, etc. info from _all_ repositories
    filename = settings.get('results-repos-output-file')
    df_data = pd.read_json(filename, orient='index').rename_axis("repo").reset_index()
    df_data = df_data.drop(["skipped", "error", "issues"], axis="columns")

    # Obtain number of commits, etc. from _cloned_ repositories
    df_cloned_data = pd.read_csv(settings.get('results-clone-info-output-file'))
    df_cloned_data["earliest_todo_issue"] = df_cloned_data["earliest_todo_issue"].apply(lambda x: datetime.datetime.utcfromtimestamp(x).isoformat(sep=" "))

    # Merge the two together
    df_cloned_data = df_cloned_data.merge(df_data, on="repo", how="right", sort=True)

    # Set correct clone information for uncloned repositories (they have more data missing as well, which is fine)
    df_cloned_data = df_cloned_data.fillna(value={'cloned': False})

    # Merge repo info and pre/post-issue info together
    df_merged = df_merged.merge(df_cloned_data, on="repo", how="left", sort=True)

    df_merged.to_csv(settings.get('results-merged-output-file'), index=False)



def remove_pre_duplicates(settings, logger):
    """
        Remove duplicates from all TODO-comments that were identified
    """

    pre_filename = settings.get('results-todo-comments-pre-bot-output-file')
    df_pre = pd.read_csv(pre_filename)

    # Remove duplicates for issues from the same repo that have the same title.
    #   Sort first to keep the earlist commit date
    #   Issues: 34948 -> 24396
    df_pre = df_pre.sort_values('commit_date', ascending=True)
    df_pre = df_pre.drop_duplicates(subset=["repo", "owner", "title"]).sort_index()

    df_pre["repo"] = df_pre["repo"] + "/" + df_pre["owner"]
    del df_pre["owner"]

    # Obtain post-bot issues (i.e., those that are actually crated by the bot on GitHub)
    post_filename = settings.get('results-issues-output-file')
    df_post = pd.read_csv(post_filename)
    df_post = df_post.drop_duplicates()

    df_post["commit_date"] = df_post["created_at"]
    df_post = df_post[["repo", "title", "body", "commit_date"]]

    # Indicate from which dataset the issues originated
    df_post["pre"] = False
    df_pre["pre"] = True

    # Remove issues that were already in the post-batch (i.e., those with the same title from the same repo)
        # Issues: 24396 -> 20809
    df_merged = df_pre.append(df_post)
    df_merged = df_merged.drop_duplicates(subset=["repo", "title"], keep=False)

    # Only keep the issues in the pre-batch
    df_merged = df_merged[df_merged["pre"] == True]
    del df_merged["pre"]
    df_merged = df_merged.sort_index()

    df_merged.to_csv(pre_filename, index=False)


def obtain_cloned_repos(settings, logger):
    """
        Obtains information (e.g. number of commits) of the cloned repositories
    """
    input_filename = settings.get('results-repos-output-file')
    with open(input_filename, newline='', encoding='utf-8') as input_file:
        repos = json.load(input_file)

    # Obtain earliest todo-issue (discard all other data)
    repos = map(lambda kv: (kv[0],
        datetime.datetime.fromisoformat(
            min(kv[1].get('issues'), key=lambda y: y.get('created_at'), default=None).get('created_at')
            # Read dates are in UTC
            ).replace(tzinfo=datetime.timezone.utc).timestamp()
        ),
        repos.items())
    repos = dict(repos)

    cloned_repo_lst = []

    path = settings.get("download-output-path-repo")
    with os.scandir(path) as it:
        for entry in it:
            if entry.is_dir():
                # Iterate over repo folders (of a single author)
                with os.scandir(os.path.join(path, entry.name)) as it2:
                    for repo in it2:
                        if repo.is_dir():
                            repo_name = entry.name + "/" + repo.name
                            print("Handling " + repo_name)
                            repo_path = os.path.join(path, entry.name, repo.name)
                            r = Repository(repo_path)
                            earliest_todo_issue = repos.get(repo_name)
                            total_commits = 0
                            pre_commits = 0
                            if earliest_todo_issue is not None:
                                repos[repo_name] = [0, 0]
                                for commit in r.walk(r.head.target, GIT_SORT_TIME | GIT_SORT_REVERSE):
                                    if commit.commit_time < earliest_todo_issue:
                                        pre_commits += 1
                                    total_commits += 1

                            cloned_repo_lst.append( {
                                "repo": repo_name,
                                "cloned": True,
                                "total_commits": total_commits,
                                "earliest_todo_issue": earliest_todo_issue,
                                "pre_earliest_issue_commits": pre_commits,
                            })
    df_cloned_repos = pd.DataFrame(cloned_repo_lst, columns=["repo", "cloned", "total_commits", "earliest_todo_issue", "pre_earliest_issue_commits"])
    df_cloned_repos.to_csv(settings.get('results-clone-info-output-file'), index=False)


def find_pre_bot_issues(settings, logger):
    """
        For each cloned repo's commits, pass them to a local (modified) copy of todo[bot] so that
        it can identify TODO-comments in those.
    """
    input_filename = settings.get('results-repos-output-file')
    with open(input_filename, newline='', encoding='utf-8') as input_file:
        repos = json.load(input_file)

    # Obtain (repo, earliest_todo_issue) pairs
    repos = map(lambda kv: (kv[0],
        datetime.datetime.fromisoformat(
            min(kv[1].get('issues'), key=lambda y: y.get('created_at'), default=None).get('created_at')
            # Read dates are in UTC
            ).replace(tzinfo=datetime.timezone.utc).timestamp()
        ),
        repos.items())
    repos = dict(repos)

    # Iterate over all cloned repos
    path = settings.get("download-output-path-repo")
    with os.scandir(path) as it:
        for entry in it:
            if entry.is_dir():
                # Iterate over repo folders (of a single author)
                with os.scandir(os.path.join(path, entry.name)) as it2:
                    for repo in it2:
                        if repo.is_dir():
                            repo_name = entry.name + "/" + repo.name
                            logger.debug("Handling " + repo_name)
                            repo_path = os.path.join(path, entry.name, repo.name)

                            r = Repository(repo_path)
                            earliest_todo_issue = repos.get(repo_name)

                            if earliest_todo_issue is not None:
                                # Iterate over all this repo's commits
                                for commit in r.walk(r.head.target, GIT_SORT_TIME | GIT_SORT_REVERSE):
                                    # Ignore post-bot commits + merge commits
                                    # NB: The initial commit is ignored as well

                                    if commit.commit_time < earliest_todo_issue and commit.parents and len(commit.parents) <= 1:
                                        commit_dt = datetime.datetime.utcfromtimestamp(commit.commit_time).isoformat()
                                        logger.debug(f"> Handling commit {str(commit.hex)} ({commit_dt})")
                                        os.system(f'node {settings.get('modified-todo-bot-install-path')} -o "{entry.name}" -r "{repo.name}" -s {commit.hex} -e "{commit_dt}" >> bot_pre_bot_finder_node.log')


def generate_diffs_and_testcases(settings, logger):
    """
        Generate a diff for each cloned repo's commits.
        Also generate jest 'testcases' for each cloned repo's commits.
        These testcases do not test todo[bot]'s behaviour, but instead
        output TODO-comments found in each of these commits.

        Unfortunately, these testcases run WAY too slow when using a lot of them.
        The generated diffs can still be used elsewhere though.
    """

    input_filename = settings.get('results-repos-output-file')
    with open(input_filename, newline='', encoding='utf-8') as input_file:
        repos = json.load(input_file)

    # Obtain (repo, earliest_todo_comment) pairs
    repos = map(lambda kv: (kv[0],
        datetime.datetime.fromisoformat(
            min(kv[1].get('issues'), key=lambda y: y.get('created_at'), default=None).get('created_at')
            # Read dates are in UTC
            ).replace(tzinfo=datetime.timezone.utc).timestamp()
        ),
        repos.items())
    repos = dict(repos)

    js_template = None
    with open('./templates/testcase.js', 'r', encoding="utf-8") as f:
        js_template = Template(f.read())
    with open('./templates/base_test_pre.js', 'r', encoding="utf-8") as f:
        js_template_pre = f.read()
    with open('./templates/base_test_post.js', 'r', encoding="utf-8") as f:
        js_template_post = f.read()

    path = settings.get("download-output-path-repo")
    test_output_path = settings.get("download-output-path-repo")
    diff_output_path = settings.get("diffs-output-path")
    with os.scandir(path) as it:
        for entry in it:
            if entry.is_dir():
                # Iterate over repo folders (of a single author)
                with os.scandir(os.path.join(path, entry.name)) as it2:
                    for repo in it2:
                        if repo.is_dir():

                            # Create "test" file for each repo, containing all that repo's commits
                            test_js_filename = f"{test_output_path}/{entry.name}/{repo.name}.test.js"
                            os.makedirs(os.path.dirname(test_js_filename), exist_ok=True)
                            with open(test_js_filename, "a", encoding="utf-8") as testcase_file:
                                testcase_file.write(js_template_pre)

                                repo_name = entry.name + "/" + repo.name
                                logger.debug("Handling " + repo_name)
                                repo_path = os.path.join(path, entry.name, repo.name)
                                r = Repository(repo_path)
                                earliest_todo_issue = repos.get(repo_name)

                                if earliest_todo_issue is not None:
                                    for commit in r.walk(r.head.target, GIT_SORT_TIME | GIT_SORT_REVERSE):
                                        # Ignore post-bot commits + merge commits
                                        # the initial commit is ignored as well

                                        if commit.commit_time < earliest_todo_issue and commit.parents and len(commit.parents) <= 1:
                                            commit_dt = datetime.datetime.utcfromtimestamp(commit.commit_time).isoformat()
                                            logger.debug(f"Handling commit {str(commit.hex)} ({commit_dt})")

                                            prev_commit = commit.parents[0]
                                            diff = prev_commit.tree.diff_to_tree(commit.tree)

                                            if diff.patch:
                                                # Output the diff
                                                filename = f"{diff_output_path}/{entry.name}/{repo.name}/{commit.hex}.diff"
                                                os.makedirs(os.path.dirname(filename), exist_ok=True)
                                                with open(filename, "w", encoding="utf-8") as diff_file:
                                                    diff_file.write(diff.patch)

                                                # Add the commit to the fake testcase
                                                result = js_template.substitute({
                                                    'HEAD_COMMIT_SHA': commit.hex,
                                                    'DATE': commit.commit_time,
                                                    'HEAD_COMMIT_AUTHOR_USERNAME': commit.author.name,
                                                    'REPO_NAME': repo.name,
                                                    'OWNER_USERNAME': entry.name,
                                                    'DIFF_FILENAME': filename,
                                                })
                                                testcase_file.write(result)
                                testcase_file.write(js_template_post)
