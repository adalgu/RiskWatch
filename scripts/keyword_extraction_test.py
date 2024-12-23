import os
import json
import asyncio
from typing import List, Dict, Any
from openai import AsyncOpenAI
import anthropic
import google.generativeai as genai
from konlpy.tag import Okt
from dotenv import load_dotenv

from news_collector.collectors.api_metadata_collector import APIMetadataCollector

# Load environment variables
load_dotenv()

# Model configurations
CHATGPT_MODEL = "gpt-4o-mini"
CLAUDE_MODEL = "claude-3-5-haiku-20241022"
GEMINI_MODEL = "gemini-1.5-flash-8b"
SYSTEM_PROMPT = "You are a keyword extraction expert. Extract the most important keywords from the given text. Return only the keywords as a comma-separated list."

# Initialize API clients
chatgpt = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
claude = anthropic.Anthropic()
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

class KeywordExtractor:
    def __init__(self):
        self.okt = Okt()
        self.chatgpt_model = CHATGPT_MODEL
        self.claude_model = CLAUDE_MODEL
        self.gemini_model = GEMINI_MODEL

    def extract_with_konlpy(self, text: str, top_n: int = 5) -> tuple[List[str], str]:
        """Extract keywords using KoNLPy (Okt)"""
        # Normalize and pos tag the text
        tagged = self.okt.pos(text, norm=True, stem=True)
        
        # Filter for nouns and meaningful words
        words = [word for word, pos in tagged if pos in ['Noun', 'Adjective', 'Verb', 'Foreign'] and len(word) > 1]
        
        # Count word frequencies
        word_count = {}
        for word in words:
            word_count[word] = word_count.get(word, 0) + 1
        
        # Sort by frequency and return top N
        sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
        keywords = [word for word, _ in sorted_words[:top_n]]
        return keywords, "Okt"

    async def extract_with_chatgpt(self, text: str, top_n: int = 5) -> tuple[List[str], str]:
        """Extract keywords using ChatGPT API"""
        try:
            response = await chatgpt.chat.completions.create(
                model=self.chatgpt_model,
                messages=[
                    {"role": "system", "content": f"{SYSTEM_PROMPT}"},
                    {"role": "user", "content": f"Extract top {top_n} keywords from this text: {text}"}
                ]
            )
            keywords = response.choices[0].message.content.split(',')
            keywords = [k.strip() for k in keywords[:top_n]]
            return keywords, response.model
        except Exception as e:
            print(f"ChatGPT API error: {e}")
            return [], ""

    async def extract_with_claude(self, text: str, top_n: int = 5) -> tuple[List[str], str]:
        """Extract keywords using Claude API"""
        try:
            message = claude.messages.create(
                model=self.claude_model,
                max_tokens=1000,
                temperature=0,
                system=f"{SYSTEM_PROMPT}",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text", 
                                "text": f"Extract top {top_n} keywords from this text: {text}"
                            }
                        ]
                    }
                ]
            )
            keywords = message.content[0].text.split(',')
            keywords = [k.strip() for k in keywords[:top_n]]
            return keywords, message.model
        except Exception as e:
            print(f"Claude API error: {e}")
            return [], ""

    async def extract_with_gemini(self, text: str, top_n: int = 5) -> tuple[List[str], str]:
        """Extract keywords using Gemini API"""
        try:
            gemini = genai.GenerativeModel(
                model_name = GEMINI_MODEL,
                system_instruction = f"{SYSTEM_PROMPT}")
            response = gemini.generate_content(
                f"Extract top {top_n} most important keywords from this text. Return only the keywords as a comma-separated list, no explanations: {text}"
            )
            keywords = response.text.split(',')
            keywords = [k.strip() for k in keywords[:top_n]]
            return keywords, self.gemini_model
        except Exception as e:
            print(f"Gemini API error: {e}")
            return [], ""

async def main():
    # Initialize collector and extractor
    collector = APIMetadataCollector()
    extractor = KeywordExtractor()
    
    # Collect news articles
    keyword = "카카오모빌리티"  # Example search keyword
    result = await collector.collect(keyword=keyword, max_articles=1)
    
    print(f"\nCollected {len(result['items'])} articles")
    print(f"Total results available: {result['total']}")
    
    # Process each article
    for idx, article in enumerate(result['items'], 1):
        print(f"\nArticle {idx}:")
        print(f"Title: {article['title']}")
        print(f"Description: {article['description']}")
        
        # Combine title and description for keyword extraction
        text = f"Title : {article['title']}, Description : {article['description']}"
        
        # Extract keywords using different methods
        print("\nKeywords extracted using KoNLPy:")
        konlpy_keywords, konlpy_model = extractor.extract_with_konlpy(text)
        print(f"Model: {konlpy_model}")
        print(konlpy_keywords)
        
        print("\nKeywords extracted using ChatGPT:")
        chatgpt_keywords, chatgpt_model = await extractor.extract_with_chatgpt(text)
        print(f"Model: {chatgpt_model}")
        print(chatgpt_keywords)
        
        print("\nKeywords extracted using Claude:")
        claude_keywords, claude_model = await extractor.extract_with_claude(text)
        print(f"Model: {claude_model}")
        print(claude_keywords)

        print("\nKeywords extracted using Gemini:")
        gemini_keywords, gemini_model = await extractor.extract_with_gemini(text)
        print(f"Model: {gemini_model}")
        print(gemini_keywords)
        
        print("-" * 80)

    await collector.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
