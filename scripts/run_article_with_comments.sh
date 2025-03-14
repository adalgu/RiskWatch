#!/bin/bash
# Script to collect metadata for a specific article URL and then collect comments for it

# Default values
ARTICLE_URL=""
NO_STATS=false
RETRIES=3

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --article_url)
      ARTICLE_URL="$2"
      shift 2
      ;;
    --no-stats)
      NO_STATS=true
      shift
      ;;
    --retries)
      RETRIES="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Check if article URL is provided
if [ -z "$ARTICLE_URL" ]; then
  echo "Error: Article URL is required"
  echo "Usage: $0 --article_url <URL> [--no-stats] [--retries <number>]"
  exit 1
fi

# Build command
CMD="python scripts/collect_article_with_comments.py --article_url \"$ARTICLE_URL\""

if [ "$NO_STATS" = true ]; then
  CMD="$CMD --no-stats"
fi

CMD="$CMD --retries $RETRIES"

# Run the command
echo "Running: $CMD"
eval $CMD
