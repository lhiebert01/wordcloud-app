#!/usr/bin/env python3
"""
Flask web application for Wikipedia word frequency analysis and word cloud visualization.
"""

import os
import pickle
import re
import hashlib
from collections import Counter
from datetime import datetime
import json
import base64
from io import BytesIO

from flask import Flask, render_template, request, jsonify, send_file, Response
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import nltk
from nltk.corpus import stopwords
import requests
import PyPDF2
import docx

# Import the WikiCategoryAnalyzer class
from wiki_analyzer import WikiCategoryAnalyzer

# Ensure NLTK data is available
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)

app = Flask(__name__)

# Cache directory setup
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

# Maximum file size (5MB)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    """Analyze a Wikipedia category and generate word cloud data."""
    category = request.form.get('category', '').strip()
    
    if not category:
        return jsonify({'error': 'Please enter a valid category name'})
    
    try:
        # Create analyzer instance
        analyzer = WikiCategoryAnalyzer(category, force_refresh=True)  # Force refresh to use the improved algorithm
        
        # Check if we already have frequency results cached
        word_frequencies, cache_exists = analyzer.load_from_cache("frequency")
        
        if not cache_exists:
            # Get pages in the category
            pages = analyzer.get_pages_in_category()
            if not pages:
                return jsonify({'error': f'No pages found in category: {category}'})
            
            # Get content for all pages
            content_cache = analyzer.get_page_contents(pages)
            
            # Analyze word frequency
            word_frequencies = analyzer.analyze_word_frequency(content_cache)
            
            if not word_frequencies:
                return jsonify({'error': 'Failed to analyze word frequencies'})
        
        # Get top 200 words for the word cloud
        top_words = dict(word_frequencies.most_common(200))
        
        # Create timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Generate word cloud
        wordcloud = WordCloud(
            width=800, 
            height=400, 
            background_color='white',
            max_words=200,
            colormap='viridis',
            contour_width=1,
            contour_color='steelblue'
        ).generate_from_frequencies(top_words)
        
        # Convert word cloud to base64 image
        img = BytesIO()
        wordcloud.to_image().save(img, format='PNG')
        img.seek(0)
        img_b64 = base64.b64encode(img.getvalue()).decode('utf-8')
        
        # Get article statistics if available
        article_stats = {}
        article_stats_data, stats_exist = analyzer.load_from_cache("article_stats")
        if stats_exist:
            article_stats = article_stats_data
            
            # Calculate totals
            total_raw_words = sum(stats['total_words'] for _, stats in article_stats.items())
            total_filtered_words = sum(stats['filtered_words'] for _, stats in article_stats.items())
            
            # Sort articles by word count (descending)
            sorted_articles = sorted(article_stats.items(), 
                                    key=lambda x: x[1]['total_words'], 
                                    reverse=True)
            
            # Format for JSON response
            article_stats = {
                'total_articles': len(article_stats),
                'total_raw_words': total_raw_words,
                'total_filtered_words': total_filtered_words,
                'articles': [
                    {
                        'title': article,
                        'total_words': stats['total_words'],
                        'filtered_words': stats['filtered_words']
                    } for article, stats in sorted_articles
                ]
            }
        
        # Prepare data for response
        result = {
            'category': category,
            'timestamp': timestamp,
            'wordcloud': img_b64,
            'word_data': [{'word': word, 'count': count} for word, count in top_words.items()],
            'from_cache': cache_exists,
            'article_stats': article_stats
        }
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': f'Error analyzing category: {str(e)}'})

@app.route('/download_wordcloud', methods=['POST'])
def download_wordcloud():
    """Generate and download a word cloud image."""
    try:
        data = request.json
        word_data = {item['word']: item['count'] for item in data.get('word_data', [])}
        category = data.get('category', 'Wikipedia_Category')
        
        if not word_data:
            return jsonify({'error': 'No word data provided'})
        
        # Generate word cloud
        wordcloud = WordCloud(
            width=1200, 
            height=800, 
            background_color='white',
            max_words=100,
            colormap='viridis',
            contour_width=1,
            contour_color='steelblue'
        ).generate_from_frequencies(word_data)
        
        # Save to BytesIO
        img = BytesIO()
        wordcloud.to_image().save(img, format='PNG')
        img.seek(0)
        
        # Create safe filename
        safe_category = category.replace(':', '_').replace(' ', '_')
        filename = f"{safe_category}_wordcloud.png"
        
        return send_file(
            img,
            mimetype='image/png',
            as_attachment=True,
            download_name=filename
        )
    
    except Exception as e:
        return jsonify({'error': f'Error generating word cloud: {str(e)}'})

@app.route('/download_frequencies', methods=['POST'])
def download_frequencies():
    """Download word frequencies as a text file."""
    try:
        data = request.json
        word_data = data.get('word_data', [])
        category = data.get('category', 'Wikipedia_Category')
        
        if not word_data:
            return jsonify({'error': 'No word data provided'})
        
        # Create text content
        content = f"Word frequency analysis for: {category}\n"
        content += f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        content += "WORD FREQUENCIES (sorted by frequency):\n"
        content += "=====================================\n\n"
        
        for item in word_data:
            content += f"{item['word']}: {item['count']}\n"
        
        # Create BytesIO object
        text_file = BytesIO()
        text_file.write(content.encode('utf-8'))
        text_file.seek(0)
        
        # Create safe filename
        filename = "WordCloud-Word-Frequencies.txt"
        
        return send_file(
            text_file,
            mimetype='text/plain',
            as_attachment=True,
            download_name=filename
        )
    
    except Exception as e:
        return jsonify({'error': f'Error generating frequency file: {str(e)}'})

