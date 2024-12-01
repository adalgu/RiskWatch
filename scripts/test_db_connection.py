import psycopg2

def test_connection():
    try:
        conn = psycopg2.connect(
            host="morrison-newsletter-bold-perry.trycloudflare.com",
            database="news_db",
            user="postgres",
            password="password"
        )
        print("Connection successful!")
        
        # Test query
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()
        print(f"PostgreSQL version: {version[0]}")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"Connection failed: {str(e)}")

if __name__ == "__main__":
    test_connection()
