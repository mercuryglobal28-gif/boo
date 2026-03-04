import os
import urllib.parse
from flask import Flask, render_template, request, Response, stream_with_context
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
TARGET_SITE = "https://flibusta.is"

# الصفحة الرئيسية
@app.route('/')
def index():
    return render_template('index.html')

# البحث
@app.route('/search')
def search():
    query = request.args.get('q', '')
    if not query:
        return render_template('index.html')
    
    # تشفير النص ليتناسب مع الروابط (URL Encoding)
    search_url = f"{TARGET_SITE}/booksearch?ask={urllib.parse.quote(query)}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        resp = requests.get(search_url, headers=headers, timeout=15)
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        books = []
        # جلب روابط الكتب من نتائج البحث
        for link in soup.find_all('a', href=True):
            href = link['href']
            text = link.text.strip()
            # التأكد أن الرابط لكتاب وليس صفحة أخرى
            if href.startswith('/b/') and text and not href.endswith('download'):
                books.append({'title': text, 'link': href})
        
        # إزالة التكرار
        unique_books = {b['link']: b for b in books}.values()
        return render_template('results.html', books=unique_books, query=query)
    except Exception as e:
        return f"<h3 style='color:red; text-align:center;'>Ошибка соединения: {e}</h3>"

# تفاصيل الكتاب وصيغ التحميل
@app.route('/b/<book_id>')
def book_details(book_id):
    book_url = f"{TARGET_SITE}/b/{book_id}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        resp = requests.get(book_url, headers=headers, timeout=15)
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        title_tag = soup.find('h1', class_='title')
        title = title_tag.text if title_tag else "Без названия (بدون عنوان)"
        
        # استخراج صيغ التحميل (epub, mobi, fb2, pdf)
        formats = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            text = link.text.strip().lower()
            if text in ['epub', 'mobi', 'fb2', 'pdf', 'djvu', 'rtf', 'txt']:
                # حفظ المسار الكامل للتحميل
                formats.append({'format': text.upper(), 'download_path': href.lstrip('/')})
                
        return render_template('book.html', title=title, formats=formats)
    except Exception as e:
        return f"<h3 style='color:red; text-align:center;'>Ошибка загрузки книги: {e}</h3>"

# تمرير التحميل (Proxy Download)
@app.route('/download/<path:filepath>')
def download(filepath):
    download_url = f"{TARGET_SITE}/{filepath}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    req = requests.get(download_url, headers=headers, stream=True)
    
    return Response(
        stream_with_context(req.iter_content(chunk_size=1024)),
        content_type=req.headers.get('content-type'),
        headers={'Content-Disposition': req.headers.get('Content-Disposition', 'attachment')}
    )

if __name__ == '__main__':
    # تحديد المنفذ بناءً على متطلبات الخادم (Render)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
