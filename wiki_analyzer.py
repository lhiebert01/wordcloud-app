#!/usr/bin/env python3
"""
Wikipedia Category Word Frequency Analysis with Caching

This script analyzes the frequency of non-common words across all pages in a Wikipedia category,
with a local caching mechanism to avoid redundant API calls and processing.
"""

import sys
import requests
import re
import nltk
from nltk.corpus import stopwords
from collections import Counter
import argparse
import os
import time
import pickle
from datetime import datetime

# Ensure NLTK data is available
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)

# Cache directory setup
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

class WikiCategoryAnalyzer:
    def __init__(self, category, force_refresh=False):
        self.category = category
        self.force_refresh = force_refresh
        self.safe_category = category.replace(':', '_').replace(' ', '_')
        
    def get_cache_path(self, cache_type):
        """Get path to a cache file"""
        return os.path.join(CACHE_DIR, f"{self.safe_category}_{cache_type}.cache")
    
    def load_from_cache(self, cache_type):
        """Load data from cache if it exists"""
        cache_path = self.get_cache_path(cache_type)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'rb') as f:
                    return pickle.load(f), True
            except Exception:
                pass
        return None, False
    
    def save_to_cache(self, cache_type, data):
        """Save data to cache"""
        cache_path = self.get_cache_path(cache_type)
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(data, f)
            return True
        except Exception:
            return False
    
    def get_pages_in_category(self):
        """Get all pages in the category (from cache or API)"""
        # Try to load from cache first
        if not self.force_refresh:
            pages, cache_exists = self.load_from_cache("pages")
            if cache_exists:
                print(f"Using cached page list for '{self.category}' ({len(pages)} pages)")
                return pages
        
        # Format category name for API
        category_name = self.category
        if not category_name.startswith("Category:"):
            category_name = f"Category:{category_name}"
        
        print(f"Fetching pages in {category_name}...")
        
        session = requests.Session()
        url = "https://en.wikipedia.org/w/api.php"
        pages = []
        cmcontinue = None
        
        try:
            while True:
                params = {
                    "action": "query",
                    "format": "json",
                    "list": "categorymembers",
                    "cmtitle": category_name,
                    "cmlimit": 500,
                }
                
                if cmcontinue:
                    params["cmcontinue"] = cmcontinue
                
                response = session.get(url=url, params=params)
                data = response.json()
                
                if "query" in data and "categorymembers" in data["query"]:
                    for member in data["query"]["categorymembers"]:
                        if member["ns"] == 0:  # Namespace 0 is for articles
                            pages.append(member["title"])
                
                if "continue" in data and "cmcontinue" in data["continue"]:
                    cmcontinue = data["continue"]["cmcontinue"]
                else:
                    break
                
                time.sleep(0.5)  # Avoid rate limits
                
        except Exception as e:
            print(f"Error fetching category members: {e}")
        
        # Save to cache if we found pages
        if pages:
            self.save_to_cache("pages", pages)
            print(f"Found {len(pages)} pages in category")
        
        return pages
    
    def get_page_contents(self, pages):
        """Get content for all pages (from cache or API)"""
        # Try to load content cache
        content_cache = {}
        if not self.force_refresh:
            cached_content, cache_exists = self.load_from_cache("content")
            if cache_exists:
                content_cache = cached_content
                print(f"Loaded {len(content_cache)} pages from content cache")
        
        # Fetch any missing pages
        session = requests.Session()
        url = "https://en.wikipedia.org/w/api.php"
        missing_pages = [p for p in pages if p not in content_cache]
        
        if missing_pages:
            print(f"Fetching content for {len(missing_pages)} pages...")
            
            for i, page_title in enumerate(missing_pages):
                params = {
                    "action": "query",
                    "format": "json",
                    "titles": page_title,
                    "prop": "extracts",
                    "explaintext": True,
                }
                
                try:
                    response = session.get(url=url, params=params)
                    data = response.json()
                    
                    # Extract the page content
                    pages_data = data["query"]["pages"]
                    page_id = next(iter(pages_data))
                    
                    if "extract" in pages_data[page_id]:
                        content_cache[page_title] = pages_data[page_id]["extract"]
                    else:
                        content_cache[page_title] = ""
                        
                except Exception as e:
                    print(f"Error fetching content for {page_title}: {e}")
                    content_cache[page_title] = ""
                
                # Save cache periodically
                if (i + 1) % 10 == 0:
                    self.save_to_cache("content", content_cache)
                    print(f"Saved content cache ({i+1}/{len(missing_pages)} pages processed)")
                
                time.sleep(0.5)  # Avoid rate limits
        
        # Save the final content cache
        if missing_pages:
            self.save_to_cache("content", content_cache)
        
        return content_cache
    
    def analyze_word_frequency(self, content_cache):
        """Analyze word frequency across all pages"""
        # Check if we already have frequency results cached
        if not self.force_refresh:
            word_frequencies, cache_exists = self.load_from_cache("frequency")
            if cache_exists:
                print(f"Using cached word frequency results for '{self.category}'")
                return word_frequencies
        
        print("Analyzing word frequencies...")
        total_word_count = Counter()
        
        # Track article statistics
        article_stats = {}
        
        # Get stopwords for filtering
        stop_words = set(stopwords.words('english'))
        # Add common Wikipedia-specific terms to stopwords
        additional_stops = {'edit', 'view', 'history', 'talk', 'read', 'article', 'wikipedia', 'references', 
                           'external', 'links', 'category', 'categories', 'navigation', 'search', 'coordinates',
                           'retrieved', 'accessed', 'ref', 'cite', 'isbn', 'doi', 'page', 'pages', 'http', 'https',
                           'www', 'com', 'org', 'net', 'edu', 'gov', 'jpg', 'png', 'svg', 'html', 'php'}
        stop_words.update(additional_stops)
        
        # Process each page
        for page_title, content in content_cache.items():
            # Convert to lowercase
            text = content.lower()
            
            # Replace common HTML entities
            text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
            
            # Remove URLs
            text = re.sub(r'https?://\S+', '', text)
            
            # Remove wiki markup and references
            text = re.sub(r'\[\d+\]', '', text)  # Remove citation numbers [1], [2], etc.
            text = re.sub(r'\{\{.*?\}\}', '', text)  # Remove content in {{ }}
            text = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]*)\]\]', r'\1', text)  # Convert [[link|text]] to text
            
            # Replace non-alphanumeric with space, but preserve apostrophes in words
            text = re.sub(r'[^a-z0-9\'\s]', ' ', text)
            
            # Replace multiple spaces with a single space
            text = re.sub(r'\s+', ' ', text)
            
            # Split into words and filter
            words = text.split()
            
            # More sophisticated filtering
            filtered_words = []
            for word in words:
                # Remove apostrophes at the beginning/end of words
                word = word.strip("'")
                
                # Skip if it's a stopword, too short, or just a number
                if (word not in stop_words and 
                    len(word) > 2 and 
                    not word.isdigit() and
                    not re.match(r'^[\d\.]+$', word)):  # Skip numbers and decimal values
                    filtered_words.append(word)
            
            # Update word count
            total_word_count.update(filtered_words)
            
            # Store article statistics
            article_stats[page_title] = {
                'total_words': len(words),
                'filtered_words': len(filtered_words)
            }
        
        # Save frequency results to cache
        self.save_to_cache("frequency", total_word_count)
        
        # Save article statistics to cache
        self.save_to_cache("article_stats", article_stats)
        
        return total_word_count
    
    def save_results_to_file(self, word_frequencies, source="analysis"):
        """Save word frequency results to a file"""
        output_file = f"{self.safe_category}_word_frequency.txt"
        
        # Try to load article statistics
        article_stats, stats_exist = self.load_from_cache("article_stats")
        if not stats_exist:
            article_stats = {}
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"Word frequency analysis for Wikipedia category: {self.category}\n")
            f.write(f"Analysis date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Source: {source}\n\n")
            
            # Write word frequencies (top 200)
            f.write("WORD FREQUENCIES (sorted by frequency - top 200):\n")
            f.write("==============================================\n\n")
            for word, count in word_frequencies.most_common(200):
                f.write(f"{word}: {count}\n")
            
            # Write article statistics
            f.write("\n\nARTICLE STATISTICS:\n")
            f.write("===================\n\n")
            f.write(f"Total articles analyzed: {len(article_stats)}\n\n")
            
            # Sort articles by total word count (descending)
            sorted_articles = sorted(article_stats.items(), 
                                    key=lambda x: x[1]['total_words'], 
                                    reverse=True)
            
            # Calculate totals
            total_raw_words = sum(stats['total_words'] for _, stats in sorted_articles)
            total_filtered_words = sum(stats['filtered_words'] for _, stats in sorted_articles)
            
            f.write(f"Total words across all articles: {total_raw_words}\n")
            f.write(f"Total filtered words used for analysis: {total_filtered_words}\n\n")
            
            # Write per-article statistics
            f.write("Per-article word counts:\n")
            f.write("-----------------------\n")
            for article, stats in sorted_articles:
                f.write(f"{article}: {stats['total_words']} words ({stats['filtered_words']} after filtering)\n")
        
        print(f"Results saved to {os.path.abspath(output_file)}")
    
    def display_results(self, word_frequencies):
        """Display the most common words"""
        print("\nMost common words in the category:")
        for word, count in word_frequencies.most_common(20):
            print(f"{word}: {count}")

    def run_analysis(self):
        """Run the complete analysis pipeline"""
        # Check if we already have frequency results cached
        if not self.force_refresh:
            word_frequencies, cache_exists = self.load_from_cache("frequency")
            if cache_exists:
                print(f"Using cached word frequency results for '{self.category}'")
                self.save_results_to_file(word_frequencies, source="cache")
                self.display_results(word_frequencies)
                return word_frequencies
        
        # Get pages in category
        pages = self.get_pages_in_category()
        if not pages:
            print(f"No pages found in category: {self.category}")
            return None
        
        # Get page contents
        content_cache = self.get_page_contents(pages)
        
        # Analyze word frequencies
        word_frequencies = self.analyze_word_frequency(content_cache)
        
        # Save results to file
        self.save_results_to_file(word_frequencies, source="fresh analysis")
        
        # Display results
        self.display_results(word_frequencies)
        
        return word_frequencies

def main():
    parser = argparse.ArgumentParser(description="Analyze word frequency in Wikipedia categories")
    parser.add_argument("category", help="Wikipedia category name")
    parser.add_argument("--force-refresh", action="store_true", help="Force refresh cache")
    args = parser.parse_args()
    
    try:
        analyzer = WikiCategoryAnalyzer(args.category, args.force_refresh)
        analyzer.run_analysis()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
