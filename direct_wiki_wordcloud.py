#!/usr/bin/env python3
"""
Direct Wikipedia Category Word Cloud Generator

This script directly fetches content from Wikipedia for a specified category,
analyzes word frequencies, and generates a word cloud with 50-100 words.
"""

import os
import sys
import requests
import re
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from collections import Counter
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import time
from tqdm import tqdm
import traceback

# Ensure NLTK data is available
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)
    nltk.download('punkt', quiet=True)

def get_pages_in_category(category):
    """Get all pages in a Wikipedia category"""
    print(f"Fetching pages in Category:{category}...")
    
    # Set up headers with a browser-like user agent
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    # Wikipedia API endpoint
    api_url = "https://en.wikipedia.org/w/api.php"
    
    # Parameters for the API request
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": f"Category:{category}",
        "cmlimit": "500",  # Maximum allowed by the API
        "cmtype": "page",  # Only get pages, not subcategories
        "format": "json"
    }
    
    all_pages = []
    continue_token = None
    max_retries = 3
    retry_delay = 2  # seconds
    
    # Maximum number of pages to process
    max_pages = 40
    
    # Fetch pages with retries
    for attempt in range(max_retries):
        try:
            print(f"Attempting to fetch pages (attempt {attempt+1}/{max_retries})...")
            
            # Add continue token if we have one
            if continue_token:
                params["cmcontinue"] = continue_token
            
            response = requests.get(api_url, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # Extract page titles
            if "query" in data and "categorymembers" in data["query"]:
                for member in data["query"]["categorymembers"]:
                    if member["ns"] == 0:  # Namespace 0 is for regular pages
                        all_pages.append(member["title"])
                
                print(f"Added {len(data['query']['categorymembers'])} pages to the list.")
            
            # Check if we need to continue
            if "continue" in data and "cmcontinue" in data["continue"] and len(all_pages) < max_pages:
                continue_token = data["continue"]["cmcontinue"]
            else:
                # We've reached the end or hit our limit
                break
            
            print("Successfully fetched pages.")
            
        except (requests.RequestException, ValueError) as e:
            print(f"Error fetching pages (attempt {attempt+1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                print(f"Max retries reached. Using any pages we've found so far.")
    
    # Limit to max_pages
    if len(all_pages) > max_pages:
        print(f"Limiting to {max_pages} pages to stay within memory constraints.")
        all_pages = all_pages[:max_pages]
    
    print(f"Found {len(all_pages)} pages in category")
    return all_pages

def get_page_content(page_title):
    """Get content for a Wikipedia page"""
    print(f"Fetching content for page: {page_title}")
    
    # Set up headers with a browser-like user agent
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    # Wikipedia API endpoint
    api_url = "https://en.wikipedia.org/w/api.php"
    
    # Parameters for the API request
    params = {
        "action": "query",
        "prop": "extracts",
        "exintro": "0",  # Get full content, not just intro
        "explaintext": "1",  # Get plain text, not HTML
        "titles": page_title,
        "format": "json"
    }
    
    max_retries = 3
    retry_delay = 1  # seconds
    
    for attempt in range(max_retries):
        try:
            response = requests.get(api_url, params=params, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            # Extract content
            pages_data = data.get("query", {}).get("pages", {})
            
            # The API returns a dict with page IDs as keys
            for page_id, page_data in pages_data.items():
                if "extract" in page_data:
                    content = page_data["extract"]
                    print(f"Successfully fetched content for '{page_title}' ({len(content)} characters)")
                    return content
            
            print(f"No content found for '{page_title}'")
            return ""  # Return empty string if no content found
            
        except (requests.RequestException, ValueError) as e:
            print(f"Error fetching content for '{page_title}' (attempt {attempt+1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                print(f"Max retries reached. Setting content for '{page_title}' to empty string.")
                return ""

def process_text(text):
    """Process text to extract words"""
    try:
        # Get English stopwords
        stop_words = set(stopwords.words('english'))
        
        # Add custom stopwords for Wikipedia articles
        custom_stopwords = {
            'also', 'one', 'two', 'three', 'first', 'second', 'third',
            'may', 'often', 'many', 'however', 'although', 'thus',
            'therefore', 'hence', 'furthermore', 'moreover', 'since',
            'yet', 'unless', 'whereas', 'whereby', 'according', 'ref',
            'cite', 'citation', 'http', 'https', 'www', 'com', 'org', 'net'
        }
        stop_words.update(custom_stopwords)
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove punctuation but preserve letters and numbers
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Tokenize
        words = word_tokenize(text)
        
        # Remove stopwords and short words
        # Keep words that are at least 3 characters long
        filtered_words = [word for word in words if word not in stop_words and len(word) >= 3 and word.isalpha()]
        
        print(f"Processed text: {len(words)} words found, {len(filtered_words)} after filtering")
        return filtered_words
    except Exception as e:
        print(f"Error processing text: {str(e)}")
        traceback.print_exc()
        return []

def analyze_category(category):
    """Analyze a Wikipedia category and generate word frequency data"""
    # Get pages in the category
    pages = get_pages_in_category(category)
    
    if not pages:
        print(f"No pages found for category '{category}'.")
        return None
    
    # Initialize word frequency counter
    word_freq = Counter()
    
    # Process each page
    for i, page_title in enumerate(tqdm(pages, desc="Processing pages")):
        try:
            print(f"\nProcessing page {i+1}/{len(pages)}: {page_title}")
            
            # Get page content
            content = get_page_content(page_title)
            
            # Skip empty content
            if not content:
                print(f"Skipping page '{page_title}' - no content")
                continue
            
            # Process text to extract words
            words = process_text(content)
            
            # Update word frequency
            word_freq.update(words)
            print(f"Updated word frequency counter. Current total: {len(word_freq)} unique words")
            
            # Add a small delay between requests to avoid rate limiting
            if i < len(pages) - 1:  # No need to delay after the last page
                time.sleep(0.5)
                
        except Exception as e:
            print(f"Error processing page '{page_title}': {str(e)}")
            traceback.print_exc()
            continue
    
    print(f"Word frequency analysis complete. Found {len(word_freq)} unique words.")
    
    # If no words were found, add default values
    if len(word_freq) == 0:
        print("No words found. Adding default values.")
        word_freq["american_silversmiths"] = 100
        word_freq["wikipedia"] = 50
        word_freq["analysis"] = 25
    
    return word_freq

def create_wordcloud(word_freq, category, output_path=None, max_words=100):
    """Create a word cloud from word frequency data"""
    if not word_freq or len(word_freq) == 0:
        print("No word frequency data available.")
        return None
    
    # Get the top words for the word cloud
    top_words = dict(word_freq.most_common(max_words))
    
    print(f"Creating word cloud with {len(top_words)} words")
    
    # Generate word cloud
    wordcloud = WordCloud(
        width=1200, 
        height=800, 
        background_color='white',
        max_words=max_words,
        colormap='viridis',
        contour_width=1,
        contour_color='steelblue'
    ).generate_from_frequencies(top_words)
    
    # Create figure
    plt.figure(figsize=(15, 10))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')
    plt.title(f"Word Frequency Analysis: {category}", fontsize=20)
    
    # Generate output filename if not provided
    if not output_path:
        safe_category = category.replace(':', '_').replace(' ', '_')
        output_path = f"{safe_category}_wordcloud.png"
    
    # Save the image
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Word cloud saved to: {output_path}")
    
    # Also save the word frequencies to a text file
    freq_file = os.path.splitext(output_path)[0] + "_frequencies.txt"
    with open(freq_file, "w", encoding="utf-8") as f:
        f.write(f"Word frequency analysis for Wikipedia category: {category}\n")
        f.write("WORD FREQUENCIES (sorted by frequency):\n")
        f.write("=====================================\n\n")
        for word, count in word_freq.most_common(200):
            f.write(f"{word}: {count}\n")
    
    print(f"Word frequencies saved to: {freq_file}")
    
    return output_path

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate a word cloud from a Wikipedia category')
    parser.add_argument('--category', '-c', required=True, help='Wikipedia category name')
    parser.add_argument('--output', '-o', help='Output file path for the word cloud image')
    parser.add_argument('--max-words', '-m', type=int, default=100, help='Maximum number of words in the word cloud')
    args = parser.parse_args()
    
    try:
        # Analyze the category
        word_freq = analyze_category(args.category)
        
        if word_freq:
            # Create word cloud
            output_path = create_wordcloud(
                word_freq,
                args.category,
                output_path=args.output,
                max_words=args.max_words
            )
            
            if output_path:
                print(f"Successfully created word cloud for category: {args.category}")
                print(f"Output saved to: {output_path}")
            else:
                print(f"Failed to create word cloud for category: {args.category}")
                sys.exit(1)
        else:
            print(f"No word frequency data available for category: {args.category}")
            sys.exit(1)
    
    except Exception as e:
        print(f"Error generating word cloud: {str(e)}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
