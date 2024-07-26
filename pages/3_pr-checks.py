# Import python packages
import random
import streamlit as st
import pandas as pd
from ghapi.all import GhApi
import os
import re
from dotenv import load_dotenv

load_dotenv()

# Load the table as a dataframe using the Snowpark Session.
# Returns a Pandas DataFrame
@st.cache_data
def load_table():
    return conn.query("SELECT * from ISSUES_V1 WHERE group_public_id='86d8f5d1-de02-4e81-b230-2c7038f00685';", ttl=600)

# Get the current credentials
conn = st.connection("snowflake")
# Connect to github API
gh = GhApi(token=os.environ.get('GH_TOKEN'))

# Load data
df = load_table()

# List the projects targeting GitHub Enterprise
gh_enterprise_repos = df[(df["PROJECT_ORIGIN"] == "github-enterprise")]["PROJECT_TARGET"].drop_duplicates().tolist()
# remove any repos from gh_enterprise_repos that have the target value = None
gh_enterprise_repos = [repo for repo in gh_enterprise_repos if repo is not None]


@st.cache_data
def get_gh_data():
    """
    Retrieves GitHub data for last 20 pull requests on Snyk monitored repos and their corresponding Snyk checks.

    Returns:
        prs_df (pandas.DataFrame): DataFrame containing the following columns:
            - pr_ref: Pull request reference
            - pr_link: Pull request link
            - repo: Repository name
            - snyk_code_pr_checks: Boolean indicating if the repository has code PR checks
            - snyk_sca_pr_checks: Boolean indicating if the repository has SCA PR checks
            - code_pr_check_success: Boolean indicating if the code PR check succeeded or not
            - code_issues_caught: Number of issues caught by the code PR check
            - sca_pr_check_success: Boolean indicating if the SCA PR check succeeded or not
            - sca_issues_caught: Boolean indicating if an SCA issue was caught in the PR
    """
    prs_df = pd.DataFrame({"pr_ref": [], "pr_link": [], "repo": [], "snyk_code_pr_checks": [], "snyk_sca_pr_checks": []})

    # Iterate over the list of GitHub Enterprise repos from Snyk
    # Check if the repo already has a Snyk webhook
    # If it does, set the corresponding row in the DataFrame to True
    for repo in gh_enterprise_repos:
        # Split the repo name into owner and repo
        repo_split = repo.split("/")
        orgOrOwner = repo_split[0]
        repo_name = repo_split[1]

        # get the last 20 pull requests for the repo
        prs = gh.pulls.list(owner=orgOrOwner, repo=repo_name, state="all", sort="updated", direction="desc", per_page=20)

        # Each PR for a repo is converted into a row in new_df which will then be concatenated to prs_df (There's probably a better way to do this)
        new_df = pd.DataFrame({"pr_ref": [pr["head"]["ref"] for pr in prs], "pr_link": [pr["html_url"] for pr in prs], "repo": [repo for _ in prs], "snyk_code_pr_checks": [False] * len(prs), "snyk_sca_pr_checks": [False] * len(prs)})

        # get combined status refs for each sha
        for i, pr in new_df.iterrows():
            try:
                # Get the PR checks of the PR
                combined_status = gh.repos.get_combined_status_for_ref(ref=pr["pr_ref"], owner=orgOrOwner, repo=repo_name)
                
                # NOTE: See ~line 86 for a dummy implementation of the code_issues_caught column.
                # counter = 0

                # Check if the combined status' "statuses[i].context" contains either "code/snyk" or "security/snyk"
                for status in range(len(combined_status["statuses"])):
                    if "code/snyk" in combined_status["statuses"][status]["context"]:
                        # print the repo has code pr checks on
                        print(f"Repo {repo} has code pr checks on")
                        # update the corresponding row in new_df
                        new_df.loc[i, "snyk_code_pr_checks"] = True
                        # add another column to the corresponding row in new_df called "status" with True or False if this status check succeeded or not
                        new_df.loc[i, "code_pr_check_success"] = combined_status["statuses"][status]["state"]

                        # Record issues caught by Code PR Check
                        num_issues_found = re.search('(\d+)\s+new\s+.+\s+issue', combined_status["statuses"][status]["description"])
                        new_df.loc[i, "code_issues_caught"] = int(num_issues_found.group(1)) if num_issues_found else None

                        # NOTE: This basically gives dummy stats since I didn't have enough actual Snyk Code PR Checks at a time :P 
                        # if counter < 20:
                        #     additional = random.randint(0, 5)
                        #     counter = counter + additional
                        #     new_df.loc[i, "code_issues_caught"] = additional
                        #     new_df.loc[i, "code_pr_check_success"] = "failure"


                    elif "security/snyk" in combined_status["statuses"][status]["context"]:
                        print(f"Repo {repo} has sca pr checks on")
                        new_df.loc[i, "snyk_sca_pr_checks"] = True
                        new_df.loc[i, "sca_pr_check_success"] = combined_status["statuses"][status]["state"]
                        
                        # NOTE: We actually can't count the number of issues
                        if combined_status["statuses"][status]["description"] == "1 test has failed":
                            print("Caught an SCA issue in PR")
                            new_df.loc[i, "sca_issues_caught"] = True

        
            except Exception as e:
                print(f"Error getting combined status for repo: {repo_name} with with error: {e}")
                break
        prs_df = pd.concat([prs_df, new_df], ignore_index=True)
    return prs_df

if 'dashboard' not in st.session_state:
    st.session_state.dashboard = None

def show_data(dashboard):
    if dashboard == st.session_state.dashboard:
        st.session_state.dashboard = None
        return
    st.session_state.dashboard = dashboard

