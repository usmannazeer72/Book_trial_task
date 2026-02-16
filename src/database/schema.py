"""
MongoDB Database Schema and Configuration

Collections:
1. books - Main book records with metadata and status
2. outlines - Generated outlines (versioned)
3. chapters - Individual chapters with content
4. chapter_summaries - Summaries for context chaining
5. notifications_log - Notification history
"""

from pymongo import MongoClient, ASCENDING
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()


class DatabaseManager:
    """MongoDB database manager with schema initialization"""
    
    def __init__(self):
        self.uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
        self.db_name = os.getenv('MONGODB_DATABASE', 'book_generation')
        self.client = None
        self.db = None
    
    def connect(self):
        """Establish database connection"""
        self.client = MongoClient(self.uri)
        self.db = self.client[self.db_name]
        print(f"✓ Connected to MongoDB: {self.db_name}")
        return self.db
    
    def initialize_schema(self):
        """Create collections and indexes"""
        if not self.db:
            self.connect()
        
        # Create collections if they don't exist
        collections = {
            'books': [
                ('book_id', ASCENDING),
                ('status_outline_notes', ASCENDING),
                ('book_output_status', ASCENDING)
            ],
            'outlines': [
                ('book_id', ASCENDING),
                ('version', ASCENDING)
            ],
            'chapters': [
                ('book_id', ASCENDING),
                ('chapter_number', ASCENDING),
                ('chapter_notes_status', ASCENDING)
            ],
            'chapter_summaries': [
                ('book_id', ASCENDING),
                ('chapter_id', ASCENDING)
            ],
            'notifications_log': [
                ('book_id', ASCENDING),
                ('sent_at', ASCENDING)
            ]
        }
        
        for collection_name, indexes in collections.items():
            if collection_name not in self.db.list_collection_names():
                self.db.create_collection(collection_name)
                print(f"✓ Created collection: {collection_name}")
            
            # Create indexes
            for field, order in indexes:
                self.db[collection_name].create_index([(field, order)])
        
        print("✓ Database schema initialized")
    
    def close(self):
        """Close database connection"""
        if self.client:
            self.client.close()
            print("✓ Database connection closed")


# Schema Templates
def create_book_record(title, notes_on_outline_before="", book_id=None):
    """Create a new book record"""
    from bson import ObjectId
    
    return {
        '_id': ObjectId(),
        'book_id': book_id or str(ObjectId()),
        'title': title,
        'notes_on_outline_before': notes_on_outline_before,
        'notes_on_outline_after': "",
        'status_outline_notes': "",  # "yes", "no", "no_notes_needed"
        'final_review_notes_status': "",  # "yes", "no", "no_notes_needed"
        'book_output_status': "pending",  # "pending", "in_progress", "completed", "paused"
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
    }


def create_outline_record(book_id, outline_text, version=1):
    """Create an outline record"""
    from bson import ObjectId
    
    return {
        '_id': ObjectId(),
        'book_id': book_id,
        'outline_text': outline_text,
        'version': version,
        'created_at': datetime.utcnow()
    }


def create_chapter_record(book_id, chapter_number, chapter_title, content):
    """Create a chapter record"""
    from bson import ObjectId
    
    return {
        '_id': ObjectId(),
        'book_id': book_id,
        'chapter_number': chapter_number,
        'chapter_title': chapter_title,
        'content': content,
        'chapter_notes_status': "",  # "yes", "no", "no_notes_needed"
        'chapter_notes': "",
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
    }


def create_chapter_summary_record(chapter_id, book_id, summary_text):
    """Create a chapter summary record"""
    from bson import ObjectId
    
    return {
        '_id': ObjectId(),
        'chapter_id': str(chapter_id),
        'book_id': book_id,
        'summary_text': summary_text,
        'created_at': datetime.utcnow()
    }


def create_notification_record(book_id, event_type, message, status="sent"):
    """Create a notification log record"""
    from bson import ObjectId
    
    return {
        '_id': ObjectId(),
        'book_id': book_id,
        'event_type': event_type,
        'message': message,
        'status': status,
        'sent_at': datetime.utcnow()
    }


if __name__ == "__main__":
    # Initialize database
    db_manager = DatabaseManager()
    db_manager.connect()
    db_manager.initialize_schema()
    db_manager.close()
