# Web Interface Guide

## Quick Start

### 1. Install Dependencies
```bash
pip install flask
# Or install all requirements
pip install -r requirements.txt
```

### 2. Run the Server
```bash
# Option 1: Using the run script
python src/web/run_server.py

# Option 2: Direct Python
python -m src.web.app

# Option 3: Flask CLI
export FLASK_APP=src/web/app.py
flask run
```

### 3. Open in Browser
Navigate to: `http://localhost:5012`

## Features Overview

### Dashboard (`/`)
- **Statistics Cards**: Total videos, insights, nuggets, averages
- **Search Bar**: Quick search across all content
- **Video List**: All processed videos with preview
- **Click to View**: Click any video to see detailed insights

### Video Details (`/video/<video_id>`)
- **Video Metadata**: Title, description, publish date, duration
- **Summary**: AI-generated summary of the video
- **Key Insights**: Numbered list of all insights
- **Golden Nuggets**: Memorable quotes in highlighted boxes
- **Full Transcript**: Collapsible transcript view
- **YouTube Link**: Direct link to watch the video

### Search (`/search`)
- **Real-time Search**: Search as you type (HTMX-powered)
- **Cross-video Search**: Search across all insights and quotes
- **Match Highlighting**: See where matches occur
- **Quick Navigation**: Click results to view full video

### Statistics (`/stats`)
- **Overall Metrics**: Total counts and averages
- **Top Videos**: Videos ranked by number of insights
- **Per-video Averages**: Insights and nuggets per video

### Cost Tracking (`/costs`)
- **Total Costs**: Overall API spending
- **Service Breakdown**: Whisper vs GPT costs
- **Per-video Costs**: Cost breakdown by video
- **Recent Entries**: Latest cost tracking entries

## HTMX Features

The interface uses HTMX for a modern, interactive experience:

### Navigation
- Smooth page transitions without full reloads
- URL updates for bookmarking
- Browser back/forward support

### Search
- Real-time search results
- Debounced input (waits 500ms after typing stops)
- Partial page updates

### Video Cards
- Click to load video details
- Content loads in place
- No page refresh

## API Endpoints

The web interface exposes JSON APIs:

### `GET /api/videos`
Returns list of all processed videos:
```json
[
  {
    "video_id": "p8Jx4qvDoSo",
    "title": "Video Title",
    "summary": "...",
    "insights_count": 7,
    "nuggets_count": 4
  }
]
```

### `GET /api/video/<video_id>`
Returns detailed video data:
```json
{
  "video_id": "p8Jx4qvDoSo",
  "insights": {
    "summary": "...",
    "insights": [...],
    "golden_nuggets": [...]
  },
  "metadata": {
    "title": "...",
    "description": "..."
  },
  "transcript": "..."
}
```

### `GET /api/search?q=query`
Returns search results:
```json
[
  {
    "video_id": "p8Jx4qvDoSo",
    "title": "...",
    "matches": ["summary", "insight_0"],
    "summary": "..."
  }
]
```

## Customization

### Changing Port
Edit `app.py`:
```python
app.run(debug=True, host='0.0.0.0', port=8080)  # Change 5012 to 8080
```

### Changing Theme
Edit `templates/base.html` to modify Tailwind classes or add custom CSS.

### Adding New Routes
```python
@app.route('/your-route')
def your_function():
    return render_template('your_template.html', data=your_data)
```

## Troubleshooting

### "No videos showing"
- Ensure you've run the pipeline: `python src/transcript/pipeline.py`
- Check that insights exist: `ls src/transcript/data/insights/`

### "Search not working"
- Check browser console for errors
- Verify HTMX is loaded (check Network tab)
- Ensure insight files are valid JSON

### "Cost tracking empty"
- Cost tracking requires using `CostTracker` in the pipeline
- Check if `data/costs.json` exists

### "Port already in use"
- Change port in `app.py` or `run_server.py`
- Or kill the process using port 5012:
  ```bash
  lsof -ti:5012 | xargs kill
  ```

## Production Deployment

### Using Gunicorn
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5012 src.web.app:app
```

### Using Docker
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5012", "src.web.app:app"]
```

### Environment Variables
- `FLASK_ENV=production` - Production mode
- `FLASK_DEBUG=0` - Disable debug mode
- `SECRET_KEY` - Set a secure secret key

## Architecture

```
src/web/
├── app.py                 # Flask application & routes
├── run_server.py          # Simple startup script
├── templates/            # HTML templates
│   ├── base.html         # Base template
│   ├── dashboard.html    # Main dashboard
│   ├── video_detail.html # Video details
│   ├── search.html       # Search page
│   ├── stats.html        # Statistics
│   └── costs.html        # Cost tracking
└── static/
    └── css/
        └── style.css     # Custom styles
```

## Future Enhancements

- [ ] Export insights to PDF/Markdown
- [ ] Filter by date range, speaker, topic
- [ ] Visual charts (Chart.js integration)
- [ ] Bookmark/favorite insights
- [ ] Share insights via URL
- [ ] Dark mode toggle
- [ ] Advanced search filters
- [ ] Batch export
- [ ] User authentication (optional)

## Tips

1. **Use Browser DevTools**: Check Network tab to see HTMX requests
2. **Check Console**: Look for JavaScript errors
3. **Validate JSON**: Ensure insight files are valid JSON
4. **Monitor Logs**: Flask debug mode shows helpful error messages
5. **HTMX Docs**: See https://htmx.org/docs/ for advanced features

## Support

For issues or questions:
1. Check the main README
2. Review error messages in browser console
3. Check Flask logs in terminal
4. Verify data files exist and are valid
