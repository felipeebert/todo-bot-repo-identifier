# Files
The following files contain different kinds of information:
- `total_repo_information.csv`: Contains characteristics (e.g., number of stars, date of the earliest TODO-issue, total number of TODO-issues) for all repositories in which todo\[bot] has created at least one issue. Data does not contain duplicates. Data contains repositories that were not cloned, but these can be filtered out with help of the `cloned`-column.
- `issues_pre.csv`: Issues that would have been created by todo\[bot] for TODO-comments made in commits before the bot was actually introduced to a repository. Issues were identified using a local copy of todo\[bot] and passing commit diffs to it. Data does not contain duplicates.
- `issues_post.csv`: Issues created by todo\[bot], including those for uncloned repositories. Data does not contain duplicates.

# Logs
Logs are included in the `/logs` folder for the following tasks:
- Cloning: Repositories were cloned to an external hard drive. This process crashed three times (twice because of too long filenames, which Windows cannot handle. Once because cloning took too long). Each of the following files describes one of four runs.
    * `bot_cloner_run1.log`
    * `bot_cloner_run2.log`
    * `bot_cloner_run3.log`
    * `bot_cloner_run4.log`
- Identifying issues created by todo\[bot], and querying characteristics of repositories of these issues. Files:
    * `bot_issue_and_repo_finder.log`
- Identifying issues created before todo\[bot] was introduced to a repository. Contains a log for the underlying node process (on which a local copy of todo\[bot] ran), which describes which TODO-comments the bot found for which commits (diffs) in which repositories. This log also indicates whether the commit (diff) was not identified (e.g., because it was too large). The other log describes the progress of commit diff generation (which were used by the aforementioned task).
    * `bot_pre_finder_node.log`
    * `bot_pre_finder_diffs.log`
