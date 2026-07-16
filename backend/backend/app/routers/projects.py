"""
Project management routes - create, list, and get projects
"""
import os
import uuid
import tempfile
import json
from fastapi import APIRouter, Depends, HTTPException, UploadFile, Request, status
from sqlalchemy.orm import Session
from typing import List, Optional, Any
from app.database import get_db
from app.models import User, Project
from app.schemas import ProjectResponse, ProjectListResponse, ProjectContextUpdate
from app.dependencies import get_current_user
from app.config import get_settings
from app.services.hf_storage import upload_media_to_hf, delete_media_from_hf
from app.media_types import (
    MEDIA_SUBTYPES,
    allowed_extensions_for_subtype,
    max_size_for_subtype,
    modality_for_subtype,
    resolve_modality_from_extension,
)

settings = get_settings()
router = APIRouter(prefix="/projects", tags=["Projects"])


def _save_upload_to_temp(upload: UploadFile, file_ext: str, max_size: int) -> str:
    """Stream upload to a temp file; raise HTTPException on size exceed."""
    with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as tmp:
        tmp_path = tmp.name

    try:
        with open(tmp_path, "wb") as f:
            total_size = 0
            while chunk := upload.file.read(1024 * 1024):
                total_size += len(chunk)
                if total_size > max_size:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"File too large. Maximum size: {max_size // (1024 * 1024)}MB",
                    )
                f.write(chunk)
        return tmp_path
    except HTTPException:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def _is_real_upload(upload: Any) -> bool:
    """True if form value is a non-empty file upload."""
    if upload is None:
        return False
    filename = getattr(upload, "filename", None)
    return bool(filename and str(filename).strip())


def _form_str(form: Any, key: str, default: Optional[str] = None) -> Optional[str]:
    value = form.get(key)
    if value is None:
        return default
    if hasattr(value, "filename"):
        # Accidentally got a file for a text field
        return default
    text = str(value).strip()
    return text if text else default


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new project with multimedia creative input.

    Multipart fields:
    - title (required)
    - media_subtype (default video_ad)
    - media or video (file)
    - text_content (paste for email/blog)
    - demographic_filter (optional JSON string)
    """
    form = await request.form()

    title = _form_str(form, "title")
    if not title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="title is required",
        )

    media_subtype = _form_str(form, "media_subtype", "video_ad") or "video_ad"
    demographic_filter = _form_str(form, "demographic_filter")
    pasted = _form_str(form, "text_content")

    media_field = form.get("media")
    video_field = form.get("video")
    upload = media_field if _is_real_upload(media_field) else (
        video_field if _is_real_upload(video_field) else None
    )

    if media_subtype not in MEDIA_SUBTYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid media_subtype. Allowed: {', '.join(MEDIA_SUBTYPES.keys())}",
        )

    modality = modality_for_subtype(media_subtype)

    if modality == "text":
        if not upload and not pasted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="For text creatives, provide text_content and/or a text file upload.",
            )
    else:
        if not upload:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A media file is required for this creative type.",
            )
        if pasted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="text_content is only allowed for email/blog text subtypes.",
            )

    # Prefer pasted text when both are provided for text subtypes
    use_paste_only = modality == "text" and bool(pasted)

    media_url = None
    actual_modality = modality
    tmp_path = None

    try:
        if upload and not use_paste_only:
            filename_src = upload.filename or ""
            file_ext = os.path.splitext(filename_src)[1].lower()
            allowed = allowed_extensions_for_subtype(media_subtype)
            if file_ext not in allowed:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid file type for {media_subtype}. Allowed: {', '.join(sorted(allowed))}",
                )

            actual_modality = resolve_modality_from_extension(media_subtype, file_ext)
            max_size = max_size_for_subtype(media_subtype)
            tmp_path = _save_upload_to_temp(upload, file_ext, max_size)

            file_id = str(uuid.uuid4())
            filename = f"{file_id}{file_ext}"
            try:
                media_url = upload_media_to_hf(tmp_path, filename, modality=actual_modality)
            except Exception as upload_err:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to upload media to storage: {str(upload_err)}",
                )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process file: {str(e)}",
        )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

    demo_filter = None
    if demographic_filter:
        try:
            demo_filter = json.loads(demographic_filter)
        except json.JSONDecodeError:
            pass

    # Paste-only text: ready immediately without Celery
    if use_paste_only:
        from app.services.vlm_service import normalize_pasted_text

        project = Project(
            user_id=current_user.id,
            title=title,
            video_path=None,
            media_subtype=media_subtype,
            media_modality="text",
            demographic_filter=demo_filter,
            vlm_generated_context=normalize_pasted_text(pasted, media_subtype),
            status="READY",
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        return project

    project = Project(
        user_id=current_user.id,
        title=title,
        video_path=media_url,
        media_subtype=media_subtype,
        media_modality=actual_modality,
        demographic_filter=demo_filter,
        status="PENDING",
    )

    db.add(project)
    db.commit()
    db.refresh(project)

    from app.tasks import process_media_task
    process_media_task.delay(str(project.id))

    return project


@router.get("", response_model=List[ProjectListResponse])
def list_projects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all projects for the current user."""
    projects = (
        db.query(Project)
        .filter(Project.user_id == current_user.id)
        .order_by(Project.created_at.desc())
        .all()
    )
    return projects


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific project by ID."""
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.user_id == current_user.id)
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a project and its stored media file."""
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.user_id == current_user.id)
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if project.video_path and project.video_path.startswith("https://"):
        delete_media_from_hf(project.video_path)
    elif project.video_path and os.path.exists(project.video_path):
        os.remove(project.video_path)

    db.delete(project)
    db.commit()


@router.patch("/{project_id}/context", response_model=ProjectResponse)
def update_project_context(
    project_id: str,
    context_update: ProjectContextUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update the generated context brief for a project."""
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.user_id == current_user.id)
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    project.vlm_generated_context = context_update.vlm_generated_context
    db.commit()
    db.refresh(project)

    return project
