import requests

def get_autogen_repositories():
    url = "https://api.github.com/search/repositories"
    params = {
        'q': 'autogen',
        'sort': 'stars',
        'order': 'desc'
    }
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        repositories = response.json().get('items', [])
        for repo in repositories:
            print(repo['html_url'])
    else:
        print("Error:", response.status_code, response.text)

get_autogen_repositories()