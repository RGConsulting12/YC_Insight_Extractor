# YC Insight Extractor Web Interface

A beautiful, interactive web interface built with Flask and HTMX to visualize all insights, videos, and statistics from the YC Insight Extractor pipeline.

## Features

- 📊 **Dashboard**: Overview of all processed videos with statistics
- 🔍 **Search**: Search across all insights, quotes, and topics
- 📹 **Video Details**: Detailed view of each video's insights and transcript
- 📈 **Statistics**: Comprehensive analytics and metrics
- 💰 **Cost Tracking**: Monitor API costs for processing
- ⚡ **HTMX**: Dynamic, interactive UI without writing JavaScript
- 🎨 **Modern UI**: Clean, responsive design with Tailwind CSS

## Installation

1. Install Flask (if not already installed):
```bash
pip install flask
```

Or add to `requirements.txt`:
```
flask==3.0.0
```

2. Ensure you have processed some videos using the pipeline:
```bash
python src/transcript/pipeline.py
```

## Running the Web Interface

### Option 1: Direct Run
```bash
cd src/web
python app.py
```

### Option 2: From Project Root
```bash
python -m src.web.app
```

### Option 3: Using Flask CLI
```bash
export FLASK_APP=src/web/app.py
flask run
```

The server will start at `http://localhost:5012`

## Usage

### Dashboard
- View all processed videos
- See overall statistics (total videos, insights, nuggets)
- Quick search bar
- Click any video to see detailed insights

### Search
- Search across all insights, quotes, and topics
- Real-time search results (HTMX-powered)
- Click results to view full video details

### Video Details
- Full video metadata
- Summary
- All key insights
- Golden nuggets (memorable quotes)
- Full transcript (collapsible)
- Link to watch on YouTube

### Statistics
- Overall metrics
- Averages per video
- Top videos by insights count

### Cost Tracking
- Total API costs
- Breakdown by service (Whisper, GPT)
- Cost per video
- Recent cost entries

## HTMX Features

The interface uses HTMX for dynamic updates without page reloads:

- **Navigation**: Smooth transitions between pages
- **Search**: Real-time search results
- **Video Cards**: Click to load video details
- **Partial Updates**: Only update necessary parts of the page

## Customization

### Styling
Edit `static/css/style.css` for custom styles.

### Templates
All templates are in `templates/`:
- `base.html`: Base template with navigation
- `dashboard.html`: Main dashboard
- `video_detail.html`: Video detail page
- `search.html`: Search page
- `stats.html`: Statistics page
- `costs.html`: Cost tracking page

### Routes
Add new routes in `app.py`:
```python
@app.route('/your-route')
def your_function():
    return render_template('your_template.html')
```

## API Endpoints

The web interface also exposes JSON API endpoints:

- `GET /api/videos` - List all videos
- `GET /api/video/<video_id>` - Get video insights
- `GET /api/search?q=query` - Search insights

## Development

### Debug Mode
The app runs in debug mode by default. To disable:
```python
app.run(debug=False, host='0.0.0.0', port=5012)
```

### Production Deployment
For production, use a WSGI server like Gunicorn:
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5012 src.web.app:app
```

## Troubleshooting

### No videos showing
- Ensure you've run the pipeline to process videos
- Check that insights files exist in `src/transcript/data/insights/`

### Search not working
- Verify HTMX is loaded (check browser console)
- Check that insight files are valid JSON

### Cost tracking empty
- Cost tracking requires the `CostTracker` utility
- Ensure cost tracking is enabled in the pipeline

## Architecture

```
src/web/
├── app.py              # Flask application
├── templates/          # HTML templates
│   ├── base.html
│   ├── dashboard.html
│   ├── video_detail.html
│   ├── search.html
│   ├── stats.html
│   └── costs.html
└── static/
    └── css/
        └── style.css   # Custom styles
```

## Future Enhancements

- [ ] Export insights to PDF/Markdown
- [ ] Filter videos by date, speaker, topic
- [ ] Visual charts and graphs
- [ ] Bookmark/favorite insights
- [ ] Share insights via URL
- [ ] Dark mode
- [ ] Advanced search filters

## License

Same as main project.
