import os
import json
import httpx
from typing import Optional
from fastapi import HTTPException
from openai import OpenAI, AsyncOpenAI, APIError, APIConnectionError
import logging

logger = logging.getLogger(__name__)


class OpenRouterClient:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        # Get from parameters or environment variables
        self.api_key = api_key or os.getenv("OPEN_ROUTER_API_KEY")
        self.base_url = base_url or os.getenv("OPEN_ROUTER_URL", "https://openrouter.ai/api/v1")
        self.is_enabled = bool(self.api_key)  # Track if the client is enabled

        if self.is_enabled:
            logger.info(f"OpenRouter API configured with base URL: {self.base_url}")

            # Initialize OpenAI SDK v2.0.0+ compatible clients
            # For synchronous operations
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            
            # For asynchronous operations
            self.async_client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            
            logger.info("OpenRouter client initialized successfully with valid API key")
        else:
            logger.warning("OPEN_ROUTER_API_KEY not set. Using simulated responses only.")
            self.client = None
            self.async_client = None
        
        # HTTP client for direct calls if needed
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def generate_response(self, message: str) -> Optional[str]:
        """
        Generate a response from OpenRouter API using OpenAI SDK v2.0.0+
        """
        # Validate inputs before making LLM call
        if not message or not message.strip():
            logger.warning("Input validation failed: message is empty or None")
            return self._get_simulated_response("empty input received")

        # If API is not enabled, use simulated response
        if not self.is_enabled:
            logger.info("OpenRouter API not enabled, using simulated response")
            return self._get_simulated_response(message)

        try:
            # Use the async client for async operations
            logger.info(f"Attempting to generate response for message: '{message[:100]}...'")
            
            response = await self.async_client.chat.completions.create(
                model="openai/gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful AI assistant for a task management application. Respond concisely and helpfully to user requests about tasks, skills, or general questions. Be friendly and professional."
                    },
                    {
                        "role": "user",
                        "content": message
                    }
                ],
                max_tokens=500,
                temperature=0.7
            )

            logger.info(f"OpenRouter response received with status code from API")

            # Extract content using OpenAI SDK v2.0.0+ response object
            if response.choices and len(response.choices) > 0:
                first_choice = response.choices[0]
                content = first_choice.message.content

                if content is None:
                    content = ""

                logger.info(f"Raw generated content: '{content}'")

                # Trim whitespace and validate content length
                cleaned_content = content.strip()
                logger.info(f"Cleaned content length: {len(cleaned_content)}")

                # Validate content length (>5 characters)
                if cleaned_content and len(cleaned_content) >= 5:
                    logger.info(f"Successfully validated response with {len(cleaned_content)} characters")
                    return cleaned_content
                else:
                    logger.warning(f"Generated content was too short after cleaning: '{cleaned_content}'")
                    return self._get_simulated_response(message)
            else:
                logger.warning("OpenRouter response missing choices array or it's empty")
                return self._get_simulated_response(message)

        except APIConnectionError as e:
            logger.error(f"OpenRouter API connection error: {str(e)}")
            return self._get_simulated_response(message)

        except APIError as e:
            logger.error(f"OpenRouter API error: {str(e)}")
            return self._get_simulated_response(message)

        except Exception as e:
            logger.error(f"Unexpected error during API call: {str(e)}", exc_info=True)
            return self._get_simulated_response(message)

    def _get_simulated_response(self, user_message: str) -> str:
        """
        Generate a simulated AI response when the real API is not available
        """
        import random

        # Basic simulation based on the type of question
        user_lower = user_message.lower()

        if any(word in user_lower for word in ['hello', 'hi', 'hey', 'greetings']):
            responses = [
                f"Hello there! I received your message: '{user_message}'. I'm an AI assistant ready to help!",
                f"Hi! Thanks for reaching out with: '{user_message}'. How can I assist you today?",
                f"Greetings! I see you said '{user_message}'. I'm here to help answer questions and provide assistance."
            ]
        elif any(word in user_lower for word in ['how are you', 'how do you do', 'how are you doing']):
            responses = [
                "I'm functioning well, thank you for asking! I'm an AI designed to assist with your questions and tasks.",
                "I'm operating optimally! As an AI, I don't experience emotions, but I'm ready to help you.",
                "Thank you for asking! I'm an artificial intelligence assistant, so I don't have feelings, but I'm ready to assist!"
            ]
        elif any(word in user_lower for word in ['thank', 'thanks', 'appreciate']):
            responses = [
                "You're welcome! Is there anything else I can help you with?",
                "I'm glad I could be of assistance! Let me know if you need anything else.",
                "Happy to help! Feel free to ask if you have more questions."
            ]
        elif any(word in user_lower for word in ['what', 'how', 'when', 'where', 'who', 'why']):
            responses = [
                f"That's an interesting question about '{user_message}'. As an AI, I process information to provide helpful responses.",
                f"I understand you're asking about '{user_message}'. I analyze patterns in data to generate responses.",
                f"Regarding '{user_message}', I use advanced algorithms to understand and respond to your queries."
            ]
        else:
            responses = [
                f"I've processed your message: '{user_message}'. As an AI assistant, I aim to provide helpful and informative responses.",
                f"I understand you're saying '{user_message}'. I'm designed to assist with various questions and tasks.",
                f"Thanks for sharing '{user_message}'. I'm here to provide useful information and support.",
                f"I've analyzed '{user_message}' and I'm ready to help. As an AI, I can assist with information and problem-solving.",
                f"Your input '{user_message}' has been received. I'm prepared to help with questions, explanations, or suggestions."
            ]

        return random.choice(responses)

    async def close(self):
        """Close the HTTP client"""
        await self.http_client.aclose()


# Global instance - lazily initialized
_openrouter_client = None


def get_openrouter_client() -> OpenRouterClient:
    """Get or create the global OpenRouter client instance"""
    global _openrouter_client
    if _openrouter_client is None:
        _openrouter_client = OpenRouterClient()
    return _openrouter_client


class _LazyOpenRouterClient:
    """Lazy wrapper that delays OpenRouter client initialization"""
    def __getattr__(self, name):
        client = get_openrouter_client()
        return getattr(client, name)


# Global instance for backward compatibility - uses lazy initialization
openrouter_client = _LazyOpenRouterClient()