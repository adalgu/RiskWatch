FROM python:3.12-slim

WORKDIR /app

# Copy the entire project
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r news_storage/web_ui/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Set Python path
ENV PYTHONPATH=/app

# Run the application
CMD ["python", "-m", "news_visualizer.web_ui.app"]
