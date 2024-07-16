import streamlit as st
import pandas as pd


# Load the table as a dataframe using the Snowpark Session.
# Returns a Pandas DataFrame
@st.cache_data
def load_table():
    return conn.query("SELECT * from ISSUES_V1;", ttl=600)

# Get the current credentials from secrets.toml
conn = st.connection("snowflake") 

# Load data
df = load_table()

with st.sidebar:
    st.title("Getting Started")
    st.write("""
            This is a demo of the Snowflake<>Snyk integration with a few varying levels of complexity.
             Each of the pages above will hopefully show you something new about working with streamlit.
             Feel free to take any of the code snippets and use them in your own projects. \n\n This first page
             is focused just on getting the data from Snowflake and showing a simple representation of the data.
             \n\n With each of these, the code is to serve as starter code. There may be bugs, there may be issues but 
             hopefully it can help you get started with getting value out of Snyk's Snowflake integration quickly :)
            """)

# Bar Chart of Open and Resolved Issues
# Count and display the number of open and resolved issues
open_issues = df[df["ISSUE_STATUS"] == "Open"].shape[0]
resolved_issues = df[df["ISSUE_STATUS"] == "Resolved"].shape[0]
values = [open_issues, resolved_issues]
labels = ["Open Issues", "Resolved Issues"]
data = {label: value for label, value in zip(labels, values)}
st.title("Open vs Resolved Issues")
st.bar_chart(data)

st.write(df.head(10))