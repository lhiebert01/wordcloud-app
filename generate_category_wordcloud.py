#!/usr/bin/env python3
"""
Script to generate a word cloud from a Wikipedia category.
This script fetches real data from Wikipedia and creates a visualization
with 50-100 of the highest frequency words.
"""

import os
import sys
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import argparse
from collections import Counter
import time

# Import the WikiCategoryAnalyzer class
from wiki_analyzer import WikiCategoryAnalyzer

def create_wordcloud_from_category(category, output_path=None, title=None, max_words=100, force_refresh=True):
    """
    Create a word cloud from a Wikipedia category.
    
    Args:
        category (str): Wikipedia category name
        output_path (str, optional): Path to save the word cloud image
        title (str, optional): Title for the word cloud
        max_words (int, optional): Maximum number of words to include in the word cloud
        force_refresh (bool, optional): Force refresh of cached data
    
    Returns:
        str: Path to the saved word cloud image
    """
    print(f"Analyzing Wikipedia category: {category}")
    
    # Create analyzer instance
    analyzer = WikiCategoryAnalyzer(category, force_refresh=force_refresh)
    
    # Get pages in the category
    pages = analyzer.get_pages_in_category()
    if not pages:
        print(f"No pages found in category: {category}")
        return None
    
    print(f"Found {len(pages)} pages in category: {category}")
    
    # Analyze the category to get word frequencies
    word_frequencies = analyzer.analyze_category()
    
    print(f"Analysis complete. Found {len(word_frequencies)} unique words")
    
    # Get the top words for the word cloud
    top_words = dict(word_frequencies.most_common(max_words))
    
    if not top_words:
        print(f"No words found for category: {category}")
        return None
    
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
    
    if title:
        plt.title(title, fontsize=20)
    else:
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
        for word, count in word_frequencies.most_common(200):
            f.write(f"{word}: {count}\n")
    
    print(f"Word frequencies saved to: {freq_file}")
    
    return output_path

def main():
    parser = argparse.ArgumentParser(description='Generate a word cloud from a Wikipedia category')
    parser.add_argument('--category', '-c', required=True, help='Wikipedia category name')
    parser.add_argument('--output', '-o', help='Output file path for the word cloud image')
    parser.add_argument('--title', '-t', help='Title for the word cloud')
    parser.add_argument('--max-words', '-m', type=int, default=100, help='Maximum number of words in the word cloud')
    parser.add_argument('--force-refresh', '-f', action='store_true', help='Force refresh of cached data')
    args = parser.parse_args()
    
    try:
        # Create word cloud
        output_path = create_wordcloud_from_category(
            args.category,
            output_path=args.output,
            title=args.title,
            max_words=args.max_words,
            force_refresh=args.force_refresh
        )
        
        if output_path:
            print(f"Successfully created word cloud for category: {args.category}")
            print(f"Output saved to: {output_path}")
        else:
            print(f"Failed to create word cloud for category: {args.category}")
            sys.exit(1)
    
    except Exception as e:
        print(f"Error generating word cloud: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
