import os
import urllib.parse
from flask import Flask, render_template, request, Response, stream_with_context
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
TARGET_SITE = "https://flibusta.is"
HEADERS = {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1'}

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
            a_tags = li.find_all('a', href=True)
            if len(a_tags) >= 1:
                link = a_tags[0]
                href = link['href']
                if href.startswith('/b/'):
                    books.append({'title': link.text.strip(), 'link': href})
        
        return render_template('results.html', books=books, query=query)
    except Exception as e:
        return f"Ошибка: {e}"

@app.route('/b/<book_id>')
def book_details(book_id):
    book_url = f"{TARGET_SITE}/b/{book_id}"
    try:
        resp = requests.get(book_url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        # جلب العنوان
        title = soup.find('h1', class_='title').text if soup.find('h1', class_='title') else "Книга"
        
        # جلب صورة الغلاف (Proxy)
        img_tag = soup.find('img', src=True)
        image_url = None
        if img_tag and '/i/' in img_tag['src']:
            # نرسل رابط الصورة إلى مسار الـ proxy الخاص بنا
            image_url = f"/proxy_media?url={urllib.parse.quote(img_tag['src'])}"

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

# ممر (Proxy) للصور والملفات لتجاوز الحجب
@app.route('/proxy_media')
def proxy_media():
    media_url = request.args.get('url')
    if not media_url: return "", 404
    
    # تصحيح الرابط إذا كان نسبياً
    full_url = media_url if media_url.startswith('http') else f"{TARGET_SITE}{media_url}"
    
    req = requests.get(full_url, headers=HEADERS, stream=True)
    return Response(req.content, content_type=req.headers.get('content-type'))

@app.route('/download/<path:filepath>')
def download(filepath):
    req = requests.get(f"{TARGET_SITE}/{filepath}", headers=HEADERS, stream=True)
    return Response(
        stream_with_context(req.iter_content(chunk_size=4096)),
        content_type=req.headers.get('content-type'),
        headers={'Content-Disposition': f'attachment; filename="book_{filepath.split("/")[-1]}"'}
    )

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
