#!/usr/bin/env python3
"""
Visualize word frequency results from Wikipedia category analysis.
"""

import os
import pickle
import sys
import argparse
import matplotlib.pyplot as plt
from collections import Counter

def main():
    parser = argparse.ArgumentParser(description="Visualize word frequency results")
    parser.add_argument("category", help="Wikipedia category name")
    parser.add_argument("--top", type=int, default=20, help="Number of top words to display")
    args = parser.parse_args()
    
    # Format category name for cache lookup
    category = args.category
    safe_category = category.replace(':', '_').replace(' ', '_')
    
    # Cache directory
    cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
    cache_path = os.path.join(cache_dir, f"{safe_category}_frequency.cache")
    
    if not os.path.exists(cache_path):
        print(f"No cached results found for category: {category}")
        print(f"Please run wiki_analyzer.py first to generate results.")
        return
    
    try:
        # Load the cached frequency data
        with open(cache_path, 'rb') as f:
            word_frequencies = pickle.load(f)
        
        # Get top words
        top_words = word_frequencies.most_common(args.top)
        
        # Create visualization
        words, counts = zip(*top_words)
        
        plt.figure(figsize=(12, 8))
        plt.bar(words, counts, color='skyblue')
        plt.xlabel('Words')
        plt.ylabel('Frequency')
        plt.title(f'Top {args.top} Words in Wikipedia Category: {category}')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        # Save the visualization
        output_file = f"{safe_category}_visualization.png"
        plt.savefig(output_file)
        print(f"Visualization saved to {os.path.abspath(output_file)}")
        
        # Display statistics
        print(f"\nTop {args.top} words in Wikipedia category '{category}':")
        print("-" * 40)
        for i, (word, count) in enumerate(top_words):
            print(f"{i+1:3d}. {word:20s}: {count}")
        
        # Show total unique words
        print("-" * 40)
        print(f"Total unique words: {len(word_frequencies)}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
