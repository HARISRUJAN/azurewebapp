from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.schemas import DocumentIngest, DocumentResponse
from app.services.ingestion_service import ingestion_service
from app.core.security import get_current_active_admin

router = APIRouter()


@router.post("/ingest", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def ingest_document(
    document: DocumentIngest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
):
    """Ingest a document into the system"""
    try:
        db_document = ingestion_service.ingest_document(db, document)
        return db_document
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error ingesting document: {str(e)}"
        )

