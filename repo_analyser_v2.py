import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# Remove uncloned repositories from a dataframe
def remove_uncloned(df):
    return df[df["cloned"] == True]


# Number of commits before todo[bot] histogram
def plot_commits_pre(settings, logger):
    input_filename = "output/total_repo_information.csv"
    df = pd.read_csv(input_filename)

    df = remove_uncloned(df)
    df = df[(df['pre_earliest_issue_commits'] < 100)]
    print(df)

    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=df['pre_earliest_issue_commits']
    ))

    fig.update_layout(
        xaxis_title_text='Number of Commits (before todo[bot])', # xaxis label
        yaxis_title_text='Number of Repositories', # yaxis label
        bargap=0.1, # gap between bars of adjacent location coordinates
        bargroupgap=0.05, # gap between bars of the same location coordinates
        xaxis_tick0 = 0,
        xaxis_dtick = 10
    )
    fig.show()
    fig.write_image("output/images/pre_commits.svg")


# Number of commits per TODO-comment (pre- and post-bot)
def plot_pre_post_conclusion(settings, logger):
    input_filename = "output/total_repo_information.csv"
    df = pd.read_csv(input_filename)
    pd.set_option("display.precision", 20)
    df = remove_uncloned(df)
    df["num_pre_per_commits"] = df['pre_earliest_issue_commits'] / df['num_pre_issues']
    df["num_post_per_commits"] = (df['total_commits'] - df['pre_earliest_issue_commits']) /  df['num_post_issues']
    print(df)

    fig = go.Figure(data=go.Scattergl(
        x = df['num_pre_per_commits'],
        y = df['num_post_per_commits'],
        mode='markers',
        marker=dict(
            size=5,
            line_width=1,
        )
    ))

    fig.update_xaxes(type="log")
    fig.update_yaxes(type="log")

    fig.update_xaxes(range=[-1,3.4])
    fig.update_yaxes(range=[-1,3.4])

    fig.update_layout(
        yaxis_title_text="Number of commits per 'TODO'-comment (post)",
        xaxis_title_text="Number of commits per 'TODO'-comment (pre)",
    )
    fig.show()
    fig.write_image("output/images/scatterplot_pre_post_todos.svg")


# Histogram total number of TODO-comments (pre- and post-todo[bot])
def plot_pre_post_todo(settings, logger):
    input_filename = "output/total_repo_information.csv"
    df = pd.read_csv(input_filename)

    df = remove_uncloned(df)
    # df = df[df["num_pre_issues"] <= 350]
    df["num_total_issues"] = df['num_pre_issues'] + df['num_post_issues']

    fig = px.histogram(
        x=df['num_total_issues'], log_y=True
    )
    fig.update_traces(xbins_size=1)

    fig.update_layout(
        yaxis_title_text="Number of Repositories (log)",
        xaxis_title_text="Number of total 'TODO'-comments",
        # yaxis_type='log',
        bargap=0.1, # gap between bars of adjacent location coordinates
        bargroupgap=0.05, # gap between bars of the same location coordinates
        xaxis_tick0 = 0,
        xaxis_dtick = 25,
        # barmode = 'stack',
    )
    fig.show()
    fig.write_image("output/images/issues_pre_post.svg")


# Histogram TODO-comments before todo[bot]
def plot_pre_todo(settings, logger):
    input_filename = "output/total_repo_information.csv"
    df = pd.read_csv(input_filename)
    df = remove_uncloned(df)
    df = df.sort_values(by=["num_pre_issues"])

    df = df[df["num_pre_issues"] <= 350]
    print(df)
    df = df[df["pre_earliest_issue_commits"] > 1]
    print(df)

    fig = px.histogram(
        x=df['num_pre_issues'], log_y=True
    )
    fig.update_traces(xbins_size=1)

    fig.update_layout(
        yaxis_title_text="Number of Repositories (log)",
        xaxis_title_text="Number of 'TODO'-comments before todo[bot] was adopted",
        # yaxis_type='log',
        bargap=0.1, # gap between bars of adjacent location coordinates
        bargroupgap=0.05, # gap between bars of the same location coordinates
        xaxis_tick0 = 0,
        xaxis_dtick = 25,
        # barmode = 'stack',
    )

    fig.show()
    fig.write_image("output/images/issues_pre.svg")


