# Wikipedia Category Word Frequency Analyzer

This tool analyzes Wikipedia categories to find the most common non-trivial words across all pages in a category. It includes a robust caching system to avoid redundant API calls and processing.

## Features

- Analyzes any Wikipedia category to find word frequencies
- Implements a three-level caching system:
  - Page list cache: Stores the list of pages in a category
  - Content cache: Stores the raw content of each page
  - Frequency cache: Stores the final word frequency analysis
- Filters out common words (stopwords) for more meaningful results
- Generates word clouds with up to 200 most frequent words
- Provides detailed article statistics including word counts per article
- Saves results to a text file for further analysis
- Web interface for easy interaction and visualization

## Usage

```bash
# Basic usage
python wiki_analyzer.py "Category_Name"

# Force refresh (ignore cache)
python wiki_analyzer.py "Category_Name" --force-refresh

# View results and generate word cloud
python show_results.py "Category_Name" --generate-wordcloud

# View top N words (default: 100, max: 200)
python show_results.py "Category_Name" --top 150
```

Example:
```bash
python wiki_analyzer.py "Large_language_models"
python show_results.py "Large_language_models" --generate-wordcloud
```

## Web Interface

The application includes a web interface for easier interaction:

```bash
# Start the web server
python app.py
```

Then open your browser to http://localhost:5000 to access the interface.

## Cache System

The caching system stores data in the `cache/` directory:
- `{category}_pages.cache`: List of pages in the category
- `{category}_content.cache`: Content of all pages
- `{category}_frequency.cache`: Word frequency analysis results

This prevents redundant API calls and processing when analyzing the same category multiple times.

## Output

The script generates the following outputs:
- `{category}_word_frequency.txt`: Contains all words and their frequencies in descending order (up to 200 words)
- `{category}_wordcloud.png`: Word cloud visualization (when using the --generate-wordcloud option)

It also displays:
- The top words in the console output
- Article statistics showing word counts for each article in the category
- Total word counts across all articles

## Requirements

- Python 3.6+
- Required packages: requests, nltk, matplotlib, wordcloud, flask, tqdm
