import os
import urllib.parse
from flask import Flask, render_template, request, Response, stream_with_context, jsonify
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
TARGET_SITE = "https://flibusta.is"
MOBILE_SITE = "https://m.flibusta.is" # تم إضافة رابط نسخة الهاتف للإحصائيات
HEADERS = {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1'}

# ==========================================
# الواجهة الأساسية (HTML)
# ==========================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search')
def search():
    query = request.args.get('q', '')
    if not query: return render_template('index.html')
    
    search_url = f"{TARGET_SITE}/booksearch?ask={urllib.parse.quote(query)}"
    try:
        resp = requests.get(search_url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.content, 'html.parser')
        books = []
        
        for li in soup.find_all('li'):
            links = li.find_all('a', href=True)
            if links and links[0]['href'].startswith('/b/'):
                book_title = links[0].text.strip()
                book_href = links[0]['href']
                
                authors = [a.text.strip() for a in links[1:] if a['href'].startswith('/a/')]
                author_name = ", ".join(authors) if authors else "Автор не указан"
                
                books.append({
                    'title': book_title,
                    'author': author_name,
                    'link': book_href
                })
        
        return render_template('results.html', books=books, query=query)
    except Exception as e:
        return f"Ошибка: {e}"

@app.route('/b/<book_id>')
def book_details(book_id):
    book_url = f"{TARGET_SITE}/b/{book_id}"
    try:
        resp = requests.get(book_url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        title = soup.find('h1', class_='title').text if soup.find('h1', class_='title') else "Книга"
        
        img_tag = soup.find('img', title="Cover image") or soup.find('img', src=True)
        image_url = None
        if img_tag:
            src = img_tag['src']
            full_img_path = src if src.startswith('http') else f"{TARGET_SITE}{src}"
            image_url = f"/proxy_media?url={urllib.parse.quote(full_img_path)}"

        formats = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            text = a.text.lower()
            valid_formats = ['epub', 'mobi', 'fb2', 'pdf', 'djvu', 'txt']
            for fmt in valid_formats:
                if f"/{fmt}" in href or f"({fmt})" in text or text == fmt:
                    formats.append({'name': fmt.upper(), 'path': href.lstrip('/')})
                    break

        return render_template('book.html', title=title, formats=formats, image_url=image_url)
    except Exception as e:
        return f"Ошибка: {e}"

# ==========================================
# أدوات مساعدة (Proxy & Download)
# ==========================================

@app.route('/proxy_media')
def proxy_media():
    target_url = request.args.get('url')
    if not target_url: return "", 404
    try:
        img_resp = requests.get(target_url, headers=HEADERS, timeout=10)
        return Response(img_resp.content, content_type=img_resp.headers.get('content-type'))
    except:
        return "", 404

@app.route('/download/<path:filepath>')
def download(filepath):
    req = requests.get(f"{TARGET_SITE}/{filepath}", headers=HEADERS, stream=True)
    return Response(
        stream_with_context(req.iter_content(chunk_size=4096)),
        content_type=req.headers.get('content-type'),
        headers={'Content-Disposition': f'attachment; filename="book_{filepath.split("/")[-1]}"'}
    )

# ==========================================
# مسارات API الخاصة بتطبيق الهاتف (تُرجع JSON)
# ==========================================

def fetch_book_stats(url):
    """دالة مساعدة لجلب إحصائيات الكتب وإرجاع أول 30 كتاباً كـ JSON"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.content, 'html.parser')
        items = []
        
        for li in soup.find_all('li'):
            links = li.find_all('a', href=True)
            if links and links[0]['href'].startswith('/b/'):
                title = links[0].text.strip()
                link = links[0]['href']
                
                authors = [a.text.strip() for a in links[1:] if a['href'].startswith('/a/')]
                author_name = ", ".join(authors) if authors else "Неизвестно"
                
                items.append({'title': title, 'author': author_name, 'link': link})
                
                if len(items) >= 30: # التوقف عند 30 عنصر
                    break
        return items
    except Exception as e:
        return {"error": str(e)}

def fetch_author_stats(url):
    """دالة مساعدة لجلب إحصائيات المؤلفين وإرجاع أول 30 مؤلفاً كـ JSON"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.content, 'html.parser')
        items = []
        
        for li in soup.find_all('li'):
            a_tag = li.find('a', href=True)
            if a_tag and a_tag['href'].startswith('/a/'):
                name = a_tag.text.strip()
                link = a_tag['href']
                # النص الكامل قد يحتوي على عدد الكتب مثلاً
                full_text = li.text.strip()
                
                items.append({'name': name, 'link': link, 'details': full_text})
                
                if len(items) >= 30: # التوقف عند 30 عنصر
                    break
        return items
    except Exception as e:
        return {"error": str(e)}


@app.route('/api/stat/day')
def api_stat_day():
    # Топ дня
    data = fetch_book_stats(f"{MOBILE_SITE}/stat/24")
    return jsonify(data)

@app.route('/api/stat/week')
def api_stat_week():
    # Топ недели
    data = fetch_book_stats(f"{MOBILE_SITE}/stat/w")
    return jsonify(data)

@app.route('/api/stat/popular_books')
def api_stat_popular_books():
    # Популярные книги
    data = fetch_book_stats(f"{MOBILE_SITE}/stat/b")
    return jsonify(data)

@app.route('/api/stat/popular_authors')
def api_stat_popular_authors():
    # Популярные авторы
    data = fetch_author_stats(f"{MOBILE_SITE}/stat/a")
    return jsonify(data)

@app.route('/api/stat/prolific_authors')
def api_stat_prolific_authors():
    # Плодовитые авторы
    data = fetch_author_stats(f"{MOBILE_SITE}/stat/plo")
    return jsonify(data)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
