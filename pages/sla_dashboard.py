# Import python packages
import streamlit as st
import pandas as pd
import datetime


# Load the table as a dataframe using the Snowpark Session.
# Returns a Pandas DataFrame
@st.cache_data
def load_table():
    return conn.query("SELECT * from ISSUES_V1 WHERE group_public_id!='dd404c7d-4cfd-425a-8128-036e73755b8e';", ttl=600)

# Get the current credentials
conn = st.connection("snowflake")
# Load data
df = load_table()

# Write directly to the app
with st.sidebar:
    st.title("Shiv Enterprises - SLA Dashboard")
    st.write("This is more complicated but a more realistic example of a possible SLA dashboard a customer may want to build")

    # Create filter by orgs option
    orgs = df["ORG_NAME"].unique().tolist()
    selected_orgs = st.multiselect("Select Organizations out of " + str(len(orgs)) + " options" , orgs)
    if not selected_orgs:
        selected_orgs = df["ORG_NAME"].unique()

    # Filter by orgs selected
    df = df[df["ORG_NAME"].isin(selected_orgs)]

    # Setting more filter options here by Snyk tags and Snyk project collections
    tags = df["PROJECT_TAGS"].unique().tolist()
    collections = df["PROJECT_COLLECTION"].unique().tolist()
    # Create streamlit multi select with options from Project Collections, Tags
    selected_collections = st.multiselect("Select Project Collections out of " + str(len(collections)) + " options" , collections)
    selected_tags = st.multiselect("Select Project Tags out of " + str(len(tags)) + " options" , tags)

    # Can also filter by risk/priority score too
    min_score = 0
    max_score = 1000
    min_col, max_col = st.columns(2)
    with min_col:
        min_score = st.number_input("Minimum Score", 0, max_score, 0)
    with max_col:
        max_score = st.number_input("Maximum Score", min_score, 1000, 1000)
    df = df[(df["SCORE"] >= min_score) & (df["SCORE"] <= max_score)]

    # SLA Targets
    medium_sla = st.number_input("SLA For Medium Vulns", 0, value=90)
    high_sla = st.number_input("SLA for High Vulns", 0, value=60)
    critical_sla = st.number_input("SLA for Critical Vulns", 0, value=30)

    # Filter df with selected collections, tags
    if not selected_collections:
        selected_collections = df["PROJECT_COLLECTION"].unique()
    if not selected_tags:
        selected_tags = df["PROJECT_TAGS"].unique()
    df = df[df["PROJECT_COLLECTION"].isin(selected_collections) & df["PROJECT_TAGS"].isin(selected_tags)]

st.title("SLA Targets")
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown('<div style="background-color: #f9e5dc; padding: 10px; border-radius: 10px;"><h2 style="margin: 0; color: black;">Mediums: ' + str(medium_sla) + '</h2></div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div style="background-color: #ffc382; padding: 10px; border-radius: 10px;"><h2 style="margin: 0; color: black;">Highs: ' + str(high_sla) + '</h2></div>', unsafe_allow_html=True)

with col3:
    st.markdown('<div style="background-color: #ff8282; padding: 10px; border-radius: 10px;"><h2 style="margin: 0; color: black;">Criticals: ' + str(critical_sla) + '</h2></div>', unsafe_allow_html=True)


# Bar Chart of Open and Resolved Issues
# Count and display the number of open and resolved issues
open_issues = df[df["ISSUE_STATUS"] == "Open"].shape[0]
resolved_issues = df[df["ISSUE_STATUS"] == "Resolved"].shape[0]
values = [open_issues, resolved_issues]
labels = ["Open Issues", "Resolved Issues"]
data = {label: value for label, value in zip(labels, values)}
st.title("Open vs Resolved Issues")
st.bar_chart(data)


# Calculate Issue Age. 
# For Open Issues - this code defines it as time between today and last introduced. 
# For Resolved - this code defines it as time between LAST_RESOLVED and last_introduced
# NOTE: This is not Snyk endorsed timing and not necessarily how our own reporting team defines it. 
df["LAST_INTRODUCED"] = pd.to_datetime(df["LAST_INTRODUCED"])
df["ISSUE_AGE"] = 0
resolved_mask = df["ISSUE_STATUS"] == "Resolved"
df.loc[resolved_mask, "ISSUE_AGE"] = (df.loc[resolved_mask, "LAST_RESOLVED"] - df.loc[resolved_mask, "LAST_INTRODUCED"]).dt.days
df.loc[~resolved_mask, "ISSUE_AGE"] = (datetime.datetime.now() - df.loc[~resolved_mask, "LAST_INTRODUCED"]).dt.days

# Allow us to look at data for either open or resolved issues
open_closed_filter = st.radio("Select Issue Status Type ", ("Open", "Resolved"))
df = df[df["ISSUE_STATUS"] == open_closed_filter]
average_age = round(df["ISSUE_AGE"].mean())

