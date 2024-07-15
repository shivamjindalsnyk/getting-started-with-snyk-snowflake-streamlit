import streamlit as st
import pandas as pd
import datetime


# Load the table as a dataframe using the Snowpark Session.
# Returns a Pandas DataFrame
@st.cache_data
def load_table():
    return conn.query("SELECT * from ISSUES_V1 WHERE group_public_id!='dd404c7d-4cfd-425a-8128-036e73755b8e';", ttl=600)

# Get the current credentials from secrets.toml
conn = st.connection("snowflake") 

# Load data
df = load_table()

# Sidebar with options to filter data
with st.sidebar:
    st.title("Quick Start Dashboard")
    st.write("This is a bit more complicated than the Getting Started page, but still pretty simple. \n\n You can filter the data by organization, project collection, project tags, and risk score. \n\n The data is then displayed in a table and simple bar chart.")
    
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

    # Filter df with selected collections, tags
    if not selected_collections:
        selected_collections = df["PROJECT_COLLECTION"].unique()
    if not selected_tags:
        selected_tags = df["PROJECT_TAGS"].unique()
    df = df[df["PROJECT_COLLECTION"].isin(selected_collections) & df["PROJECT_TAGS"].isin(selected_tags)]

# Bar Chart of Open and Resolved Issues
# Count and display the number of open and resolved issues
open_issues = df[df["ISSUE_STATUS"] == "Open"].shape[0]
resolved_issues = df[df["ISSUE_STATUS"] == "Resolved"].shape[0]
values = [open_issues, resolved_issues]
labels = ["Open Issues", "Resolved Issues"]
data = {label: value for label, value in zip(labels, values)}
st.title("Open vs Resolved Issues")
st.bar_chart(data)

# Show first 10 (note: this is not top 10) issues
st.write(df.head(10))