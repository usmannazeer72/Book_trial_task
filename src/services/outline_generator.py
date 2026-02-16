"""
Outline Generator Service - Generate and manage book outlines
"""

import logging
from datetime import datetime
from src.database.schema import DatabaseManager, create_outline_record
from src.services.llm_service import LLMService
from src.services.notification_service import NotificationService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OutlineGeneratorService:
    """Service to generate book outlines with gating logic"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.db = self.db_manager.connect()
        self.llm_service = LLMService()
        self.notification_service = NotificationService()
    
    def can_generate_outline(self, book_id: str) -> tuple[bool, str]:
        """
        Check if outline can be generated based on gating logic
        
        Returns:
            (can_generate, reason)
        """
        book = self.db.books.find_one({'book_id': book_id})
        
        if not book:
            return False, "Book not found"
        
        # Rule 1: notes_on_outline_before must exist
        if not book.get('notes_on_outline_before'):
            return False, "notes_on_outline_before is required before generating outline"
        
        # Rule 2: Check if outline already exists
        existing_outline = self.db.outlines.find_one({'book_id': book_id})
        if existing_outline:
            # If outline exists, check status
            status = book.get('status_outline_notes', '')
            
            if status == 'no_notes_needed':
                return False, "Outline already approved, ready for chapter generation"
            elif status == 'yes':
                # Editor wants to add notes - can regenerate after notes are added
                if book.get('notes_on_outline_after'):
                    return True, "Can regenerate with feedback"
                else:
                    return False, "Waiting for editor notes (notes_on_outline_after)"
            elif status == 'no' or status == '':
                return False, "Outline paused - awaiting editor review"
        
        # No outline exists and we have the required notes - can generate
        return True, "Ready to generate outline"
    
    def generate_outline(self, book_id: str) -> bool:
        """
        Generate outline for a book
        
        Returns:
            True if successful
        """
        try:
            # Check if we can generate
            can_generate, reason = self.can_generate_outline(book_id)
            
            if not can_generate:
                logger.warning(f"Cannot generate outline for {book_id}: {reason}")
                return False
            
            # Get book details
            book = self.db.books.find_one({'book_id': book_id})
            title = book['title']
            notes_before = book.get('notes_on_outline_before', '')
            notes_after = book.get('notes_on_outline_after', '')
            
            # Check if this is a regeneration
            existing_outline = self.db.outlines.find_one({'book_id': book_id})
            is_regeneration = existing_outline is not None
            
            logger.info(f"{'Regenerating' if is_regeneration else 'Generating'} outline for: {title}")
            
            # Generate outline with LLM
            if is_regeneration and notes_after:
                # Regenerate with feedback
                outline_text = self.llm_service.regenerate_with_feedback(
                    original_content=existing_outline['outline_text'],
                    content_type="outline",
                    feedback_notes=notes_after
                )
            else:
                # Generate new outline
                outline_text = self.llm_service.generate_outline(title, notes_before)
            
            # Determine version number
            version = existing_outline['version'] + 1 if existing_outline else 1
            
            # Store outline
            outline_record = create_outline_record(book_id, outline_text, version)
            self.db.outlines.insert_one(outline_record)
            
            # Update book status
            self.db.books.update_one(
                {'book_id': book_id},
                {
                    '$set': {
                        'status_outline_notes': 'pending',  # Waiting for editor review
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            
            logger.info(f"✓ Outline generated (version {version}) for: {title}")
            
            # Send notification
            self.notification_service.notify_outline_ready(book_id, title)
            
            return True
        
        except Exception as e:
            logger.error(f"Error generating outline for {book_id}: {str(e)}")
            
            # Notify about error
            book = self.db.books.find_one({'book_id': book_id})
            if book:
                self.notification_service.notify_error(
                    book_id, 
                    book['title'], 
                    f"Error generating outline: {str(e)}"
                )
            
            return False
    
    def process_all_pending_outlines(self) -> dict:
        """
        Process all books that need outline generation
        
        Returns:
            Statistics dict
        """
        stats = {
            'total': 0,
            'generated': 0,
            'skipped': 0,
            'failed': 0
        }
        
        # Find all books that might need outline generation
        books = list(self.db.books.find({
            'notes_on_outline_before': {'$ne': ''}
        }))
        
        stats['total'] = len(books)
        logger.info(f"Processing {stats['total']} books for outline generation")
        
        for book in books:
            book_id = book['book_id']
            
            can_generate, reason = self.can_generate_outline(book_id)
            
            if can_generate:
                success = self.generate_outline(book_id)
                if success:
                    stats['generated'] += 1
                else:
                    stats['failed'] += 1
            else:
                logger.info(f"Skipping {book['title']}: {reason}")
                stats['skipped'] += 1
        
        logger.info(f"Outline generation complete: {stats}")
        return stats
    
    def get_outline(self, book_id: str, version: int = None) -> dict:
        """Get outline for a book (latest version by default)"""
        if version:
            return self.db.outlines.find_one({'book_id': book_id, 'version': version})
        else:
            return self.db.outlines.find_one(
                {'book_id': book_id},
                sort=[('version', -1)]
            )
    
    def close(self):
        """Close all connections"""
        self.db_manager.close()
        self.notification_service.close()


if __name__ == "__main__":
    # Test outline generator
    service = OutlineGeneratorService()
    
    # Process all pending outlines
    stats = service.process_all_pending_outlines()
    print(f"Outline Generation Stats: {stats}")
    
    service.close()
