import requests

# GitHub API URL for searching repositories
search_url = "https://api.github.com/search/repositories"
query = "Autogen"

# Parameters for the search
params = {
    "q": query,
    "sort": "stars",
    "order": "desc"
}

# Perform the search
response = requests.get(search_url, params=params)

# Check if the request was successful
if response.status_code == 200:
    search_results = response.json()
    # Extract the first repository's URL
    if search_results['items']:
        autogen_url = search_results['items'][0]['html_url']
        print(f"Found Autogen repository URL: {autogen_url}")
    else:
        print("No Autogen repositories found.")
else:
    print(f"Error occurred: {response.status_code} - {response.text}")