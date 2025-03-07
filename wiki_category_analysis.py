#!/usr/bin/env python3
"""
Wikipedia Category Word Frequency Analysis

This script takes a Wikipedia category name as input and analyzes the frequency
of non-common words across all pages in that category.
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
import json
import pickle
from datetime import datetime

# Download required NLTK data
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    print("Downloading NLTK stopwords...")
    nltk.download('stopwords', quiet=True)
    print("Download complete.")

# Cache directory
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def get_cache_path(category, cache_type):
    """
    Get the path to a cache file for a specific category and cache type.
    
    Args:
        category (str): The Wikipedia category name
        cache_type (str): Type of cache ('pages', 'content', or 'frequency')
        
    Returns:
        str: Path to the cache file
    """
    safe_category = category.replace(':', '_').replace(' ', '_')
    return os.path.join(CACHE_DIR, f"{safe_category}_{cache_type}.cache")

def load_from_cache(category, cache_type):
    """
    Load data from cache if it exists.
    
    Args:
        category (str): The Wikipedia category name
        cache_type (str): Type of cache ('pages', 'content', or 'frequency')
        
    Returns:
        tuple: (data, exists) where data is the cached data and exists is a boolean
               indicating whether the cache exists
    """
    cache_path = get_cache_path(category, cache_type)
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'rb') as f:
                cache_data = pickle.load(f)
            print(f"Loaded {cache_type} from cache: {cache_path}")
            return cache_data, True
        except Exception as e:
            print(f"Error loading cache: {e}")
    return None, False

def save_to_cache(category, cache_type, data):
    """
    Save data to cache.
    
    Args:
        category (str): The Wikipedia category name
        cache_type (str): Type of cache ('pages', 'content', or 'frequency')
        data: The data to cache
    """
    cache_path = get_cache_path(category, cache_type)
    try:
        with open(cache_path, 'wb') as f:
            pickle.dump(data, f)
        print(f"Saved {cache_type} to cache: {cache_path}")
    except Exception as e:
        print(f"Error saving cache: {e}")

def get_pages_in_category(category):
    """
    Get all pages that belong to a specific Wikipedia category.
    Uses cache if available.
    """
    # Try to load from cache first
    pages, cache_exists = load_from_cache(category, "pages")
    if cache_exists:
        return pages
    
    session = requests.Session()
    url = "https://en.wikipedia.org/w/api.php"
    
    # Format the category name correctly
    if not category.startswith("Category:"):
        category = f"Category:{category}"
    
    pages = []
    cmcontinue = None
    
    print(f"Fetching pages in {category}...")
    
    try:
        while True:
            params = {
                "action": "query",
                "format": "json",
                "list": "categorymembers",
                "cmtitle": category,
                "cmlimit": 500,  # Maximum allowed by the API
            }
            
            if cmcontinue:
                params["cmcontinue"] = cmcontinue
            
            response = session.get(url=url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if "query" in data and "categorymembers" in data["query"]:
                for member in data["query"]["categorymembers"]:
                    # Only include actual pages, not subcategories
                    if member["ns"] == 0:  # Namespace 0 is for articles
                        pages.append(member["title"])
                print(f"Found {len(pages)} pages so far...")
            
            if "continue" in data and "cmcontinue" in data["continue"]:
                cmcontinue = data["continue"]["cmcontinue"]
            else:
                break
                
            # Add a small delay to avoid hitting rate limits
            time.sleep(0.5)
            
    except Exception as e:
        print(f"Error fetching category members: {e}")
    
    # Save to cache
    if pages:
        save_to_cache(category, "pages", pages)
    
    return pages

def get_page_content(page_title, content_cache=None):
    """
    Get the text content of a Wikipedia page.
    Uses cache if available.
    
    Args:
        page_title (str): The title of the Wikipedia page
        content_cache (dict, optional): Cache of page contents
        
    Returns:
        str: The text content of the page
    """
    # Check if content is in the provided cache
    if content_cache is not None and page_title in content_cache:
        return content_cache[page_title]
    
    session = requests.Session()
    url = "https://en.wikipedia.org/w/api.php"
    
    params = {
        "action": "query",
        "format": "json",
        "titles": page_title,
        "prop": "extracts",
        "explaintext": True,  # Get plain text content
    }
    
    try:
        response = session.get(url=url, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Extract the page content
        pages = data["query"]["pages"]
        page_id = next(iter(pages))
        
        if "extract" in pages[page_id]:
            return pages[page_id]["extract"]
        else:
            print(f"No content found for page: {page_title}")
            return ""
            
    except Exception as e:
        print(f"Error fetching page content for {page_title}: {e}")
        return ""

def analyze_word_frequency(text):
    """
    Analyze the frequency of non-common words in a text.
    """
    # Convert to lowercase and remove non-alphanumeric characters
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', '', text)
    
    # Split into words
    words = text.split()
    
    # Remove common words (stopwords)
    stop_words = set(stopwords.words('english'))
    words = [word for word in words if word not in stop_words and len(word) > 1]
    
    # Count word frequencies
    return Counter(words)

def main():
    parser = argparse.ArgumentParser(description="Analyze word frequency in Wikipedia categories")
    parser.add_argument("category", help="Wikipedia category name")
    parser.add_argument("--force-refresh", action="store_true", help="Force refresh cache")
    args = parser.parse_args()
    
    try:
        category = args.category
        print(f"Starting analysis of category: {category}")
        
        # Check if we already have the frequency results cached
        word_frequencies, cache_exists = load_from_cache(category, "frequency")
        
        if cache_exists and not args.force_refresh:
            print(f"Using cached word frequency results for '{category}'")
            
            # Display the most common words
            print("\nMost common words in the category:")
            for word, count in word_frequencies.most_common(20):
                print(f"{word}: {count}")
                
            # Save results to a file (even if from cache, to ensure we have the latest format)
            safe_category = category.replace(':', '_').replace(' ', '_')
            output_file = f"{safe_category}_word_frequency.txt"
            
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(f"Word frequency analysis for Wikipedia category: {category}\n")
                f.write(f"Analysis date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Source: Cache\n\n")
                f.write("Word frequencies:\n")
                for word, count in word_frequencies.most_common():
                    f.write(f"{word}: {count}\n")
            
            print(f"\nComplete word frequency analysis saved to {os.path.abspath(output_file)}")
            return
        
        # Get all pages in the category
        pages = get_pages_in_category(category)
        
        if not pages:
            print(f"No pages found in category: {category}")
            return
        
        print(f"Found {len(pages)} pages in category: {category}")
        if len(pages) > 0:
            print("First few pages:", ", ".join(pages[:3]))
        
        # Try to load content cache
        content_cache, cache_exists = load_from_cache(category, "content")
        if not cache_exists or args.force_refresh:
            content_cache = {}
        
        # Analyze word frequency across all pages
        total_word_count = Counter()
        
        print("Starting content analysis...")
        for i, page_title in enumerate(pages):
            print(f"Processing page {i+1}/{len(pages)}: {page_title}")
            
            # Get page content (from cache or API)
            if page_title in content_cache:
                print(f"Using cached content for {page_title}")
                content = content_cache[page_title]
            else:
                content = get_page_content(page_title)
                content_cache[page_title] = content
                
                # Save content cache periodically (every 10 pages)
                if (i + 1) % 10 == 0:
                    save_to_cache(category, "content", content_cache)
            
            # Analyze word frequency
            word_count = analyze_word_frequency(content)
            total_word_count.update(word_count)
            
            print(f"Processed {page_title} - found {len(word_count)} unique words")
            
            # Add a small delay to avoid hitting rate limits (only if fetching from API)
            if page_title not in content_cache:
                time.sleep(0.5)
        
        # Save the final content cache
        save_to_cache(category, "content", content_cache)
        
        # Save the word frequency results to cache
        save_to_cache(category, "frequency", total_word_count)
        
        # Save results to a file
        safe_category = category.replace(':', '_').replace(' ', '_')
        output_file = f"{safe_category}_word_frequency.txt"
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"Word frequency analysis for Wikipedia category: {category}\n")
            f.write(f"Analysis date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Source: Fresh analysis\n\n")
            f.write("Word frequencies:\n")
            for word, count in total_word_count.most_common():
                f.write(f"{word}: {count}\n")
        
        # Display the most common words
        print("\nMost common words in the category:")
        for word, count in total_word_count.most_common(20):
            print(f"{word}: {count}")
            
        print(f"\nComplete word frequency analysis saved to {os.path.abspath(output_file)}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
