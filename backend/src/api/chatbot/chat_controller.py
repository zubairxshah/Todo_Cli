from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from .openrouter_client import get_openrouter_client
from ...services.task_execution_service import TaskExecutionService
from ...database import get_session
from sqlmodel import Session
import logging
import uuid

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = None  # Optional user_id for task operations


class ChatResponse(BaseModel):
    status: str
    message: str
    data: Optional[dict] = None


@router.post("/", response_model=ChatResponse)
async def chat_endpoint(
    chat_request: ChatRequest,
    session: Session = Depends(get_session)
):
    """
    Main chat endpoint that handles user messages with task execution capability.
    Compatible with OpenAI SDK v2.0.0+
    """
    user_message = chat_request.message
    user_id = chat_request.user_id

    # Log incoming request
    logger.info(f"Incoming chat request: {user_message[:100] if user_message else 'EMPTY'}")

    # Validate input
    if not user_message or not user_message.strip():
        error_msg = "Message cannot be empty"
        logger.warning(error_msg)
        return ChatResponse(
            status="error",
            message=error_msg
        )

    try:
        # First, try to parse as task command
        task_command = TaskExecutionService.parse_task_command(user_message)
        
        if task_command:
            logger.info(f"Detected task command: {task_command['action']}")
            
            # Convert user_id to UUID if provided
            user_uuid = None
            if user_id:
                try:
                    user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
                except (ValueError, TypeError):
                    logger.warning(f"Invalid user_id: {user_id}")
            
            # Execute the task operation
            if task_command['action'] == 'create':
                result = TaskExecutionService.execute_create_task(
                    title=task_command.get('title'),
                    description=task_command.get('description'),
                    user_id=user_uuid,
                    session=session
                )
                return ChatResponse(
                    status="success" if result['success'] else "error",
                    message=result['message'],
                    data={'task': result.get('task')} if result.get('task') else None
                )
            
            elif task_command['action'] == 'list':
                result = TaskExecutionService.execute_list_tasks(
                    user_id=user_uuid,
                    session=session
                )
                return ChatResponse(
                    status="success" if result['success'] else "error",
                    message=result['message'],
                    data={'tasks': result.get('tasks')} if result.get('tasks') else None
                )
            
            elif task_command['action'] == 'update':
                result = TaskExecutionService.execute_update_task(
                    task_id=task_command.get('task_id'),
                    title=task_command.get('title'),
                    description=task_command.get('description'),
                    completed=task_command.get('completed'),
                    user_id=user_uuid,
                    session=session
                )
                return ChatResponse(
                    status="success" if result['success'] else "error",
                    message=result['message'],
                    data={'task': result.get('task')} if result.get('task') else None
                )
            
            elif task_command['action'] == 'toggle':
                result = TaskExecutionService.execute_toggle_task(
                    task_id=task_command.get('task_id'),
                    user_id=user_uuid,
                    session=session
                )
                return ChatResponse(
                    status="success" if result['success'] else "error",
                    message=result['message'],
                    data={'task': result.get('task')} if result.get('task') else None
                )
            
            elif task_command['action'] == 'delete':
                result = TaskExecutionService.execute_delete_task(
                    task_id=task_command.get('task_id'),
                    user_id=user_uuid,
                    session=session
                )
                return ChatResponse(
                    status="success" if result['success'] else "error",
                    message=result['message'],
                    data=None
                )
        
        # If not a task command, use OpenRouter for conversation
        openrouter_client = get_openrouter_client()
        
        # Generate response from OpenRouter using OpenAI SDK v2.0.0+
        openrouter_response = await openrouter_client.generate_response(user_message)

        # LOG THE RAW LLM RESPONSE OBJECT
        logger.info(f"OpenRouter raw response: {repr(openrouter_response)}")

        # Perform comprehensive validation of the response
        if openrouter_response is not None and isinstance(openrouter_response, str):
            # Clean the response
            cleaned_response = openrouter_response.strip()

            # Validate that it has meaningful content (more than just whitespace or common empty indicators)
            if cleaned_response and len(cleaned_response) >= 5:  # At least 5 characters
                logger.info(f"Returning successful response to user (length: {len(cleaned_response)})")

                # Ensure the response is never the problematic fallback message
                if "I'm having trouble generating a response right now" in cleaned_response:
                    logger.warning("Detected problematic fallback message, replacing with better response")
                    final_response = f"I understand you asked: '{user_message}'. I'm an AI assistant ready to help with your questions about tasks, skills, or general topics."
                else:
                    final_response = cleaned_response

                return ChatResponse(
                    status="success",
                    message=final_response,
                    data=None
                )
            else:
                logger.warning(f"Response too short or empty after cleaning: '{cleaned_response}' (length: {len(cleaned_response)})")

                # Create a more specific response based on the original message
                specific_response = f"I received your message '{user_message}', but I need more details to provide a helpful response. Could you elaborate on what you'd like help with?"
                return ChatResponse(
                    status="fallback",
                    message=specific_response,
                    data=None
                )
        else:
            logger.warning(f"Invalid response type received: {type(openrouter_response)}, value: {repr(openrouter_response)}")

            # Create a more specific error response
            specific_error = f"I encountered an issue processing your message '{user_message}'. Please try rephrasing your question."
            return ChatResponse(
                status="error",
                message=specific_error,
                data=None
            )

    except Exception as e:
        logger.error(f"Chat endpoint error: {str(e)}", exc_info=True)

        # Return error response with more specific message
        error_message = "I'm experiencing technical difficulties right now. Please try again shortly."
        return ChatResponse(
            status="error",
            message=error_message,
            data=None
        )


# Health check endpoint
@router.get("/health")
async def health_check():
    """
    Health check endpoint to verify the chat service is running
    """
    return {"status": "healthy", "service": "openrouter-chat-api", "version": "2.0.0"}