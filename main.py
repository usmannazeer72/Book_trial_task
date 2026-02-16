"""
Main Entry Point - Automated Book Generation System
"""

import argparse
import logging
import sys
from src.orchestrator import BookGenerationOrchestrator
from src.database.schema import DatabaseManager
from src.config.settings import config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def init_database():
    """Initialize database schema"""
    logger.info("Initializing database...")
    db_manager = DatabaseManager()
    db_manager.connect()
    db_manager.initialize_schema()
    db_manager.close()
    logger.info("✓ Database initialized")


def run_workflow(input_source='excel', excel_path=None):
    """Run the complete book generation workflow"""
    logger.info("Starting Book Generation Workflow")
    
    orchestrator = BookGenerationOrchestrator()
    stats = orchestrator.run_complete_workflow(input_source=input_source, excel_path=excel_path)
    orchestrator.close()
    
    return stats


def run_single_book(book_id):
    """Run workflow for a single book"""
    logger.info(f"Processing single book: {book_id}")
    
    orchestrator = BookGenerationOrchestrator()
    results = orchestrator.run_single_book_workflow(book_id)
    orchestrator.close()
    
    return results


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Automated Book Generation System')
    
    parser.add_argument(
        'command',
        choices=['init', 'run', 'run-book'],
        help='Command to execute'
    )
    
    parser.add_argument(
        '--input-source',
        choices=['excel', 'sheets'],
        default='excel',
        help='Input source for book data'
    )
    
    parser.add_argument(
        '--excel-path',
        type=str,
        help='Path to Excel input file'
    )
    
    parser.add_argument(
        '--book-id',
        type=str,
        help='Book ID for run-book command'
    )
    
    args = parser.parse_args()
    
    try:
        # Validate configuration
        config.validate()
        
        if args.command == 'init':
            # Initialize database
            init_database()
        
        elif args.command == 'run':
            # Run complete workflow
            stats = run_workflow(
                input_source=args.input_source,
                excel_path=args.excel_path
            )
            
            print("\n" + "=" * 80)
            print("WORKFLOW COMPLETE")
            print("=" * 80)
            print(f"Books Ingested: {stats['books_ingested']}")
            print(f"Outlines Generated: {stats['outlines_generated']}")
            print(f"Chapters Generated: {stats['chapters_generated']}")
            print(f"Books Compiled: {stats['books_compiled']}")
        
        elif args.command == 'run-book':
            if not args.book_id:
                print("Error: --book-id is required for run-book command")
                sys.exit(1)
            
            results = run_single_book(args.book_id)
            
            print("\n" + "=" * 80)
            print("BOOK PROCESSING COMPLETE")
            print("=" * 80)
            print(f"Book ID: {results['book_id']}")
            print(f"Outline Generated: {results['outline_generated']}")
            print(f"Chapters Generated: {results['chapters_generated']}")
            print(f"Compiled: {results['compiled']}")
            
            if results['output_files']:
                print("\nOutput Files:")
                for format_type, filepath in results['output_files'].items():
                    print(f"  {format_type.upper()}: {filepath}")
    
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
