import streamlit as st
import os
import pickle
import re
import hashlib
from collections import Counter
from datetime import datetime
import json
import base64
from io import BytesIO
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import nltk
from nltk.corpus import stopwords
import requests
import pandas as pd

# Import the WikiCategoryAnalyzer class
from wiki_analyzer import WikiCategoryAnalyzer

# Ensure NLTK data is available
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)

# Set page configuration
st.set_page_config(
    page_title="Wikipedia Word Cloud Visualizer",
    page_icon="☁️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Cache directory setup
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #4527A0;
        text-align: center;
        margin-bottom: 1rem;
    }
    .subheader {
        font-size: 1.5rem;
        color: #5E35B1;
        margin-bottom: 1rem;
    }
    .info-box {
        background-color: #E8EAF6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .success-box {
        background-color: #E8F5E9;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .warning-box {
        background-color: #FFF8E1;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .error-box {
        background-color: #FFEBEE;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .footer {
        text-align: center;
        margin-top: 2rem;
        color: #9E9E9E;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

# Title and description
st.markdown('<h1 class="main-header">Wikipedia Word Cloud Visualizer</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center;">Analyze word frequencies from Wikipedia categories and visualize them as word clouds</p>', unsafe_allow_html=True)

# Sidebar for inputs
with st.sidebar:
    st.markdown('<h2 class="subheader">Analysis Options</h2>', unsafe_allow_html=True)
    
    # Input for Wikipedia category
    category = st.text_input("Wikipedia Category:", placeholder="e.g., Large_language_models")
    
    # Options
    force_refresh = st.checkbox("Force refresh (ignore cache)")
    max_words = st.slider("Maximum words in cloud:", min_value=50, max_value=300, value=200, step=10)
    colormap = st.selectbox("Color scheme:", 
                           ["viridis", "plasma", "inferno", "magma", "cividis", 
                            "Blues", "Greens", "Reds", "Purples", "Oranges"])
    
    # Generate button
    generate_button = st.button("Generate Word Cloud", type="primary", use_container_width=True)
    
    # Example categories
    st.markdown("### Example Categories")
    example_categories = ["Large_language_models", "American_silversmiths", "Decorative_arts", 
                         "Machine_learning", "Artificial_intelligence", "Quantum_computing"]
    
    for example in example_categories:
        if st.button(example, key=f"example_{example}", use_container_width=True):
            category = example
            st.session_state.category = example
            generate_button = True

# Initialize session state for category if needed
if 'category' in st.session_state and not category:
    category = st.session_state.category

# Main content area
if generate_button and category:
    st.session_state.category = category
    
    # Create progress container
    progress_container = st.empty()
    progress_container.markdown('<div class="info-box">Starting analysis...</div>', unsafe_allow_html=True)
    
    try:
        # Create analyzer instance
        analyzer = WikiCategoryAnalyzer(category, force_refresh=force_refresh)
        
        # Check if we already have frequency results cached
        word_frequencies, cache_exists = analyzer.load_from_cache("frequency")
        
        if not cache_exists or force_refresh:
            # Get pages in the category
            progress_container.markdown(f'<div class="info-box">Fetching pages in category: {category}...</div>', unsafe_allow_html=True)
            pages = analyzer.get_pages_in_category()
            
            if not pages:
                st.error(f"No pages found in category: {category}")
            else:
                # Get content for all pages
                progress_container.markdown(f'<div class="info-box">Fetching content for {len(pages)} pages...</div>', unsafe_allow_html=True)
                content_cache = analyzer.get_page_contents(pages)
                
                # Analyze word frequency
                progress_container.markdown('<div class="info-box">Analyzing word frequencies...</div>', unsafe_allow_html=True)
                word_frequencies = analyzer.analyze_word_frequency(content_cache)
                
                if not word_frequencies:
                    st.error("Failed to analyze word frequencies")
        
        # Clear progress container
        progress_container.empty()
        
        if word_frequencies:
            # Get top words for the word cloud
            top_words = dict(word_frequencies.most_common(max_words))
            
            # Create two columns for word cloud and statistics
            col1, col2 = st.columns([3, 2])
            
            with col1:
                st.markdown('<h2 class="subheader">Word Cloud Visualization</h2>', unsafe_allow_html=True)
                
                # Generate word cloud
                wordcloud = WordCloud(
                    width=800, 
                    height=600, 
                    background_color='white',
                    max_words=max_words,
                    colormap=colormap,
                    contour_width=1,
                    contour_color='steelblue'
                ).generate_from_frequencies(top_words)
                
                # Display the word cloud
                fig, ax = plt.subplots(figsize=(10, 8))
                ax.imshow(wordcloud, interpolation='bilinear')
                ax.axis("off")
                st.pyplot(fig)
                
                # Download buttons
                img = BytesIO()
                wordcloud.to_image().save(img, format='PNG')
                img.seek(0)
                
                # Create a safe filename
                safe_category = category.replace(':', '_').replace(' ', '_')
                
                st.download_button(
                    label="Download Word Cloud (PNG)",
                    data=img,
                    file_name=f"{safe_category}_wordcloud.png",
                    mime="image/png",
                    use_container_width=True
                )
                
                # Generate word frequency text file
                frequency_text = f"Word frequency analysis for: {category}\n"
                frequency_text += f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                frequency_text += "WORD FREQUENCIES (sorted by frequency):\n"
                frequency_text += "=====================================\n\n"
                
                for word, count in top_words.items():
                    frequency_text += f"{word}: {count}\n"
                
                st.download_button(
                    label="Download Word Frequencies (TXT)",
                    data=frequency_text,
                    file_name=f"{safe_category}_word_frequency.txt",
                    mime="text/plain",
                    use_container_width=True
                )
            
            with col2:
                st.markdown('<h2 class="subheader">Analysis Results</h2>', unsafe_allow_html=True)
                
                # Display source info
                st.markdown(f"**Category:** {category}")
                st.markdown(f"**Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                st.markdown(f"**Source:** {'Cache' if cache_exists and not force_refresh else 'Fresh Analysis'}")
                st.markdown(f"**Words Analyzed:** {len(word_frequencies):,}")
                
                # Display top words
                st.markdown('<h3 class="subheader">Top Words</h3>', unsafe_allow_html=True)
                
                # Create DataFrame for top 50 words
                top_50_words = [(word, count) for word, count in list(top_words.items())[:50]]
                df = pd.DataFrame(top_50_words, columns=["Word", "Frequency"])
                
                # Display as a table
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                # Get article statistics if available
                article_stats_data, stats_exist = analyzer.load_from_cache("article_stats")
                
                if stats_exist:
                    st.markdown('<h3 class="subheader">Article Statistics</h3>', unsafe_allow_html=True)
                    
                    # Calculate totals
                    total_articles = len(article_stats_data)
                    total_raw_words = sum(stats['total_words'] for _, stats in article_stats_data.items())
                    total_filtered_words = sum(stats['filtered_words'] for _, stats in article_stats_data.items())
                    
                    # Display summary statistics
                    st.markdown(f"**Total Articles:** {total_articles:,}")
                    st.markdown(f"**Total Words:** {total_raw_words:,}")
                    st.markdown(f"**Filtered Words:** {total_filtered_words:,}")
                    st.markdown(f"**Percentage Used:** {(total_filtered_words / total_raw_words * 100):.2f}%")
                    
                    # Sort articles by word count (descending)
                    sorted_articles = sorted(article_stats_data.items(), 
                                           key=lambda x: x[1]['total_words'], 
                                           reverse=True)
                    
                    # Create DataFrame for articles
                    articles_data = []
                    for article, stats in sorted_articles[:20]:  # Show top 20 articles
                        articles_data.append({
                            "Title": article,
                            "Total Words": stats['total_words'],
                            "Filtered Words": stats['filtered_words'],
                            "% Used": f"{(stats['filtered_words'] / stats['total_words'] * 100):.2f}%"
                        })
                    
                    articles_df = pd.DataFrame(articles_data)
                    
                    # Display as a table with a note that it's limited
                    st.markdown("**Top 20 Articles by Word Count:**")
                    st.dataframe(articles_df, use_container_width=True, hide_index=True)
                    
                    if len(sorted_articles) > 20:
                        st.markdown(f"*Showing 20 of {len(sorted_articles)} articles*")
    
    except Exception as e:
        st.error(f"Error analyzing category: {str(e)}")

# Display instructions if no category entered
elif not category:
    st.markdown('<div class="info-box">', unsafe_allow_html=True)
    st.markdown("### How to Use This Tool")
    st.markdown("""
    1. Enter a Wikipedia category name in the sidebar
    2. Click "Generate Word Cloud" to analyze the category
    3. View the word cloud and statistics
    4. Download the word cloud or frequency data
    
    Try one of the example categories to get started!
    """)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Show example word cloud
    st.image("https://raw.githubusercontent.com/lhiebert01/wordcloud-app/main/Large_language_models_visualization.png", 
             caption="Example: Word Cloud for 'Large language models' category")

# Footer
st.markdown('<div class="footer">Wikipedia Word Cloud Visualizer © 2025 | Designed by <a href="https://www.linkedin.com/in/lindsayhiebert/" target="_blank">Lindsay Hiebert</a> | GenAI & Cybersecurity Expert</div>', unsafe_allow_html=True)
