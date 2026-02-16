"""
Main Orchestrator - Automated Book Generation Workflow
"""

import logging
import time
from typing import Dict, List
from src.database.schema import DatabaseManager
from src.services.ingestion_service import IngestionService
from src.services.outline_generator import OutlineGeneratorService
from src.services.chapter_generator import ChapterGeneratorService
from src.services.compilation_service import CompilationService
from src.config.settings import config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BookGenerationOrchestrator:
    """Main orchestrator for the automated book generation workflow"""
    
    def __init__(self):
        logger.info("Initializing Book Generation Orchestrator")
        
        self.ingestion_service = IngestionService()
        self.outline_service = OutlineGeneratorService()
        self.chapter_service = ChapterGeneratorService()
        self.compilation_service = CompilationService()
        self.db_manager = DatabaseManager()
        self.db = self.db_manager.connect()
    
    def run_complete_workflow(self, input_source: str = 'excel', excel_path: str = None) -> Dict:
        """
        Run the complete book generation workflow
        
        Args:
            input_source: 'excel' or 'sheets'
            excel_path: Path to Excel file (if input_source is 'excel')
        
        Returns:
            Summary statistics
        """
        stats = {
            'books_ingested': 0,
            'outlines_generated': 0,
            'chapters_generated': 0,
            'books_compiled': 0,
            'errors': []
        }
        
        try:
            # Step 1: Ingest data
            logger.info("=" * 80)
            logger.info("STEP 1: INGESTING BOOK DATA")
            logger.info("=" * 80)
            
            if input_source == 'excel':
                path = excel_path or config.app.input_excel_path
                book_ids = self.ingestion_service.ingest_from_excel(path)
            else:
                book_ids = self.ingestion_service.ingest_from_google_sheets()
            
            stats['books_ingested'] = len(book_ids)
            logger.info(f"✓ Ingested {len(book_ids)} books")
            
            # Step 2: Generate outlines
            logger.info("\n" + "=" * 80)
            logger.info("STEP 2: GENERATING OUTLINES")
            logger.info("=" * 80)
            
            outline_stats = self.outline_service.process_all_pending_outlines()
            stats['outlines_generated'] = outline_stats['generated']

            # If configured, auto-approve outlines immediately so chapters can be generated
            if getattr(config.app, 'auto_approve_outlines', False):
                logger.info("Auto-approving generated outlines (AUTO_APPROVE_OUTLINES=True)")
                # Find books that have an outline and are pending
                pending_with_outline = list(self.db.books.find({'status_outline_notes': 'pending'}))
                for b in pending_with_outline:
                    # Ensure an outline exists
                    outline_doc = self.db.outlines.find_one({'book_id': b['book_id']})
                    if outline_doc:
                        self.db.books.update_one({'book_id': b['book_id']}, {'$set': {'status_outline_notes': 'no_notes_needed'}})
                        logger.info(f"Auto-approved outline for: {b['title']}")
            
            # Step 3: Generate chapters (for approved outlines)
            logger.info("\n" + "=" * 80)
            logger.info("STEP 3: GENERATING CHAPTERS")
            logger.info("=" * 80)
            
            # Find books with approved outlines
            approved_books = list(self.db.books.find({
                'status_outline_notes': 'no_notes_needed'
            }))
            
            total_chapters = 0
            for book in approved_books:
                book_id = book['book_id']
                logger.info(f"\nProcessing chapters for: {book['title']}")
                
                chapter_stats = self.chapter_service.generate_all_chapters(book_id)
                total_chapters += chapter_stats['generated']

                # If configured, auto-approve chapters so compilation can proceed
                if getattr(config.app, 'auto_approve_chapters', False):
                    logger.info(f"Auto-approving chapters for {book['title']} (AUTO_APPROVE_CHAPTERS=True)")
                    self.db.chapters.update_many(
                        {'book_id': book_id},
                        {'$set': {'chapter_notes_status': 'no_notes_needed'}}
                    )
            
            stats['chapters_generated'] = total_chapters
            
            # Step 4: Compile final books (for books with all chapters approved)
            logger.info("\n" + "=" * 80)
            logger.info("STEP 4: COMPILING FINAL BOOKS")
            logger.info("=" * 80)
            
            # Find books ready for compilation
            for book in approved_books:
                book_id = book['book_id']
                
                can_compile, reason = self.compilation_service.can_compile(book_id)
                
                if can_compile:
                    logger.info(f"\nCompiling: {book['title']}")
                    output_files = self.compilation_service.compile_book(book_id)
                    
                    if output_files:
                        stats['books_compiled'] += 1
                else:
                    logger.info(f"Cannot compile {book['title']}: {reason}")
            
            # Final summary
            logger.info("\n" + "=" * 80)
            logger.info("WORKFLOW COMPLETE")
            logger.info("=" * 80)
            logger.info(f"Books Ingested: {stats['books_ingested']}")
            logger.info(f"Outlines Generated: {stats['outlines_generated']}")
            logger.info(f"Chapters Generated: {stats['chapters_generated']}")
            logger.info(f"Books Compiled: {stats['books_compiled']}")
            
            return stats
        
        except Exception as e:
            logger.error(f"Workflow error: {str(e)}")
            stats['errors'].append(str(e))
            return stats
    
    def run_single_book_workflow(self, book_id: str) -> Dict:
        """
        Run workflow for a single book
        
        Args:
            book_id: Book ID to process
        
        Returns:
            Workflow results
        """
        results = {
            'book_id': book_id,
            'outline_generated': False,
            'chapters_generated': 0,
            'compiled': False,
            'output_files': {}
        }
        
        try:
            book = self.db.books.find_one({'book_id': book_id})
            if not book:
                logger.error(f"Book {book_id} not found")
                return results
            
            logger.info(f"Processing book: {book['title']}")
            
            # Step 1: Generate outline
            can_generate, reason = self.outline_service.can_generate_outline(book_id)
            if can_generate:
                success = self.outline_service.generate_outline(book_id)
                results['outline_generated'] = success
                
                # Wait for manual approval (in real scenario)
                logger.info("⚠ Outline generated. Waiting for editor approval...")
                logger.info("  Update 'status_outline_notes' to 'no_notes_needed' to proceed")
                return results
            
            # Step 2: Generate chapters
            outline_status = book.get('status_outline_notes', '')
            if outline_status == 'no_notes_needed':
                chapter_stats = self.chapter_service.generate_all_chapters(book_id)
                results['chapters_generated'] = chapter_stats['generated']
                
                # Wait for chapter approval
                logger.info("⚠ Chapters generated. Waiting for editor approval...")
                logger.info("  Update 'chapter_notes_status' to 'no_notes_needed' for each chapter")
                return results
            
            # Step 3: Compile
            can_compile, reason = self.compilation_service.can_compile(book_id)
            if can_compile:
                output_files = self.compilation_service.compile_book(book_id)
                results['compiled'] = bool(output_files)
                results['output_files'] = output_files
            
            return results
        
        except Exception as e:
            logger.error(f"Error processing book {book_id}: {str(e)}")
            return results
    
    def close(self):
        """Close all service connections"""
        self.ingestion_service.close()
        self.outline_service.close()
        self.chapter_service.close()
        self.compilation_service.close()
        self.db_manager.close()


if __name__ == "__main__":
    orchestrator = BookGenerationOrchestrator()
    
    # Run complete workflow
    stats = orchestrator.run_complete_workflow(input_source='excel')
    
    print("\n" + "=" * 80)
    print("FINAL STATISTICS")
    print("=" * 80)
    print(f"Books Ingested: {stats['books_ingested']}")
    print(f"Outlines Generated: {stats['outlines_generated']}")
    print(f"Chapters Generated: {stats['chapters_generated']}")
    print(f"Books Compiled: {stats['books_compiled']}")
    
    if stats['errors']:
        print(f"\nErrors: {len(stats['errors'])}")
        for error in stats['errors']:
            print(f"  - {error}")
    
    orchestrator.close()
