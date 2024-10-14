import requests

# GitHub API URL for searching issues in a specific repository
repo_url = "https://api.github.com/repos/microsoft/autogen/issues"
query = "Cache"

# Perform the search for issues containing the keyword "Cache"
response = requests.get(repo_url)

# Check if the request was successful
if response.status_code == 200:
    issues = response.json()
    # Extract relevant issues
    cache_issues = [
        issue for issue in issues 
        if (issue.get('title') and 'Cache' in issue['title']) or 
           (issue.get('body') and 'Cache' in issue['body'])
    ]
    if cache_issues:
        for issue in cache_issues:
            print(f"Issue Title: {issue['title']}, URL: {issue['html_url']}")
    else:
        print("No issues found containing the keyword 'Cache'.")
else:
    print(f"Error occurred: {response.status_code} - {response.text}")