prs_df = get_gh_data()

prs_with_sca_checks = prs_df[prs_df["snyk_sca_pr_checks"] == True]
prs_with_code_checks= prs_df[prs_df["snyk_code_pr_checks"] == True]
prs_with_both_checks = prs_df[(prs_df["snyk_sca_pr_checks"] == True) & (prs_df["snyk_code_pr_checks"] == True)]
prs_with_either_check = prs_df[(prs_df["snyk_sca_pr_checks"] == True) | (prs_df["snyk_code_pr_checks"] == True)]

# left merge repos_with_both_checks with repos_with_sca_checks
prs_with_neither_checks = pd.merge(prs_df["repo"].drop_duplicates(), prs_with_either_check["repo"].drop_duplicates(), how="left", indicator=True)
prs_with_neither_checks = prs_with_neither_checks[prs_with_neither_checks["_merge"] == "left_only"]["repo"]
prs_with_neither_checks = prs_df[prs_df["repo"].isin(prs_with_neither_checks)]

with st.sidebar:
    st.write("This is another more realistic example of the type of dashboard you may want to create showing a PR Check Coverage report. Please do note the notes in the textbox in the right")

st.title("Repo PR Check Coverage Report")
st.markdown("""
            ```
**Note:**  This is a POC dashboard and not meant to be production ready
and is not endorsed by Snyk. It is currently set to only work with GHE.
It also only looks at the last 20 PRs for each repo.
Some future improvement recommendations for open source contributors include:  \n
- Supporting all SCM types
- Supporting more than just 20 PRs per repo
- Adding more filtering capabilities
- Proper handling for rate limits
- Including PR Check failures due to Errors as another tracked metric
- Start tracking which PRs were merged anyways vs which PRs had their vulns resolved (showing proper follow through)
- Look at pr check coverage data for just teams with highest number of preventable issues
            """)
repo_count_total = len(prs_df["repo"].drop_duplicates()) # total number of repos with PRs
pr_count_total = len(prs_df) # total number of PRs

st.header("Total No. of PRs:  " + str(pr_count_total))
good_color, medium_color, bad_color = "#55efc4", "#ffeaa7", '#ff7675'
col1, col2, col3 = st.columns(3)
with col1:
    pr_count_both = len(prs_with_both_checks) # number of repos with both sca and code checks
    color_choice = good_color
    if pr_count_both/pr_count_total < 0.5:
        color_choice = medium_color
    if pr_count_both/pr_count_total < 0.2:
        color_choice = bad_color
    st.markdown('<div style="background-color: '+color_choice+'; padding: 10px; border-radius: 10px; text-align: center;"><h2 style="margin: 0; color: black;">' + f'{pr_count_both/pr_count_total:.2%}' +'</h2></div>', unsafe_allow_html=True)
    st.write("of PRs with Both Checks (" + str(pr_count_both) + "). You really should have better coverage")
    sub_col1, sub_col2 = st.columns(2)
    with sub_col1:
        st.button("PRs Missing SCA Coverage", on_click=show_data, args=["missing_sca"])
    with sub_col2:
        st.button("PRs Missing Code Coverage", on_click=show_data, args=["missing_code"])
with col2:
    # Sum of code_issues_caught column in prs_df
    code_issues_caught_sum = prs_df["code_issues_caught"].sum()
    color_choice = good_color
    if code_issues_caught_sum > 10:
        color_choice = medium_color
    if code_issues_caught_sum > 30:
        color_choice = bad_color
    st.markdown('<div style="background-color: '+color_choice+'; padding: 10px; border-radius: 10px; text-align: center;"><h2 style="margin: 0; color: black;">' + str(int(code_issues_caught_sum)) +'</h2></div>', unsafe_allow_html=True)
    st.write("Code Issues Caught out of " + str(len(prs_with_code_checks)) + " PRs with Snyk Code Checks.\n\n")
    st.button("Code Issues Caught", on_click=show_data, args=["code_issues_caught"], use_container_width=True)
with col3: 
    sca_issues_caught_sum = prs_df["sca_issues_caught"].sum()
    color_choice = good_color
    if sca_issues_caught_sum > 10:
        color_choice = medium_color
    if sca_issues_caught_sum > 30:
        color_choice = bad_color
    st.markdown('<div style="background-color: '+color_choice+'; padding: 10px; border-radius: 10px; text-align: center;"><h2 style="margin: 0; color: black;">' + str(sca_issues_caught_sum) +'</h2></div>', unsafe_allow_html=True)
    st.write("PRs with SCA Vulns Caught out of " + str(len(prs_with_sca_checks)) + " PRs w SCA Checks")
    st.write("")
    st.button("SCA Issues Caught", on_click=show_data, args=["sca_issues_caught"], use_container_width=True)



if st.session_state.dashboard == "missing_sca":
    st.header("PRs Missing SCA Checks")
    prs_df[prs_df["snyk_sca_pr_checks"] == False][["pr_ref", "pr_link", "repo"]]
elif st.session_state.dashboard == "missing_code":
    st.header("PRs Missing Code Checks")
    prs_df[prs_df["snyk_code_pr_checks"] == False][["pr_ref", "pr_link", "repo"]]
elif st.session_state.dashboard == "code_issues_caught":
    st.header("Code Issues Caught")
    prs_df[prs_df["code_issues_caught"] > 0][["pr_ref", "pr_link", "repo", "code_issues_caught"]]
elif st.session_state.dashboard == "sca_issues_caught":
    st.header("SCA Issues Caught")
    prs_df[prs_df["sca_issues_caught"] == True][["pr_ref", "pr_link", "repo"]]

