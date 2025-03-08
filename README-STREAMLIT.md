# Wikipedia Word Cloud Visualizer - Streamlit Deployment Guide

## Application Overview

The Wikipedia Word Cloud Visualizer is a Streamlit application that allows users to:
- Generate word clouds from Wikipedia categories
- View word frequency statistics
- Access article statistics with direct links to Wikipedia
- Download word clouds, word frequency reports, and article statistics

## Local Development Setup

### Prerequisites
- Python 3.8 or higher
- Conda for environment management

### Setting Up the Development Environment

1. Clone the repository:
```bash
git clone https://github.com/lhiebert01/wordcloud-app.git
cd wordcloud-app
```

2. Create and activate a Conda environment:
```bash
conda create -p venv python=3.12.9 -y
conda activate venv
```

3. Install the required packages:
```bash
pip install -r requirements.txt
```

4. Run the application locally:
```bash
streamlit run streamlit_app_working.py
```

## Deploying to Streamlit Cloud

### Step 1: Prepare Your Repository

Ensure your repository contains the following files:
- `streamlit_app_working.py` (rename to `streamlit_app.py` for deployment)
- `wiki_analyzer.py`
- `requirements.txt`
- `.streamlit/config.toml` (optional for custom theming)

### Step 2: Create a Streamlit Cloud Account

1. Go to [Streamlit Cloud](https://streamlit.io/cloud)
2. Sign up using your GitHub account

### Step 3: Deploy Your App

1. From the Streamlit Cloud dashboard, click "New app"
2. Select your GitHub repository (lhiebert01/wordcloud-app)
3. Select the branch (usually main)
4. Set the main file path to `streamlit_app.py`
5. Click "Deploy"

### Step 4: Configure Environment Variables (if needed)

If your app requires API keys or other environment variables:
1. Go to your app settings in Streamlit Cloud
2. Navigate to the "Secrets" section
3. Add your environment variables in the following format:
```toml
[env]
OPENAI_API_KEY = "your-api-key-here"
```

### Step 5: Advanced Configuration

For advanced configuration options, you can create a `.streamlit/config.toml` file in your repository with custom settings:

```toml
[theme]
primaryColor = "#4527A0"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
font = "sans serif"
```

## Troubleshooting

### Common Issues

1. **Package Installation Failures**
   - Ensure all packages in requirements.txt have compatible versions
   - Consider using pinned versions for critical dependencies

2. **Memory Errors**
   - Large word clouds or processing many articles may cause memory issues
   - Consider adding caching or limiting the number of articles processed

3. **Deployment Failures**
   - Check Streamlit Cloud logs for specific error messages
   - Verify that your main Python file is correctly specified

## Maintenance

To update your deployed application:
1. Push changes to your GitHub repository
2. Streamlit Cloud will automatically redeploy your app

## Resources

- [Streamlit Documentation](https://docs.streamlit.io/)
- [Streamlit Cloud Documentation](https://docs.streamlit.io/streamlit-cloud)
- [Streamlit Community](https://discuss.streamlit.io/)
