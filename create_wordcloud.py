#!/usr/bin/env python3
"""
Script to generate a word cloud from word frequency data.
"""

import os
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import argparse
from collections import Counter

def create_wordcloud_from_dict(word_frequencies, output_path=None, title=None):
    """
    Create a word cloud from a dictionary of word frequencies.
    
    Args:
        word_frequencies (dict): Dictionary with words as keys and frequencies as values
        output_path (str, optional): Path to save the word cloud image
        title (str, optional): Title for the word cloud
    
    Returns:
        BytesIO: Image data if output_path is None, otherwise None
    """
    # Generate word cloud
    wordcloud = WordCloud(
        width=1200, 
        height=800, 
        background_color='white',
        max_words=200,
        colormap='viridis',
        contour_width=1,
        contour_color='steelblue'
    ).generate_from_frequencies(word_frequencies)
    
    # Create figure
    plt.figure(figsize=(15, 10))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')
    
    if title:
        plt.title(title, fontsize=20)
    
    # Save or display
    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Word cloud saved to: {output_path}")
        return None
    else:
        plt.tight_layout()
        plt.show()

def parse_frequency_data(data_string):
    """
    Parse frequency data from a string in the format:
    word1: frequency1
    word2: frequency2
    ...
    
    Args:
        data_string (str): String containing word frequency data
    
    Returns:
        dict: Dictionary with words as keys and frequencies as values
    """
    word_frequencies = {}
    lines = data_string.strip().split('\n')
    
    for line in lines:
        if ':' in line:
            word, freq = line.split(':', 1)
            word = word.strip()
            try:
                freq = int(freq.strip())
                word_frequencies[word] = freq
            except ValueError:
                print(f"Warning: Could not parse frequency for '{word}': {freq}")
    
    return word_frequencies

def main():
    parser = argparse.ArgumentParser(description='Generate a word cloud from frequency data')
    parser.add_argument('--input', '-i', help='Input file containing word frequencies (optional)')
    parser.add_argument('--output', '-o', help='Output file path for the word cloud image')
    parser.add_argument('--title', '-t', help='Title for the word cloud')
    args = parser.parse_args()
    
    # If input file is provided, read from it
    if args.input and os.path.exists(args.input):
        with open(args.input, 'r', encoding='utf-8') as f:
            data = f.read()
        word_frequencies = parse_frequency_data(data)
    else:
        # Use example data if no input file
        print("No input file provided or file not found. Using example data.")
        word_frequencies = {
            "american_silversmiths": 100,
            "wikipedia": 50,
            "analysis": 25
        }
    
    # Generate output filename if not provided
    if not args.output:
        args.output = "wordcloud_output.png"
    
    # Create word cloud
    create_wordcloud_from_dict(
        word_frequencies, 
        output_path=args.output,
        title=args.title or "Word Frequency Analysis"
    )

if __name__ == "__main__":
    main()
