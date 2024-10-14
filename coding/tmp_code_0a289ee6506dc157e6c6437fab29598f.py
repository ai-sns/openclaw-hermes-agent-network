import requests

def get_latest_trump_news(api_key):
    # Construct the API request URL
    url = f"https://newsapi.org/v2/everything?q=Trump&sortBy=publishedAt&apiKey={api_key}"
    
    # Make the API request
    response = requests.get(url)
    
    # Check if the request was successful
    if response.status_code == 200:
        news_data = response.json()
        articles = news_data.get('articles', [])
        # Return a list of tuples with article details
        return [(article['title'], article['publishedAt'], article['url']) for article in articles]
    else:
        # Return an error message with the status code
        return f"Error: {response.status_code} - {response.text}"

# Example usage (replace 'your_api_key' with a valid API key)
# print(get_latest_trump_news('your_api_key'))