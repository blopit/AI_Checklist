from sqlalchemy import create_engine, text
import os
import sys

def test_connection():
    # SQLite database URL
    database_url = "sqlite:///./checklist.db"
    
    try:
        # Create engine
        print(f"Attempting to connect to database...")
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False}  # Needed for SQLite
        )
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("Successfully connected to the database!")
            print("Test query result:", result.fetchone()[0])
            
    except Exception as e:
        print(f"Error connecting to database: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    test_connection() 