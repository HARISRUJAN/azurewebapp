from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.schemas import RAGQuery, RAGResponse, DocumentChunk
from app.services.rag_service import rag_service
from app.utils.string_utils import escape_for_fstring

router = APIRouter()


@router.post("/query", response_model=RAGResponse)
async def query_rag(
    query: RAGQuery,
    db: Session = Depends(get_db)
):
    """Query the RAG system with a question"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Escape question to prevent f-string evaluation errors
        question_safe = escape_for_fstring(query.question[:100] if len(query.question) > 100 else query.question)
        logger.info(f"Processing RAG query: {question_safe}...")
        
        # Retrieve relevant chunks with error handling
        try:
            chunks = rag_service.retrieve_relevant_chunks(query.question, top_k=query.top_k)
        except Exception as chunk_error:
            logger.error(f"Error retrieving chunks: {chunk_error}")
            # Check if it's a Qdrant connection error
            error_msg = str(chunk_error).lower()
            if "qdrant" in error_msg or "connection" in error_msg:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Vector database is currently unavailable. Please try again later."
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error retrieving information: {str(chunk_error)}"
                )
        
        if not chunks:
            logger.warning(f"No relevant chunks found for query: {question_safe}...")
            return RAGResponse(
                answer="I couldn't find relevant information to answer your question. This could mean:\n1. No documents have been ingested yet - please ingest some documents first.\n2. The question doesn't match any content in the knowledge base - try rephrasing or asking about a different topic.",
                citations=[]
            )
        
        logger.info(f"Retrieved {len(chunks)} relevant chunks, generating answer...")
        
        # Initialize answer variable
        answer = None
        
        # Generate answer with error handling
        try:
            answer = rag_service.generate_answer(query.question, chunks)
            
            # Additional safety check: ensure answer doesn't contain code errors
            if answer and ("current_date" in answer.lower() or "is not defined" in answer.lower()):
                answer_safe = escape_for_fstring(answer[:200])
                logger.warning(f"Answer contains code-like content, attempting to clean: {answer_safe}...")
                # Remove any lines containing code-like patterns
                lines = answer.split('\n')
                cleaned = []
                for line in lines:
                    if not any(pattern in line.lower() for pattern in ["current_date", "is not defined", "nameerror", "def ", "import ", "datetime"]):
                        cleaned.append(line)
                answer = '\n'.join(cleaned).strip()
                if not answer:
                    answer = "I apologize, but I encountered an issue generating a proper response. Please try rephrasing your question."
        except ValueError as ve:
            # Handle value errors from LLM response generation (including API errors)
            logger.error(f"ValueError during answer generation: {ve}")
            error_msg = str(ve)
            # Check if it's an API configuration error
            if "api key" in error_msg.lower() or "groq" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="AI service is currently unavailable. Please check the API configuration."
                )
            # Check if it's a code generation error
            elif "code errors" in error_msg.lower() or "invalid response" in error_msg.lower():
                answer = "I apologize, but I encountered an issue generating a proper response. The system attempted to generate code instead of a text answer. Please try rephrasing your question."
            else:
                # Re-raise other ValueErrors to be caught by outer exception handler
                raise
        
        # Ensure answer is set before formatting citations
        if not answer or not answer.strip():
            logger.warning("Answer is empty or None, using fallback message")
            answer = "I apologize, but I encountered an issue generating a proper response. Please try again or rephrasing your question."
        
        # Format citations with error handling
        citations = []
        try:
            for chunk in chunks:
                try:
                    citations.append(DocumentChunk(
                        content=chunk.get("content", ""),
                        document_title=chunk.get("document_title", ""),
                        document_source=chunk.get("document_source", ""),
                        document_url=chunk.get("document_url"),
                        chunk_index=chunk.get("chunk_index", 0),
                        entities=chunk.get("entities", []),  # Include extracted entities
                        metadata=chunk.get("metadata", {})
                    ))
                except Exception as citation_error:
                    logger.warning(f"Error formatting citation: {citation_error}, skipping chunk")
                    continue
        except Exception as citations_error:
            logger.error(f"Error formatting citations: {citations_error}")
            citations = []  # Return empty citations if formatting fails
        
        logger.info(f"Successfully generated answer for query (answer length: {len(answer)}, citations: {len(citations)})")
        return RAGResponse(answer=answer, citations=citations)
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 503 Service Unavailable) as-is
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.exception(f"Error processing RAG query: {str(e)}\n{error_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing query: {str(e)}"
        )

