import streamlit as st
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import nltk
from nltk.corpus import stopwords
import os
import pickle
from collections import Counter
from datetime import datetime
import pandas as pd
import base64
from io import BytesIO

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
    layout="wide"
)

# Add custom CSS for scrollable areas
st.markdown("""
<style>
.scrollable-container {
    max-height: 300px;
    overflow-y: auto;
    border: 1px solid #e0e0e0;
    border-radius: 5px;
    padding: 10px;
    background-color: #f9f9f9;
    font-family: monospace;
    white-space: pre-wrap;
}
</style>
""", unsafe_allow_html=True)

# Title and description
st.title("Wikipedia Word Cloud Visualizer")
st.write("Analyze word frequencies from Wikipedia categories and visualize them as word clouds")

# Sidebar for inputs
with st.sidebar:
    st.header("Analysis Options")
    
    # Input for Wikipedia category
    category = st.text_input("Wikipedia Category:", value="Large_language_models")
    
    # Options
    force_refresh = st.checkbox("Force refresh (ignore cache)")
    max_words = st.slider("Maximum words in cloud:", min_value=50, max_value=300, value=200, step=10)
    colormap = st.selectbox("Color scheme:", 
                           ["viridis", "plasma", "inferno", "magma", "cividis", 
                            "Blues", "Greens", "Reds", "Purples", "Oranges"])
    
    # Generate button
    generate_button = st.button("Generate Word Cloud", type="primary")
    
    # Example categories
    st.subheader("Example Categories")
    example_categories = ["Large_language_models", "American_silversmiths", "Decorative_arts", 
                         "Machine_learning", "Artificial_intelligence"]
    
    for example in example_categories:
        if st.button(example, key=f"example_{example}"):
            category = example
            st.session_state.category = example
            generate_button = True

# Initialize session state for category if needed
if 'category' in st.session_state and not category:
    category = st.session_state.category

