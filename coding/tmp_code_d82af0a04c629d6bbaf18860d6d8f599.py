import requests

# GitHub API URL for fetching issues in a specific repository
repo_url = "https://api.github.com/repos/microsoft/autogen/issues"

# Perform the request to get the issues
response = requests.get(repo_url)

# Check if the request was successful
if response.status_code == 200:
    issues = response.json()
    # Limit to the first 10 issues
    top_issues = issues[:10]
    
    # Prepare Markdown table
    markdown_table = "| Issue Title | URL |\n|--------------|-----|\n"
    for issue in top_issues:
        markdown_table += f"| {issue['title']} | {issue['html_url']} |\n"
    
    print(markdown_table)
else:
    print(f"Error occurred: {response.status_code} - {response.text}")