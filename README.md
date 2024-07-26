# Getting Started with Snyk, Snowflake, and Streamlit

This is a demo of how to get started with Snyk's Snowflake integration. More info on this integration can be found in our docs [here](https://docs.snyk.io/manage-risk/reporting/reporting-and-bi-integrations-snowflake-data-share).

This repo has four example files with varying levels of complexity.
- get_started: how to retrieve data from snowflake and display it in a bar chart or as a table
- quickstart: a bit more complex, showing various ways to create filters
- sla dashboard: a more realistic example of a type of dashboard a customer may want to work with
- pr-checks: another realistic example of a type of dashboard a customer may want to work with, also leveraging and correlating results with the GitHub API

In any case, this repo is to serve for **demo purposes only**. The SLA dashboard in particular is not endorsed by Snyk and is not necessarily how Snyk's own SLA dashboard calculates SLAs etc. Some of the code likely does have bugs but hopefully it can serve as inspiration for how you may work with Snyk's Snowflake integration if you wish to build on top of Streamlit

For full Streamlit documentation, see [here](https://docs.streamlit.io/)

> **Note:**  Table and fields names for demo purposes only, please refer to documentation and Snowflake for current specifications.

## Getting Started

To get started with this project, you'll need to follow these steps:

1. Create a folder named `.streamlit` with a file `secrets.toml` from the root directory of this project. The full file path from the root should then be `.streamlit/secrets.toml`
2. Define your Snowflake secrets in the `secrets.toml` file. Make sure to include the necessary credentials and connection details.

    It should look like this:
    ```
    [connections.snowflake]
    account = ""
    user = ""
    password = ""
    role = ""
    warehouse = ""
    database = ""
    schema = ""
    client_session_keep_alive = true
    ```

    Also add your GH Secret to a `.env` file in the root directory if you are using the PR Check dashboard. NOTE: You need a token with fine grained access for the PR Check dashboard. See `GH_Permissions.png` for permissions required for the token.

    ```
    GH_TOKEN=
    ```

3. Install `pipenv` if you haven't already. You can install it using the following command:

    ```shell
    pip install pipenv
    ```

4. Once `pipenv` is installed, navigate to the project directory and run the following command to install the project dependencies:

    ```shell
    pipenv shell
    pipenv install
    ```
5. After installing the prereq packages, run the streamlit app locally. Specify the dashboard you want to run. Example below:

    ```shell
    streamlit run 0_get_started.py
    ```