# Main content area
if generate_button:
    st.info(f"Analyzing category: {category}")
    
    try:
        # Create analyzer instance
        analyzer = WikiCategoryAnalyzer(category, force_refresh=force_refresh)
        
        # Check if we already have frequency results cached
        word_frequencies, cache_exists = analyzer.load_from_cache("frequency")
        
        if not cache_exists or force_refresh:
            # Get pages in the category
            with st.status("Fetching pages..."):
                pages = analyzer.get_pages_in_category()
            
            if not pages:
                st.error(f"No pages found in category: {category}")
            else:
                # Get content for all pages
                with st.status(f"Fetching content for {len(pages)} pages..."):
                    content_cache = analyzer.get_page_contents(pages)
                
                # Analyze word frequency
                with st.status("Analyzing word frequencies..."):
                    word_frequencies = analyzer.analyze_word_frequency(content_cache)
        
        if word_frequencies:
            # Get top words for the word cloud
            top_words = dict(word_frequencies.most_common(max_words))
            
            # Create two columns for word cloud and statistics
            col1, col2 = st.columns([3, 2])
            
            with col1:
                st.subheader("Word Cloud Visualization")
                
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
                
                # Download buttons for word cloud
                img = BytesIO()
                wordcloud.to_image().save(img, format='PNG')
                img.seek(0)
                
                # Create a safe filename
                safe_category = category.replace(':', '_').replace(' ', '_')
                
                st.download_button(
                    label="Download Word Cloud (PNG)",
                    data=img,
                    file_name=f"{safe_category}_wordcloud.png",
                    mime="image/png"
                )
            
            with col2:
                st.subheader("Top Words")
                
                # Create DataFrame for top 50 words
                top_50_words = [(word, count) for word, count in list(top_words.items())[:50]]
                df = pd.DataFrame(top_50_words, columns=["Word", "Frequency"])
                
                # Display as a table
                st.dataframe(df, use_container_width=True)
                
                # Generate word frequency text
                frequency_text = f"Word frequency analysis for: {category}\n"
                frequency_text += f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                frequency_text += "WORD FREQUENCIES (sorted by frequency):\n"
                frequency_text += "=====================================\n\n"
                
                for word, count in top_words.items():
                    frequency_text += f"{word}: {count}\n"
                
                # Download button for word frequencies
                st.download_button(
                    label="Download Word Frequencies (TXT)",
                    data=frequency_text,
                    file_name=f"{safe_category}_word_frequency.txt",
                    mime="text/plain"
                )
            
            # Article statistics if available
            article_stats_data, stats_exist = analyzer.load_from_cache("article_stats")
            
            if stats_exist and article_stats_data:
                st.subheader("Article Statistics")
                
                # Calculate totals
                total_articles = len(article_stats_data)
                
                if total_articles > 0:
                    total_raw_words = sum(stats['total_words'] for _, stats in article_stats_data.items() if 'total_words' in stats)
                    total_filtered_words = sum(stats['filtered_words'] for _, stats in article_stats_data.items() if 'filtered_words' in stats)
                    
                    # Display summary statistics
                    st.markdown(f"**Total Articles:** {total_articles:,}")
                    st.markdown(f"**Total Words:** {total_raw_words:,}")
                    st.markdown(f"**Filtered Words:** {total_filtered_words:,}")
                    
                    # Avoid division by zero
                    percentage_used = 0
                    if total_raw_words > 0:
                        percentage_used = (total_filtered_words / total_raw_words * 100)
                        st.markdown(f"**Percentage Used:** {percentage_used:.2f}%")
                    else:
                        st.markdown("**Percentage Used:** 0.00%")
                    
                    # Sort articles by word count (descending)
                    sorted_articles = sorted(
                        [(article, stats) for article, stats in article_stats_data.items() 
                         if 'total_words' in stats and 'filtered_words' in stats],
                        key=lambda x: x[1]['total_words'], 
                        reverse=True
                    )
                    
                    if sorted_articles:
                        # Create DataFrame for articles
                        articles_data = []
                        for article, stats in sorted_articles:
                            # Avoid division by zero
                            percentage = 0
                            if stats['total_words'] > 0:
                                percentage = (stats['filtered_words'] / stats['total_words'] * 100)
                            
                            # Create Wikipedia URL for the article
                            wiki_url = f"https://en.wikipedia.org/wiki/{article.replace(' ', '_')}"
                            
                            articles_data.append({
                                "Title": article,
                                "Total Words": stats['total_words'],
                                "Filtered Words": stats['filtered_words'],
                                "% Used": f"{percentage:.2f}%",
                                "Wikipedia Link": wiki_url
                            })
                        
                        if articles_data:
                            articles_df = pd.DataFrame(articles_data)
                            
                            # Display as a scrollable table
                            st.dataframe(
                                articles_df,
                                use_container_width=True,
                                height=300,
                                column_config={
                                    "Wikipedia Link": st.column_config.LinkColumn()
                                }
                            )
                            
                            # Generate article statistics report
                            articles_report = f"Article statistics for: {category}\n"
                            articles_report += f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                            articles_report += f"Total Articles: {total_articles}\n"
                            articles_report += f"Total Words: {total_raw_words:,}\n"
                            articles_report += f"Filtered Words: {total_filtered_words:,}\n"
                            
                            # Avoid division by zero
                            if total_raw_words > 0:
                                articles_report += f"Percentage Used: {percentage_used:.2f}%\n\n"
                            else:
                                articles_report += "Percentage Used: 0.00%\n\n"
                                
                            articles_report += "ARTICLE DETAILS (sorted by word count):\n"
                            articles_report += "=====================================\n\n"
                            
                            for article, stats in sorted_articles:
                                articles_report += f"Title: {article}\n"
                                articles_report += f"Wikipedia URL: https://en.wikipedia.org/wiki/{article.replace(' ', '_')}\n"
                                articles_report += f"Total Words: {stats['total_words']:,}\n"
                                articles_report += f"Filtered Words: {stats['filtered_words']:,}\n"
                                
                                # Avoid division by zero
                                if stats['total_words'] > 0:
                                    articles_report += f"Percentage Used: {(stats['filtered_words'] / stats['total_words'] * 100):.2f}%\n\n"
                                else:
                                    articles_report += "Percentage Used: 0.00%\n\n"
                            
                            # Download button for article statistics
                            st.download_button(
                                label="Download Article Statistics (TXT)",
                                data=articles_report,
                                file_name=f"{safe_category}_article_statistics.txt",
                                mime="text/plain"
                            )
    
    except Exception as e:
        st.error(f"Error analyzing category: {str(e)}")
else:
    st.info("Enter a Wikipedia category and click 'Generate Word Cloud' to start the analysis.")
    
    # Show example categories
    st.write("Try one of the example categories from the sidebar to get started!")