@app.route('/analyze_file', methods=['POST'])
def analyze_file():
    """Analyze an uploaded file for word frequencies."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'})
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'})
    
    try:
        # Get file content based on file type
        text_content = ""
        file_extension = os.path.splitext(file.filename)[1].lower()
        
        if file_extension == '.pdf':
            # Process PDF file
            pdf_file = BytesIO(file.read())
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            for page_num in range(len(pdf_reader.pages)):
                text_content += pdf_reader.pages[page_num].extract_text() + "\n"
        
        elif file_extension == '.docx':
            # Process Word document
            doc_file = BytesIO(file.read())
            doc = docx.Document(doc_file)
            for para in doc.paragraphs:
                text_content += para.text + "\n"
        
        elif file_extension == '.txt' or file.content_type == 'text/plain':
            # Process text file
            text_content = file.read().decode('utf-8', errors='ignore')
        
        else:
            return jsonify({'error': 'Unsupported file type. Please upload a PDF, DOCX, or TXT file.'})
        
        # Analyze the text
        word_frequencies = analyze_text_content(text_content)
        
        # Get top 100 words for the word cloud
        top_words = dict(word_frequencies.most_common(100))
        
        # Create timestamp and source name
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        source_name = file.filename
        
        # Generate word cloud
        wordcloud = WordCloud(
            width=800, 
            height=400, 
            background_color='white',
            max_words=100,
            colormap='viridis',
            contour_width=1,
            contour_color='steelblue'
        ).generate_from_frequencies(top_words)
        
        # Convert word cloud to base64 image
        img = BytesIO()
        wordcloud.to_image().save(img, format='PNG')
        img.seek(0)
        img_b64 = base64.b64encode(img.getvalue()).decode('utf-8')
        
        # Prepare data for response
        result = {
            'source_type': 'file',
            'source_name': source_name,
            'timestamp': timestamp,
            'wordcloud': img_b64,
            'word_data': [{'word': word, 'count': count} for word, count in top_words.items()]
        }
        
        # Cache the result
        cache_file_results(result)
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': f'Error analyzing file: {str(e)}'})

@app.route('/analyze_url', methods=['POST'])
def analyze_url():
    """Analyze content from a URL."""
    url = request.form.get('url', '').strip()
    
    if not url:
        return jsonify({'error': 'Please enter a valid URL'})
    
    try:
        # Generate a cache key based on the URL
        url_hash = hashlib.md5(url.encode()).hexdigest()
        cache_path = os.path.join(CACHE_DIR, f"page_{url_hash}.txt")
        
        # Check if we have this URL cached
        if os.path.exists(cache_path):
            with open(cache_path, 'r', encoding='utf-8', errors='ignore') as f:
                text_content = f.read()
        else:
            # Fetch the URL content
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Extract text from HTML using a simple regex approach
            html_content = response.text
            text_content = re.sub(r'<[^>]+>', ' ', html_content)
            text_content = re.sub(r'\s+', ' ', text_content).strip()
            
            # Save to cache
            with open(cache_path, 'w', encoding='utf-8', errors='ignore') as f:
                f.write(text_content)
        
        # Analyze the text
        word_frequencies = analyze_text_content(text_content)
        
        # Get top 100 words for the word cloud
        top_words = dict(word_frequencies.most_common(100))
        
        # Create timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Generate word cloud
        wordcloud = WordCloud(
            width=800, 
            height=400, 
            background_color='white',
            max_words=100,
            colormap='viridis',
            contour_width=1,
            contour_color='steelblue'
        ).generate_from_frequencies(top_words)
        
        # Convert word cloud to base64 image
        img = BytesIO()
        wordcloud.to_image().save(img, format='PNG')
        img.seek(0)
        img_b64 = base64.b64encode(img.getvalue()).decode('utf-8')
        
        # Prepare data for response
        result = {
            'source_type': 'url',
            'source_name': url,
            'timestamp': timestamp,
            'wordcloud': img_b64,
            'word_data': [{'word': word, 'count': count} for word, count in top_words.items()]
        }
        
        # Cache the result
        cache_file_results(result)
        
        return jsonify(result)
    
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Error fetching URL: {str(e)}'})
    except Exception as e:
        return jsonify({'error': f'Error analyzing URL content: {str(e)}'})

def analyze_text_content(text):
    """Analyze word frequency in text content."""
    # Get stopwords for filtering
    stop_words = set(stopwords.words('english'))
    
    # Convert to lowercase and remove non-alphanumeric characters
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', '', text)
    
    # Split into words and filter
    words = text.split()
    words = [word for word in words if word not in stop_words and len(word) > 1]
    
    # Count word frequencies
    word_frequencies = Counter(words)
    
    return word_frequencies

def cache_file_results(result):
    """Cache analysis results."""
    try:
        # Create a unique identifier for the result
        if result['source_type'] == 'url':
            identifier = hashlib.md5(result['source_name'].encode()).hexdigest()
        else:
            identifier = hashlib.md5((result['source_name'] + result['timestamp']).encode()).hexdigest()
        
        # Save to cache
        cache_path = os.path.join(CACHE_DIR, f"result_{identifier}.cache")
        with open(cache_path, 'wb') as f:
            pickle.dump(result, f)
    except Exception:
        # Silently fail if caching doesn't work
        pass

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
