"""
Chapter Generator Service - Generate chapters with context chaining
"""

import logging
import re
from datetime import datetime
from typing import List, Dict
from src.database.schema import (
    DatabaseManager, 
    create_chapter_record,
    create_chapter_summary_record
)
from src.services.llm_service import LLMService
from src.services.notification_service import NotificationService
from src.config.settings import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChapterGeneratorService:
    """Service to generate book chapters with context chaining"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.db = self.db_manager.connect()
        self.llm_service = LLMService()
        self.notification_service = NotificationService()
    
    def parse_outline_chapters(self, outline_text: str) -> List[Dict[str, str]]:
        """
        Parse outline to extract chapter titles
        
        Returns:
            List of dicts with chapter_number and chapter_title
        """
        chapters = []
        
        # Look for patterns like "Chapter 1:", "1.", "Chapter 1 -", etc.
        chapter_pattern = r'(?:Chapter\s+)?(\d+)[\.:)\-\s]+(.+?)(?=\n|$)'
        
        matches = re.finditer(chapter_pattern, outline_text, re.IGNORECASE | re.MULTILINE)
        
        for match in matches:
            chapter_num = int(match.group(1))
            chapter_title = match.group(2).strip()
            
            # Clean up the title
            chapter_title = re.sub(r'^[\-:)\.\s]+', '', chapter_title)
            chapter_title = re.sub(r'[\n\r]+.*', '', chapter_title)  # Remove anything after newline
            
            if chapter_title and len(chapter_title) > 3:  # Avoid very short/invalid titles
                chapters.append({
                    'chapter_number': chapter_num,
                    'chapter_title': chapter_title
                })
        
        logger.info(f"Parsed {len(chapters)} chapters from outline")
        return chapters
    
    def can_generate_chapter(self, book_id: str, chapter_number: int) -> tuple[bool, str]:
        """
        Check if chapter can be generated based on gating logic
        
        Returns:
            (can_generate, reason)
        """
        book = self.db.books.find_one({'book_id': book_id})
        
        if not book:
            return False, "Book not found"
        
        # Check outline status
        outline_status = book.get('status_outline_notes', '')
        if outline_status != 'no_notes_needed':
            return False, f"Outline not approved yet (status: {outline_status})"
        
        # Check if outline exists
        outline = self.db.outlines.find_one(
            {'book_id': book_id},
            sort=[('version', -1)]
        )
        if not outline:
            return False, "No outline found"
        
        # Check if chapter already exists
        existing_chapter = self.db.chapters.find_one({
            'book_id': book_id,
            'chapter_number': chapter_number
        })
        
        if existing_chapter:
            chapter_status = existing_chapter.get('chapter_notes_status', '')
            
            if chapter_status == 'no_notes_needed':
                return False, f"Chapter {chapter_number} already approved"
            elif chapter_status == 'yes':
                # Check if notes have been added for regeneration
                if existing_chapter.get('chapter_notes'):
                    return True, "Can regenerate with feedback"
                else:
                    return False, f"Waiting for editor notes on chapter {chapter_number}"
            elif chapter_status == 'no' or chapter_status == '':
                return False, f"Chapter {chapter_number} paused - awaiting editor review"
        
        # Check if previous chapters are approved (sequential generation)
        if chapter_number > 1:
            previous_chapter = self.db.chapters.find_one({
                'book_id': book_id,
                'chapter_number': chapter_number - 1
            })
            
            if not previous_chapter:
                return False, f"Previous chapter {chapter_number - 1} not generated yet"
            
            prev_status = previous_chapter.get('chapter_notes_status', '')
            if prev_status not in ['no_notes_needed', 'pending']:
                return False, f"Previous chapter {chapter_number - 1} not approved yet"
        
        return True, "Ready to generate chapter"
    
    def get_previous_summaries(self, book_id: str, up_to_chapter: int) -> List[str]:
        """
        Get summaries of all previous chapters for context
        
        Args:
            book_id: Book ID
            up_to_chapter: Get summaries up to (but not including) this chapter
        
        Returns:
            List of summary texts
        """
        summaries = []
        
        for chapter_num in range(1, up_to_chapter):
            chapter = self.db.chapters.find_one({
                'book_id': book_id,
                'chapter_number': chapter_num
            })
            
            if chapter:
                summary = self.db.chapter_summaries.find_one({
                    'chapter_id': str(chapter['_id'])
                })
                
                if summary:
                    summaries.append(summary['summary_text'])
                else:
                    # If no summary exists, create one from the chapter
                    logger.warning(f"No summary found for chapter {chapter_num}, generating...")
                    summary_text = self.llm_service.generate_summary(
                        chapter['chapter_title'],
                        chapter['content']
                    )
                    
                    # Store the summary
                    summary_record = create_chapter_summary_record(
                        chapter['_id'],
                        book_id,
                        summary_text
                    )
                    self.db.chapter_summaries.insert_one(summary_record)
                    summaries.append(summary_text)
        
        return summaries
    
    def generate_chapter(self, book_id: str, chapter_number: int, chapter_title: str) -> bool:
        """
        Generate a single chapter
        
        Returns:
            True if successful
        """
        try:
            # Check if we can generate
            can_generate, reason = self.can_generate_chapter(book_id, chapter_number)
            
            if not can_generate:
                logger.warning(f"Cannot generate chapter {chapter_number}: {reason}")
                return False
            
            # Get book and outline
            book = self.db.books.find_one({'book_id': book_id})
            outline = self.db.outlines.find_one(
                {'book_id': book_id},
                sort=[('version', -1)]
            )
            
            title = book['title']
            outline_text = outline['outline_text']
            
            # Get previous chapter summaries for context
            previous_summaries = self.get_previous_summaries(book_id, chapter_number)
            
            # Check if this is a regeneration
            existing_chapter = self.db.chapters.find_one({
                'book_id': book_id,
                'chapter_number': chapter_number
            })
            
            is_regeneration = existing_chapter is not None
            chapter_notes = existing_chapter.get('chapter_notes', '') if existing_chapter else ''
            
            logger.info(f"{'Regenerating' if is_regeneration else 'Generating'} Chapter {chapter_number}: {chapter_title}")
            
            # Generate chapter content
            if is_regeneration and chapter_notes:
                # Regenerate with feedback
                chapter_content = self.llm_service.regenerate_with_feedback(
                    original_content=existing_chapter['content'],
                    content_type="chapter",
                    feedback_notes=chapter_notes
                )
            else:
                # Generate new chapter
                chapter_content = self.llm_service.generate_chapter(
                    title=title,
                    outline=outline_text,
                    chapter_number=chapter_number,
                    chapter_title=chapter_title,
                    previous_summaries=previous_summaries,
                    chapter_notes=chapter_notes
                )
            
            # Generate summary for this chapter
            summary_text = self.llm_service.generate_summary(chapter_title, chapter_content)
            
            if is_regeneration:
                # Update existing chapter
                self.db.chapters.update_one(
                    {'book_id': book_id, 'chapter_number': chapter_number},
                    {
                        '$set': {
                            'content': chapter_content,
                            'chapter_notes_status': 'pending',
                            'updated_at': datetime.utcnow()
                        }
                    }
                )
                
                # Update summary
                self.db.chapter_summaries.update_one(
                    {'chapter_id': str(existing_chapter['_id'])},
                    {
                        '$set': {
                            'summary_text': summary_text
                        }
                    }
                )
                
                chapter_id = existing_chapter['_id']
            else:
                # Create new chapter
                chapter_record = create_chapter_record(
                    book_id, chapter_number, chapter_title, chapter_content
                )
                chapter_record['chapter_notes_status'] = 'pending'
                result = self.db.chapters.insert_one(chapter_record)
                chapter_id = result.inserted_id
                
                # Store summary
                summary_record = create_chapter_summary_record(
                    chapter_id, book_id, summary_text
                )
                self.db.chapter_summaries.insert_one(summary_record)
            
            logger.info(f"✓ Chapter {chapter_number} generated: {chapter_title}")
            
            # Send notification
            self.notification_service.notify_chapter_ready(book_id, title, chapter_number)
            
            return True
        
        except Exception as e:
            logger.error(f"Error generating chapter {chapter_number}: {str(e)}")
            
            # Notify about error
            book = self.db.books.find_one({'book_id': book_id})
            if book:
                self.notification_service.notify_error(
                    book_id,
                    book['title'],
                    f"Error generating chapter {chapter_number}: {str(e)}"
                )
            
            return False
    
    def generate_all_chapters(self, book_id: str) -> dict:
        """
        Generate all chapters for a book
        
        Returns:
            Statistics dict
        """
        stats = {
            'total': 0,
            'generated': 0,
            'skipped': 0,
            'failed': 0
        }
        
        # Get outline
        outline = self.db.outlines.find_one(
            {'book_id': book_id},
            sort=[('version', -1)]
        )
        
        if not outline:
            logger.error(f"No outline found for book {book_id}")
            return stats
        
        # Parse chapters from outline
        chapters = self.parse_outline_chapters(outline['outline_text'])
        # Respect configured maximum chapters per book
        max_chapters = getattr(config.app, 'max_chapters_per_book', None)
        if max_chapters and isinstance(max_chapters, int) and max_chapters > 0:
            if len(chapters) > max_chapters:
                logger.info(f"Limiting chapters to first {max_chapters} (configured MAX_CHAPTERS_PER_BOOK)")
            chapters = chapters[:max_chapters]

        stats['total'] = len(chapters)
        
        logger.info(f"Generating {stats['total']} chapters for book {book_id}")
        
        for chapter_info in chapters:
            chapter_num = chapter_info['chapter_number']
            chapter_title = chapter_info['chapter_title']
            
            can_generate, reason = self.can_generate_chapter(book_id, chapter_num)
            
            if can_generate:
                success = self.generate_chapter(book_id, chapter_num, chapter_title)
                if success:
                    stats['generated'] += 1
                else:
                    stats['failed'] += 1
                    break  # Stop on failure for sequential generation
            else:
                logger.info(f"Skipping Chapter {chapter_num}: {reason}")
                stats['skipped'] += 1
        
        logger.info(f"Chapter generation complete: {stats}")
        return stats
    
    def close(self):
        """Close all connections"""
        self.db_manager.close()
        self.notification_service.close()


if __name__ == "__main__":
    # Test chapter generator
    service = ChapterGeneratorService()
    
    # Example: Generate chapters for a specific book
    book_id = "your_book_id_here"
    stats = service.generate_all_chapters(book_id)
    print(f"Chapter Generation Stats: {stats}")
    
    service.close()
