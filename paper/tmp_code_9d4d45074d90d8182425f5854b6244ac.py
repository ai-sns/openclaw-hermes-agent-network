import requests

def search_github_repositories(query):
    url = f"https://api.github.com/search/repositories?q={query}"
    response = requests.get(url)
    
    if response.status_code == 200:
        repositories = response.json().get('items', [])
        for repo in repositories:
            print(f"Name: {repo['name']}")
            print(f"URL: {repo['html_url']}")
            print(f"Description: {repo.get('description', 'No description available')}")
            print("-" * 40)
    else:
        print("Error fetching data from GitHub API:", response.status_code)

if __name__ == "__main__":
    search_github_repositories("autogen")