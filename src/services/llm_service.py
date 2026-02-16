"""
LLM Service - Integration with Groq API
"""

from groq import Groq
import logging
from typing import Optional, List
import time
import random
from src.config.settings import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMService:
    """Service for interacting with Groq API"""
    
    def __init__(self):
        self.client = Groq(api_key=config.groq.api_key)
        self.model_name = config.groq.model_name
        logger.info(f"✓ Groq API initialized with model: {self.model_name}")

    def _log_available_models(self) -> list:
        """Attempt to list available Groq models and return their names.

        This helps diagnose model-not-found errors by logging what the API supports.
        """
        try:
            models_resp = self.client.models.list()
            names = []

            # Extract model names from the response
            if hasattr(models_resp, 'data'):
                for model in models_resp.data:
                    if hasattr(model, 'id'):
                        names.append(model.id)
                    elif isinstance(model, dict):
                        names.append(model.get('id', str(model)))
                    else:
                        names.append(str(model))
            
            logger.info(f"Available Groq models: {names}")
            return names

        except Exception as e:
            logger.error(f"Could not list Groq models: {e}")
            return []

    def _call_with_retries(self, func, *args, max_attempts: int = 3, initial_backoff: float = 1.0, **kwargs):
        """Call `func` with retries and exponential backoff for transient errors (e.g., 429 rate limits).

        - Retries on messages containing '429', 'quota', or 'rate limit'.
        - Raises the last exception if retries exhausted.
        """
        attempt = 0
        while attempt < max_attempts:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                attempt += 1
                err_str = str(e).lower()
                is_rate = ('429' in err_str) or ('quota' in err_str) or ('rate limit' in err_str)
                if is_rate and attempt < max_attempts:
                    backoff = initial_backoff * (2 ** (attempt - 1))
                    jitter = random.random() * 0.1 * backoff
                    sleep_time = backoff + jitter
                    logger.warning(f"Rate limit detected (attempt {attempt}/{max_attempts}). Retrying in {sleep_time:.1f}s...")
                    time.sleep(sleep_time)
                    continue
                # If rate-limited and attempts exhausted, raise a clearer error
                if is_rate:
                    raise RuntimeError("Rate limit or quota exceeded. Check your Groq billing/usage and consider reducing request rate.") from e
                # Non-rate errors: re-raise
                raise
    
    def generate_outline(self, title: str, notes: str = "") -> str:
        """
        Generate book outline using Groq
        
        Args:
            title: Book title
            notes: Additional notes/requirements for outline
        
        Returns:
            Generated outline as string
        """
        prompt = f"""You are a professional book outline creator. Generate a detailed outline for a book with the following details:

Title: {title}

Additional Requirements/Notes:
{notes if notes else "No additional notes"}

Please create a comprehensive book outline that includes:
1. Introduction/Preface
2. 8-12 main chapters with clear titles
3. Brief description of what each chapter should cover
4. Conclusion/Epilogue

Format the outline clearly with chapter numbers and titles.
"""
        
        try:
            logger.info(f"Generating outline for: {title}")
            
            def _generate():
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": "You are a professional book outline creator."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=2048
                )
                return response.choices[0].message.content
            
            outline = self._call_with_retries(_generate)
            logger.info(f"✓ Outline generated ({len(outline)} characters)")
            return outline
        except Exception as e:
            logger.error(f"Error generating outline: {str(e)}")
            # If model not found, attempt to list available models for debugging
            available = self._log_available_models()
            if available:
                raise RuntimeError(
                    f"Model '{self.model_name}' not available. "
                    f"Available models: {available}. Set GROQ_MODEL in .env to a supported model."
                ) from e
            raise
    
    def generate_chapter(
        self, 
        title: str, 
        outline: str, 
        chapter_number: int,
        chapter_title: str,
        previous_summaries: List[str] = None,
        chapter_notes: str = ""
    ) -> str:
        """
        Generate a single chapter with context from previous chapters
        
        Args:
            title: Book title
            outline: Full book outline
            chapter_number: Current chapter number
            chapter_title: Current chapter title
            previous_summaries: List of summaries from previous chapters
            chapter_notes: Optional notes for this chapter
        
        Returns:
            Generated chapter content
        """
        # Build context from previous chapters
        context = ""
        if previous_summaries and len(previous_summaries) > 0:
            context = "\n\nPREVIOUS CHAPTERS SUMMARY:\n"
            for i, summary in enumerate(previous_summaries, 1):
                context += f"\nChapter {i}: {summary}\n"
        
        prompt = f"""You are a professional book writer. Write Chapter {chapter_number} for the following book:

BOOK TITLE: {title}

FULL BOOK OUTLINE:
{outline}
{context}

CURRENT CHAPTER:
Chapter {chapter_number}: {chapter_title}

{"SPECIAL INSTRUCTIONS/NOTES FOR THIS CHAPTER:" if chapter_notes else ""}
{chapter_notes}

Instructions:
- Write a comprehensive, engaging chapter (approximately 2000-3000 words)
- Maintain consistency with the book's overall theme and previous chapters
- Use clear, professional language
- Include relevant examples or case studies where appropriate
- Ensure smooth flow and logical progression of ideas
- End with a transition that connects to the next chapter

Write the complete chapter content now:
"""
        
        try:
            logger.info(f"Generating Chapter {chapter_number}: {chapter_title}")
            
            def _generate():
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": "You are a professional book writer."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=4096
                )
                return response.choices[0].message.content
            
            chapter_content = self._call_with_retries(_generate)
            logger.info(f"✓ Chapter {chapter_number} generated ({len(chapter_content)} characters)")
            return chapter_content
        except Exception as e:
            logger.error(f"Error generating chapter {chapter_number}: {str(e)}")
            available = self._log_available_models()
            if available:
                raise RuntimeError(
                    f"Model '{self.model_name}' not available. "
                    f"Available models: {available}. Set GROQ_MODEL in .env to a supported model."
                ) from e
            raise
    
    def generate_summary(self, chapter_title: str, chapter_content: str) -> str:
        """
        Generate a concise summary of a chapter
        
        Args:
            chapter_title: Title of the chapter
            chapter_content: Full chapter content
        
        Returns:
            Concise summary (200-300 words)
        """
        prompt = f"""Summarize the following chapter in 200-300 words. Focus on key points, main ideas, and important takeaways.

CHAPTER: {chapter_title}

CONTENT:
{chapter_content}

Provide a clear, concise summary:
"""
        
        try:
            logger.info(f"Generating summary for: {chapter_title}")
            
            def _generate():
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": "You are a professional summarizer."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.5,
                    max_tokens=512
                )
                return response.choices[0].message.content
            
            summary = self._call_with_retries(_generate)
            logger.info(f"✓ Summary generated ({len(summary)} characters)")
            return summary
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            available = self._log_available_models()
            if available:
                raise RuntimeError(
                    f"Model '{self.model_name}' not available. "
                    f"Available models: {available}. Set GROQ_MODEL in .env to a supported model."
                ) from e
            raise
    
    def regenerate_with_feedback(
        self,
        original_content: str,
        content_type: str,  # "outline" or "chapter"
        feedback_notes: str
    ) -> str:
        """
        Regenerate content based on editor feedback
        
        Args:
            original_content: Original generated content
            content_type: Type of content being regenerated
            feedback_notes: Editor's feedback/notes
        
        Returns:
            Regenerated content
        """
        prompt = f"""You previously generated the following {content_type}:

ORIGINAL CONTENT:
{original_content}

EDITOR FEEDBACK:
{feedback_notes}

Please regenerate the {content_type} incorporating the editor's feedback. Maintain the overall structure and quality while addressing all the points mentioned in the feedback.

REGENERATED CONTENT:
"""
        
        try:
            logger.info(f"Regenerating {content_type} with feedback")
            
            def _generate():
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": f"You are a professional {content_type} writer who incorporates feedback."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=4096 if content_type == "chapter" else 2048
                )
                return response.choices[0].message.content
            
            regenerated = self._call_with_retries(_generate)
            logger.info(f"✓ Content regenerated ({len(regenerated)} characters)")
            return regenerated
        except Exception as e:
            logger.error(f"Error regenerating content: {str(e)}")
            available = self._log_available_models()
            if available:
                raise RuntimeError(
                    f"Model '{self.model_name}' not available. "
                    f"Available models: {available}. Set GROQ_MODEL in .env to a supported model."
                ) from e
            raise


if __name__ == "__main__":
    # Test LLM service
    llm = LLMService()
    
    # Test outline generation
    outline = llm.generate_outline(
        title="The Future of Artificial Intelligence",
        notes="Focus on practical applications and ethical considerations"
    )
    print("Generated Outline:")
    print(outline)
    
    # Test chapter generation
    chapter = llm.generate_chapter(
        title="The Future of Artificial Intelligence",
        outline=outline,
        chapter_number=1,
        chapter_title="Introduction to AI"
    )
    print("\nGenerated Chapter:")
    print(chapter[:500] + "...")
