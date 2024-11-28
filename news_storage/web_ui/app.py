import os
import sys
from pathlib import Path

# Add the project root to Python path
root_dir = Path(__file__).parent.parent.parent
sys.path.append(str(root_dir))

from flask import Flask, render_template, request, jsonify
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
from news_storage.models import Article, Content, Comment, CommentStats

app = Flask(__name__)

# Database setup - use environment variable with fallback
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:password@postgres:5432/news_db')
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/articles')
def get_articles():
    session = Session()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    articles = session.query(Article)\
        .order_by(desc(Article.published_at))\
        .offset((page - 1) * per_page)\
        .limit(per_page)\
        .all()
    
    result = []
    for article in articles:
        article_data = {
            'id': article.id,
            'title': article.title,
            'publisher': article.publisher,
            'published_at': article.published_at.isoformat() if article.published_at else None,
            'comment_count': len(article.comments),
            'naver_link': article.naver_link
        }
        result.append(article_data)
    
    return jsonify(result)

@app.route('/api/article/<int:article_id>')
def get_article(article_id):
    session = Session()
    article = session.query(Article).get(article_id)
    
    if not article:
        return jsonify({'error': 'Article not found'}), 404
    
    content = article.content.content if article.content else None
    comments = []
    for comment in article.comments:
        comment_data = {
            'content': comment.content,
            'username': comment.username,
            'timestamp': comment.timestamp.isoformat() if comment.timestamp else None,
            'likes': comment.likes,
            'dislikes': comment.dislikes,
            'reply_count': comment.reply_count
        }
        if comment.stats:
            comment_data['stats'] = {
                'sentiment_distribution': comment.stats.sentiment_distribution,
                'gender_ratio': comment.stats.gender_ratio,
                'age_distribution': comment.stats.age_distribution
            }
        comments.append(comment_data)
    
    return jsonify({
        'article': {
            'title': article.title,
            'publisher': article.publisher,
            'published_at': article.published_at.isoformat() if article.published_at else None,
            'content': content,
            'naver_link': article.naver_link
        },
        'comments': comments
    })

if __name__ == '__main__':
    print(f"Starting Flask app with DATABASE_URL: {DATABASE_URL}")
    print(f"Python path: {sys.path}")
    app.run(debug=True, host='0.0.0.0', port=5000)
