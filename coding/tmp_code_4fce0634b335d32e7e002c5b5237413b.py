import requests

# Define the News API endpoint and parameters
api_key = "YOUR_NEWSAPI_KEY"  # Replace with your actual News API key
url = "https://newsapi.org/v2/everything"
query = "Trump"
from_date = "2023-10-01"  # Adjust the date as needed for the last week
to_date = "2023-10-08"  # Adjust the date as needed for the last week

# Parameters for the API request
params = {
    "q": query,
    "from": from_date,
    "to": to_date,
    "sortBy": "publishedAt",
    "pageSize": 10,
    "apiKey": api_key
}

# Perform the request to get the latest news about Trump
response = requests.get(url, params=params)

# Check if the request was successful
if response.status_code == 200:
    news_articles = response.json().get('articles', [])
    if news_articles:
        for article in news_articles:
            print(f"Title: {article['title']}, URL: {article['url']}")
    else:
        print("No news articles found.")
else:
    print(f"Error occurred: {response.status_code} - {response.text}")