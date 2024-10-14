import requests

def get_autogen_repo_url():
    # GitHub API endpoint for searching repositories
    url = "https://api.github.com/search/repositories"
    params = {
        'q': 'autogen',
        'sort': 'stars',
        'order': 'desc'
    }
    headers = {'User-Agent': 'YourAppName'}

    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()  # Raise an error for bad responses

        data = response.json()
        if data['total_count'] > 0:
            # Assuming the first result is the most relevant
            repo_url = data['items'][0]['html_url']
            return repo_url
        else:
            return "No repositories found."
    except requests.exceptions.HTTPError as http_err:
        return f"HTTP error occurred: {http_err}"
    except requests.exceptions.RequestException as err:
        return f"Error fetching data from GitHub: {err}"

# Example usage
print(get_autogen_repo_url())