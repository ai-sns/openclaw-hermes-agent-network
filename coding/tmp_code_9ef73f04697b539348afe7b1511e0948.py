import requests

def get_issues_with_keyword(repo, keyword):
    url = f"https://api.github.com/repos/{repo}/issues"
    headers = {'User-Agent': 'YourAppName'}
    issues_with_keyword = []

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an error for bad responses

        issues = response.json()
        for issue in issues:
            if 'pull_request' not in issue:  # Exclude pull requests
                if keyword.lower() in issue['title'].lower() or keyword.lower() in issue['body'].lower():
                    issues_with_keyword.append({
                        'title': issue['title'],
                        'url': issue['html_url'],
                        'created_at': issue['created_at'],
                        'state': issue['state']
                    })
        return issues_with_keyword
    except requests.exceptions.HTTPError as http_err:
        return f"HTTP error occurred: {http_err}"
    except requests.exceptions.RequestException as err:
        return f"Error fetching data from GitHub: {err}"

# Example usage
repo = "microsoft/autogen"
keyword = "cache"
issues = get_issues_with_keyword(repo, keyword)

# Format the output as a Markdown table
markdown_table = "| Title | URL | Created At | State |\n|-------|-----|------------|-------|\n"
for issue in issues:
    markdown_table += f"| {issue['title']} | [Link]({issue['url']}) | {issue['created_at']} | {issue['state']} |\n"

print(markdown_table)