"""
Notification Service - Email and MS Teams notifications
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional
from src.config.settings import config
from src.database.schema import DatabaseManager, create_notification_record

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending notifications via email and MS Teams"""
    
    def __init__(self):
        self.smtp_config = config.smtp
        self.db_manager = DatabaseManager()
        self.db = self.db_manager.connect()
    
    def send_email(self, subject: str, body: str, to_email: Optional[str] = None) -> bool:
        """
        Send email notification
        
        Args:
            subject: Email subject
            body: Email body (can be HTML)
            to_email: Recipient email (defaults to config)
        
        Returns:
            True if sent successfully
        """
        try:
            to_email = to_email or self.smtp_config.to_email
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            # Use from_name if available, otherwise just email
            from_header = f"{self.smtp_config.from_name} <{self.smtp_config.from_email}>" if hasattr(self.smtp_config, 'from_name') and self.smtp_config.from_name else self.smtp_config.from_email
            msg['From'] = from_header
            msg['To'] = to_email
            
            # Create both plain text and HTML versions
            text_part = MIMEText(body, 'plain')
            html_part = MIMEText(f"<html><body>{body}</body></html>", 'html')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_config.host, self.smtp_config.port) as server:
                server.starttls()
                server.login(self.smtp_config.username, self.smtp_config.password)
                server.send_message(msg)
            
            logger.info(f"✓ Email sent: {subject}")
            return True
        
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP Authentication failed: {str(e)}")
            logger.error("→ If using Gmail: Enable 2FA and create an App Password at https://myaccount.google.com/apppasswords")
            logger.error("→ Set SMTP_PASSWORD in .env to the 16-character App Password (without spaces)")
            return False
        
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return False
    
    def notify_outline_ready(self, book_id: str, title: str) -> bool:
        """Notify that outline is ready for review"""
        subject = f"📖 Outline Ready for Review: {title}"
        body = f"""
The outline for the book "{title}" has been generated and is ready for your review.

Book ID: {book_id}
Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

Please review the outline and update the status:
- Add notes in 'notes_on_outline_after' if changes are needed
- Set 'status_outline_notes' to:
  * 'no_notes_needed' to proceed with chapter generation
  * 'yes' if you need to add revision notes
  * 'no' to pause the workflow

Thank you!
"""
        
        email_sent = self.send_email(subject, body)
        teams_sent = False
        
        # Log notification
        notification = create_notification_record(
            book_id=book_id,
            event_type="outline_ready",
            message=subject,
            status="sent" if email_sent else "failed"
        )
        self.db.notifications_log.insert_one(notification)
        
        return email_sent
    
    def notify_chapter_ready(self, book_id: str, title: str, chapter_number: int) -> bool:
        """Notify that a chapter is ready for review"""
        subject = f"📝 Chapter {chapter_number} Ready: {title}"
        body = f"""
Chapter {chapter_number} for the book "{title}" has been generated and is ready for your review.

Book ID: {book_id}
Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

Please review the chapter and update the status.

Thank you!
"""
        
        email_sent = self.send_email(subject, body)
        teams_sent = False
        
        notification = create_notification_record(
            book_id=book_id,
            event_type="chapter_ready",
            message=subject,
            status="sent" if email_sent else "failed"
        )
        self.db.notifications_log.insert_one(notification)
        
        return email_sent
    
    def notify_book_completed(self, book_id: str, title: str, output_path: str) -> bool:
        """Notify that final book is compiled"""
        subject = f"✅ Book Completed: {title}"
        body = f"""
Great news! The book "{title}" has been completed and compiled.

Book ID: {book_id}
Completed: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
Output File: {output_path}

The final draft is ready for your review.

Congratulations!
"""
        
        email_sent = self.send_email(subject, body)
        teams_sent = False
        
        notification = create_notification_record(
            book_id=book_id,
            event_type="book_completed",
            message=subject,
            status="sent" if email_sent else "failed"
        )
        self.db.notifications_log.insert_one(notification)
        
        return email_sent
    
    def notify_error(self, book_id: str, title: str, error_message: str) -> bool:
        """Notify about errors or paused workflows"""
        subject = f"⚠️ Action Required: {title}"
        body = f"""
The book generation workflow for "{title}" requires attention.

Book ID: {book_id}
Issue: {error_message}
Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

Please check the book status and take appropriate action.

Thank you!
"""
        
        email_sent = self.send_email(subject, body)
        teams_sent = False
        
        notification = create_notification_record(
            book_id=book_id,
            event_type="error",
            message=error_message,
            status="sent" if email_sent else "failed"
        )
        self.db.notifications_log.insert_one(notification)
        
        return email_sent
    
    def close(self):
        """Close database connection"""
        self.db_manager.close()


if __name__ == "__main__":
    # Test notification service
    service = NotificationService()
    
    # Test email
    service.send_email(
        subject="Test Notification",
        body="This is a test email from the Book Generation System"
    )
    
    service.close()
