#!/usr/bin/env python3
"""
Display cached word frequency results for a Wikipedia category.
"""

import os
import pickle
import sys
import argparse
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from io import BytesIO

def main():
    parser = argparse.ArgumentParser(description="Display cached word frequency results")
    parser.add_argument("category", help="Wikipedia category name")
    parser.add_argument("--top", type=int, default=100, help="Number of top words to display (default: 100, max: 200)")
    parser.add_argument("--generate-wordcloud", action="store_true", help="Generate a word cloud image")
    parser.add_argument("--output", help="Output file for word cloud (default: category_wordcloud.png)")
    args = parser.parse_args()
    
    # Ensure top is within reasonable limits
    args.top = min(max(args.top, 10), 200)
    
    # Format category name for cache lookup
    category = args.category
    safe_category = category.replace(':', '_').replace(' ', '_')
    
    # Cache directory
    cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
    cache_path = os.path.join(cache_dir, f"{safe_category}_frequency.cache")
    stats_path = os.path.join(cache_dir, f"{safe_category}_article_stats.cache")
    
    if not os.path.exists(cache_path):
        print(f"No cached results found for category: {category}")
        print(f"Please run wiki_analyzer.py first to generate results.")
        return
    
    try:
        # Load the cached frequency data
        with open(cache_path, 'rb') as f:
            word_frequencies = pickle.load(f)
        
        # Try to load article statistics if available
        article_stats = {}
        if os.path.exists(stats_path):
            try:
                with open(stats_path, 'rb') as f:
                    article_stats = pickle.load(f)
            except Exception as e:
                print(f"Warning: Could not load article statistics: {e}")
        
        # Display the top words
        print(f"\nTop {args.top} words in Wikipedia category '{category}':")
        print("-" * 60)
        print(f"{'Rank':<6}{'Word':<25}{'Count':<10}{'Percentage':<10}")
        print("-" * 60)
        
        # Calculate total word count for percentage
        total_count = sum(count for _, count in word_frequencies.most_common())
        
        for i, (word, count) in enumerate(word_frequencies.most_common(args.top)):
            percentage = (count / total_count) * 100
            print(f"{i+1:<6}{word:<25}{count:<10}{percentage:.2f}%")
        
        # Show total unique words
        print("-" * 60)
        print(f"Total unique words: {len(word_frequencies)}")
        print(f"Total word occurrences: {total_count}")
        
        # Display article statistics if available
        if article_stats:
            print("\n\nARTICLE STATISTICS:")
            print("=" * 60)
            print(f"Total articles analyzed: {len(article_stats)}")
            
            # Calculate totals
            total_raw_words = sum(stats['total_words'] for _, stats in article_stats.items())
            total_filtered_words = sum(stats['filtered_words'] for _, stats in article_stats.items())
            
            print(f"Total words across all articles: {total_raw_words}")
            print(f"Total filtered words used for analysis: {total_filtered_words}")
            
            # Sort articles by word count (descending)
            sorted_articles = sorted(article_stats.items(), 
                                    key=lambda x: x[1]['total_words'], 
                                    reverse=True)
            
            print("\nPer-article word counts (top 20 articles by size):")
            print("-" * 60)
            print(f"{'Article':<50}{'Total Words':<15}{'Filtered Words':<15}")
            print("-" * 60)
            
            for article, stats in sorted_articles[:20]:  # Show top 20 articles by default
                print(f"{article[:48]:<50}{stats['total_words']:<15}{stats['filtered_words']:<15}")
            
            if len(sorted_articles) > 20:
                print(f"... and {len(sorted_articles) - 20} more articles")
        
        # Generate word cloud if requested
        if args.generate_wordcloud:
            try:
                # Get top 100 words for the word cloud
                top_words = dict(word_frequencies.most_common(200))
                
                # Generate word cloud
                wordcloud = WordCloud(
                    width=1200, 
                    height=800, 
                    background_color='white',
                    max_words=200,
                    colormap='viridis',
                    contour_width=1,
                    contour_color='steelblue'
                ).generate_from_frequencies(top_words)
                
                # Save the word cloud
                output_file = args.output if args.output else f"{safe_category}_wordcloud.png"
                wordcloud.to_file(output_file)
                print(f"\nWord cloud saved to: {os.path.abspath(output_file)}")
                
                # Display the word cloud
                plt.figure(figsize=(12, 8))
                plt.imshow(wordcloud, interpolation='bilinear')
                plt.axis("off")
                plt.title(f"Word Cloud for '{category}'")
                plt.tight_layout()
                plt.show()
                
            except Exception as e:
                print(f"Error generating word cloud: {e}")
        
        # Check if results file exists
        results_file = f"{safe_category}_word_frequency.txt"
        if os.path.exists(results_file):
            print(f"\nFull results available in: {os.path.abspath(results_file)}")
    
    except Exception as e:
        print(f"Error reading cache: {e}")

if __name__ == "__main__":
    main()