# Repo earliest todo issue histogram
def plot_repo_creation_updated(settings, logger):
    input_filename = "output/total_repo_information.csv"
    df = pd.read_csv(input_filename)
    df = df[df["cloned"] == True]

    fig = go.Figure()
    fig.add_trace(go.Histogram(x=df["earliest_todo_issue"], name="Created", cumulative_enabled=False))

    fig.update_traces(
        xbins_end = '2021-01-01 00:00',
        xbins_size = 'M1',
        # xbins_start = '2017-01-01 00:00',
        # opacity=0.5,
    )

    fig.update_layout(
        bargap=0,
        yaxis_title_text="Number of Repositories",
        xaxis_title_text="Date",
        barmode='overlay',
    )
    fig.show()
    fig.write_image("output/images/repo_first_todo.svg")


# Issue creation date histogram
def plot_issues_by_date(settings, logger):
    input_filename = "output/issue-results_september_09.csv"
    df = pd.read_csv(input_filename)
    df = df.drop_duplicates()

    fig = go.Figure()
    fig.add_trace(go.Histogram(x=df["created_at"], name="Amount"))

    fig.update_traces(
        xbins_end = '2021-01-01 00:00',
        xbins_size = 'M1',
        xbins_start = '2017-01-01 00:00',
        # opacity=0.5,
    )

    fig.update_layout(
        bargap=0,
        yaxis_title_text="New TODO-issues",
        xaxis_title_text="Issue Creation Date",
        barmode='overlay',
    )
    fig.show()
    fig.write_image("output/images/issues_by_date_pre.svg")


    input_filename = "output/issues_pre_bot_no_duplicates.csv"
    df2 = pd.read_csv(input_filename)
    fig = go.Figure()
    fig.add_trace(go.Histogram(x=df2["commit_date"], name="Pre todo[bot]"))

    fig.update_traces(
        # xbins_end = '2017-01-01 00:00',
        xbins_size = 'M1',
        # xbins_start = '2017-01-01 00:00',
    )

    fig.update_layout(
        bargap=0.05,
        yaxis_title_text="New TODO-comments",
        xaxis_title_text="Date",
        barmode='stack',
    )
    fig.show()
    fig.write_image("output/images/issues_by_date_post.svg")

    fig.add_trace(go.Histogram(x=df["created_at"], name="Post todo[bot]"))
    fig.update_layout(
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01
        )
    )
    fig.show()
    fig.write_image("output/images/issues_by_date_both.svg")


# Number of TODO-issues per repo
def plot_issues(settings, logger):
    input_filename = "output/total_repo_information.csv"
    df = pd.read_csv(input_filename)
    df = remove_uncloned(df)


    fig = px.histogram(
        x=df['num_post_issues'], log_y=True
    )
    fig.update_traces(xbins_size=1)

    fig.update_layout(
        yaxis_title_text="Number of Repositories (log)",
        xaxis_title_text="Number of Issues",
        yaxis_type='log',
        bargap=0.1, # gap between bars of adjacent location coordinates
        bargroupgap=0.05, # gap between bars of the same location coordinates
        xaxis_tick0 = 0,
        xaxis_dtick = 25,
        # barmode = 'stack',
    )

    fig.show()
    fig.write_image("output/images/issues_pre.svg")


# Commits Histogram
def plot_commits(settings, logger):
    input_filename = "output/total_repo_information.csv"
    df = pd.read_csv(input_filename)

    df = remove_uncloned(df)
    # df = df[(df['total_commits'] < 500)]
    print(df)

    fig = go.Figure()
    # fig.add_trace(go.Histogram(
    #     x=df['pre_earliest_issue_commits'],
    #     name='Commits before todo[bot]',
    # ))
    fig.add_trace(go.Histogram(
        x=df['total_commits'] #- df['pre_earliest_issue_commits']
        ,
        name='Commits after todo[bot]',
    ))

    fig.update_layout(
        xaxis_title_text='Number of Commits', # xaxis label
        yaxis_title_text='Number of Repositories (log)', # yaxis label
        yaxis_type='log',
        bargap=0.1, # gap between bars of adjacent location coordinates
        bargroupgap=0.05, # gap between bars of the same location coordinates
        xaxis_tick0 = 0,
        xaxis_dtick = 5000,
    )

    fig.show()
    fig.write_image("output/images/total_commits_limited_stacked.svg")


