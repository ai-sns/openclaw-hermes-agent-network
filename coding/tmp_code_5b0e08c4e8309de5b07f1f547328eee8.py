import requests

def get_cache_issues():
    repo_owner = "microsoft"
    repo_name = "autogen"
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues"
    
    response = requests.get(url)
    
    if response.status_code == 200:
        issues = response.json()
        cache_issues = []
        
        for issue in issues:
            if 'cache' in issue['title'].lower() or 'cache' in issue['body'].lower():
                cache_issues.append({
                    'title': issue['title'],
                    'url': issue['html_url']
                })
        
        return cache_issues
    else:
        print("Error:", response.status_code, response.text)
        return []

# 获取并打印包含 "cache" 的 issues
cache_issues = get_cache_issues()
for issue in cache_issues:
    print(f"Title: {issue['title']}, URL: {issue['url']}")