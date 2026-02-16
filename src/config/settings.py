"""
Configuration management for the Book Generation System
"""

import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()


class MongoDBConfig(BaseModel):
    """MongoDB configuration"""
    uri: str = Field(default_factory=lambda: os.getenv('MONGODB_URI', 'mongodb://localhost:27017/'))
    database: str = Field(default_factory=lambda: os.getenv('MONGODB_DATABASE', 'book_generation'))


class GroqConfig(BaseModel):
    """Groq API configuration"""
    api_key: str = Field(default_factory=lambda: os.getenv('GROQ_API_KEY', ''))
    model_name: str = Field(default_factory=lambda: os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile'))


class SMTPConfig(BaseModel):
    """SMTP email configuration"""
    host: str = Field(default_factory=lambda: os.getenv('SMTP_HOST', 'smtp.gmail.com'))
    port: int = Field(default_factory=lambda: int(os.getenv('SMTP_PORT', '587')))
    username: str = Field(default_factory=lambda: os.getenv('SMTP_USER', ''))
    password: str = Field(default_factory=lambda: os.getenv('SMTP_PASSWORD', ''))
    from_email: str = Field(default_factory=lambda: os.getenv('FROM_EMAIL', ''))
    from_name: str = Field(default_factory=lambda: os.getenv('FROM_NAME', 'Book Generation System'))
    to_email: str = Field(default_factory=lambda: os.getenv('SMTP_TO_EMAIL', ''))


class TeamsConfig(BaseModel):
    """MS Teams webhook configuration"""
    pass

class AppConfig(BaseModel):
    """Application configuration"""
    log_level: str = Field(default_factory=lambda: os.getenv('LOG_LEVEL', 'INFO'))
    output_directory: str = Field(default_factory=lambda: os.getenv('OUTPUT_DIRECTORY', './output'))
    input_excel_path: str = Field(default_factory=lambda: os.getenv('INPUT_EXCEL_PATH', './input/books_input.xlsx'))
    auto_approve_outlines: bool = Field(default_factory=lambda: os.getenv('AUTO_APPROVE_OUTLINES', 'false').lower() in ('1', 'true', 'yes'))
    auto_generate_chapters: bool = Field(default_factory=lambda: os.getenv('AUTO_GENERATE_CHAPTERS', 'false').lower() in ('1', 'true', 'yes'))
    auto_approve_chapters: bool = Field(default_factory=lambda: os.getenv('AUTO_APPROVE_CHAPTERS', 'false').lower() in ('1', 'true', 'yes'))
    max_chapters_per_book: int = Field(default_factory=lambda: int(os.getenv('MAX_CHAPTERS_PER_BOOK', '3')))


class Config:
    """Main configuration class"""
    
    def __init__(self):
        self.mongodb = MongoDBConfig()
        self.groq = GroqConfig()
        self.smtp = SMTPConfig()
        # Google Sheets support removed
        self.app = AppConfig()
    
    def validate(self):
        """Validate critical configuration"""
        if not self.groq.api_key:
            raise ValueError("GROQ_API_KEY is required")
        
        if not self.mongodb.uri:
            raise ValueError("MONGODB_URI is required")
        
        # Create output directory if it doesn't exist
        os.makedirs(self.app.output_directory, exist_ok=True)
        
        return True


# Global config instance
config = Config()