# Usage numbers; how many repositories with todo[bot] does each GitHub user have?
def find_usage_numbers(settings, logger):
    input_filename = "output/total_repo_information.csv"
    df = pd.read_csv(input_filename)

    df = df[["repo"]]

    df[['owner', 'repo']] = df['repo'].str.split('/', n=1, expand=True)
    print(df)

    df = df.groupby(by=["owner"]).size().reset_index(name='num_repos')
    df = df.sort_values(by=["num_repos"])
    print(df)

    fig = px.histogram(df, x="num_repos", log_y=True)

    fig.update_traces(xbins_size=1)
    fig.update_layout(
        bargap=0.05,
        yaxis_title_text="Number of Repository Owners (log)",
        xaxis_title_text="Number of Owned Repositories",
        xaxis_tick0 = 0,
        xaxis_dtick = 5,
    )
    fig.show()
    fig.write_image("output/images/usage.svg")


# Histogram of stars/forks/watchers
def plot_stars_forks_watchers_hist(settings, logger):
    input_filename = "output/total_repo_information.csv"
    df = pd.read_csv(input_filename)

    df = remove_uncloned(df)

    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=df['stars'],
        name='Stars', # name used in legend and hover labels
        # marker_color='#EB89B5',
    ))
    fig.add_trace(go.Histogram(
        x=df["forks"],
        name='Forks',
        # marker_color='#330C73',
    ))
    fig.add_trace(go.Histogram(
        x=df["watchers"],
        name='Watchers',
        # marker_color='#330C73',
    ))

    fig.update_layout(
        xaxis_title_text='Number of Repositories', # xaxis label
        yaxis_title_text='Amount (log)', # yaxis label
        yaxis_type='log',
        bargap=0.1, # gap between bars of adjacent location coordinates
        bargroupgap=0.05, # gap between bars of the same location coordinates
        xaxis_tick0 = 0,
        xaxis_dtick = 2500,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="right",
            x=0.99
        )
    )

    fig.show()
    fig.write_image("output/images/hist_stars_forks_watchers_full.svg")

    print(df)
    filter_val = 25
    df = df[(df['forks'] < filter_val) & (df['stars'] < filter_val) & (df['watchers'] < filter_val)]

    print(df)

    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=df['stars'],
        name='Stars', # name used in legend and hover labels
    ))
    fig.add_trace(go.Histogram(
        x=df["forks"],
        name='Forks',
    ))
    fig.add_trace(go.Histogram(
        x=df["watchers"],
        name='Watchers',
    ))

    fig.update_layout(
        xaxis_title_text='Amount', # xaxis label
        yaxis_title_text='Number of Repositories (log)', # yaxis label
        yaxis_type='log',
        bargap=0.4, # gap between bars of adjacent location coordinates
        bargroupgap=0.05, # gap between bars of the same location coordinates
        xaxis_tick0 = 0,
        xaxis_dtick = 5,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="right",
            x=0.99
        )
    )
    fig.show()
    fig.write_image("output/images/hist_stars_forks_watchers_small.svg")


# Scatterplot of forks, stars, and watchers
def plot_stars_forks_watchers_scatter(settings, logger):
    input_filename = "output/total_repo_information.csv"
    df = pd.read_csv(input_filename)

    df = remove_uncloned(df)

    df['stars'] = df['stars'].apply(lambda x: x+1)
    df['forks'] = df['forks'].apply(lambda x: x+1)
    df['watchers'] = df['watchers'].apply(lambda x: x+1)

    df = df[df["stars"] < 20000]

    fig = go.Figure(data=go.Scattergl(
        x = df['stars'],
        y = df['forks'],
        mode='markers',
        marker=dict(
            size=df['watchers'].apply(lambda x: max(x/10, 5)),
            line_width=1,
            # A colorscale for the 3rd dimension (watchers) was not nice
            # color=df['watchers'], #set color equal to a variable
            # colorscale='Viridis_r', # one of plotly colorscales
            # # colorscale='Turbid', # one of plotly colorscales
            # showscale=True
        )
    ))

    fig.update_xaxes(type="log")
    fig.update_yaxes(type="log")

    fig.update_layout(
        yaxis_title_text="Forks (log + 1)",
        xaxis_title_text="Stars (log + 1)",
    )
    fig.show()
    fig.write_image("output/images/scatterplot_stars_forks_watchers.svg")

    # A density-contour plot did not seem useful for this data
    # fig = px.density_contour(df, x=df["stars"], y=df["forks"])
    # fig.update_traces(contours_coloring="fill", contours_showlabels = True)


