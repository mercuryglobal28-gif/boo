from flask import Flask, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

BASE_URL = "https://flibusta.is"

def get_books(query):
    try:
        # البحث في الموقع
        search_url = f"{BASE_URL}/booksearch?ask={query}"
        response = requests.get(search_url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        books = []
        # استخراج القائمة (تعتمد على هيكل HTML لموقع Flibusta)
        items = soup.find_all('li')
        for item in items:
            link = item.find('a', href=True)
            if link and '/b/' in link['href']:
                book_title = link.text
                book_id = link['href'].split('/')[-1]
                books.append({
                    'title': book_title,
                    'id': book_id,
                    'link': f"{BASE_URL}/b/{book_id}"
                })
        return books
    except Exception as e:
        print(f"Error: {e}")
        return []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/search')
def search_api():
    query = request.args.get('q', '')
    if not query:
        return jsonify([])
    results = get_books(query)
    return jsonify(results)

if __name__ == "__main__":
    app.run(debug=True)
