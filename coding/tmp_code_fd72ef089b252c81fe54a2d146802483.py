import requests
from bs4 import BeautifulSoup

def fetch_latest_trump_news():
    url = "https://news.google.com/search?q=Trump&hl=en-US&gl=US&ceid=US%3Aen"
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad responses
        
        soup = BeautifulSoup(response.text, 'html.parser')
        articles = soup.find_all('article')
        latest_news = []
        
        for article in articles:
            title_tag = article.find('h3')
            link_tag = article.find('a')
            time_tag = article.find('time')
            
            if title_tag and link_tag:
                title = title_tag.text
                link = link_tag['href']
                # Prepend base URL if the link is relative
                if link.startswith('./'):
                    link = 'https://news.google.com' + link[1:]
                published_at = time_tag['datetime'] if time_tag else 'No date'
                latest_news.append({'title': title, 'published_at': published_at, 'link': link})
        
        if not latest_news:
            return "No articles found."
        
        # Format the news in Markdown
        markdown_output = ""
        for news in latest_news:
            markdown_output += f"- **{news['title']}**  \n"
            markdown_output += f"  Published at: {news['published_at']}  \n"
            markdown_output += f"  [Read more]({news['link']})  \n\n"
        
        return markdown_output
    
    except requests.exceptions.RequestException as e:
        return f"An error occurred: {str(e)}"

# Example usage
# print(fetch_latest_trump_news())