# Different ways to compare results by - can compare orgs, tags, or collections. 
# We could theoretically do this with any column
group_options = ["ORG_NAME"]
average_age_filter = group_options[0]
if len(selected_collections) > 1: 
    group_options.append("PROJECT_COLLECTION")
if len(selected_tags) > 1: 
    group_options.append("PROJECT_TAGS")
if len(group_options) > 1:
    average_age_filter = st.radio("GROUP BY: ", group_options)

# This is calculating average issue age per (org, tag, or collection) per severity type
avg_age_df = None
for severity in ['Low', 'Medium', 'High', 'Critical']:
    temp_avg_age_calc = df[df['ISSUE_SEVERITY'] == severity].groupby(average_age_filter)['ISSUE_AGE'].mean()
    temp_avg_age_calc = temp_avg_age_calc.reset_index()
    temp_avg_age_calc['ISSUE_AGE'] = temp_avg_age_calc['ISSUE_AGE'].round()
    temp_avg_age_calc.columns = [average_age_filter, severity]
    if avg_age_df is None:
        avg_age_df = temp_avg_age_calc
    else:
        avg_age_df = pd.merge(avg_age_df, temp_avg_age_calc, on=average_age_filter)

# Calculate Time to Breach
df["TIME_TO_BREACH"] = 0
critical_mask = df["ISSUE_SEVERITY"] == "Critical"
high_mask = df["ISSUE_SEVERITY"] == "High"
medium_mask = df["ISSUE_SEVERITY"] == "Medium"
df.loc[critical_mask, "TIME_TO_BREACH"] = critical_sla - df.loc[critical_mask, "ISSUE_AGE"]
df.loc[high_mask, "TIME_TO_BREACH"] = high_sla - df.loc[high_mask, "ISSUE_AGE"]
df.loc[medium_mask, "TIME_TO_BREACH"] = medium_sla - df.loc[medium_mask, "ISSUE_AGE"]

# Calculate whether an issue breached SLA
df["SLA_BREACHED"] = df["TIME_TO_BREACH"] <= 0

# Show breached vs not breached issue counts per (org, collections, tags)
sla_breached_count = df.groupby(average_age_filter)["SLA_BREACHED"].value_counts().unstack(fill_value=0)
st.title("Count of Breached vs Non-Breached Issues by " + average_age_filter)
st.bar_chart(sla_breached_count, color=["#006400", "#FF0000"])

sla_breached_count["% Breached"] = 100 * (sla_breached_count[True]) / (sla_breached_count[False] +  sla_breached_count[True])
sla_breached_count["% Within SLA"] = 100 * (sla_breached_count[False]) / (sla_breached_count[False] +  sla_breached_count[True])
sla_breached_count = sla_breached_count.sort_values("% Breached", ascending=False)
st.title("Ratio of Issues within and out of SLA")
st.bar_chart(sla_breached_count[["% Breached", "% Within SLA"]],  color=["#FF0000", "#006400"])


# Scatter Chart of Average Issue Age by average_age_filter and Severity
st.title("Average " + open_closed_filter +" Issue Age by "+average_age_filter+" and Severity")
st.scatter_chart(avg_age_df.set_index(average_age_filter))

st.markdown("<h2>Average Age of "+open_closed_filter+" Issues: " + str(average_age) + " days </h2>", unsafe_allow_html=True)

# Prepare data to show
df["TIME_TO_BREACH_TEXT"] = df["TIME_TO_BREACH"].apply(lambda x: f"{abs(x)} days ago" if x < 0 else f"{x} days")
st.title(f"Breached and At Risk Open Issues")
with st.expander("Configure Table Settings"):
    columns = st.multiselect("Columns:", df.columns, ["PROBLEM_TITLE", "ISSUE_SEVERITY", "SCORE", "PROJECT_NAME", "ISSUE_AGE", "SLA_BREACHED", "TIME_TO_BREACH_TEXT", "ISSUE_URL"])
    filter = st.radio("Choose by:", ("inclusion", "exclusion"))

    if filter == "exclusion":
        columns = [col for col in df.columns if col not in columns]

    sort_select = st.selectbox("Sort By: ", df.columns, index=list(df.columns).index("TIME_TO_BREACH"))
    sort_order = st.radio("Sort :", ("Ascending", "Descending"))

    df = df.sort_values(sort_select, ascending=(sort_order == "Ascending"))


def split_frame(df, rows):
    return [df.iloc[i:i+rows] for i in range(0, len(df), rows)]

# Split the dataframe into pages
pages = split_frame(df[columns], 25)  # Change 50 to the desired number of rows per page

# Create a selectbox for the page number
page_number = st.number_input(
    'Page Number',1, 
     len(pages) + 1, 1)

# # Highlight rows light red if SLA_BREACHED is True
def highlight_row(row):
    if row["SLA_BREACHED"]:
        return ["background-color: lightcoral"] * len(row)
    else:
        return [""] * len(row)
    
# Display the selected page
st.write(pages[page_number - 1].style.apply(highlight_row, axis=1))
