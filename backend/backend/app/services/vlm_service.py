"""
Media processing service using Google Gemini Files API.

Supports video, image, audio, and text creatives. All modalities are
decomposed into a plain-text brief stored as vlm_generated_context.
"""
import os
import time
import logging
import tempfile
from typing import Optional, Tuple
from google import genai
from app.config import get_settings
from app.media_types import prompt_for_subtype

settings = get_settings()
logger = logging.getLogger(__name__)

_client = None
_key_index = 0


def get_client():
    """Get or create Gemini client with optional key rotation."""
    global _client, _key_index

    _client = None

    key_list = []
    if getattr(settings, "gemini_api_keys", None):
        key_list = [k.strip() for k in settings.gemini_api_keys.split(",") if k.strip()]

    if len(key_list) > 1:
        current_key = key_list[_key_index % len(key_list)]
        _key_index += 1
        _client = genai.Client(api_key=current_key)
    else:
        _client = genai.Client(api_key=settings.gemini_api_key)

    return _client


def _resolve_media_path(media_path: str) -> Tuple[str, bool]:
    """
    If media_path is an HF/URL, download to a local temp file.

    Returns:
        (local_path, is_temp)
    """
    media_path = media_path.strip()

    if not media_path.startswith("http://") and not media_path.startswith("https://"):
        return media_path, False

    logger.info(f"Downloading media from URL: {media_path}")
    import requests

    headers = {}
    if settings.hf_access_token:
        headers["Authorization"] = f"Bearer {settings.hf_access_token}"

    resp = requests.get(media_path, headers=headers, timeout=300, stream=True)
    resp.raise_for_status()

    ext = os.path.splitext(media_path.split("?")[0])[1] or ".bin"

    tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
    try:
        for chunk in resp.iter_content(chunk_size=4 * 1024 * 1024):
            if chunk:
                tmp.write(chunk)
        tmp.flush()
        tmp_path = tmp.name
    finally:
        tmp.close()

    logger.info(f"Downloaded media to temp file: {tmp_path}")
    return tmp_path, True


def get_video_duration_cv2(video_path: str) -> int:
    """Get video duration in seconds using OpenCV."""
    try:
        import cv2
        video = cv2.VideoCapture(video_path)
        fps = video.get(cv2.CAP_PROP_FPS)
        frame_count = video.get(cv2.CAP_PROP_FRAME_COUNT)
        video.release()

        if fps > 0:
            return int(frame_count / fps)
    except Exception as e:
        logger.warning(f"Could not get video duration: {e}")
    return 0


def extract_text_from_file(local_path: str) -> str:
    """Extract plain text from txt/html/pdf/docx. Returns empty string on failure."""
    ext = os.path.splitext(local_path)[1].lower()

    try:
        if ext in {".txt", ".html", ".htm"}:
            with open(local_path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
            if ext in {".html", ".htm"}:
                import re
                text = re.sub(r"(?is)<script.*?>.*?</script>", " ", text)
                text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
                text = re.sub(r"(?s)<[^>]+>", " ", text)
                text = re.sub(r"\s+", " ", text).strip()
            return text.strip()

        if ext == ".docx":
            try:
                from docx import Document
                doc = Document(local_path)
                return "\n".join(p.text for p in doc.paragraphs if p.text.strip()).strip()
            except ImportError:
                logger.warning("python-docx not installed; cannot extract .docx")
                return ""

        if ext == ".pdf":
            try:
                from pypdf import PdfReader
                reader = PdfReader(local_path)
                parts = []
                for page in reader.pages:
                    page_text = page.extract_text() or ""
                    if page_text.strip():
                        parts.append(page_text)
                return "\n\n".join(parts).strip()
            except ImportError:
                logger.warning("pypdf not installed; cannot extract .pdf text")
                return ""
            except Exception as e:
                logger.warning(f"PDF text extraction failed: {e}")
                return ""
    except Exception as e:
        logger.warning(f"Text extraction failed for {local_path}: {e}")
        return ""

    return ""


def normalize_pasted_text(text: str, subtype: str) -> str:
    """Light normalization for pasted text creatives (no Gemini)."""
    cleaned = (text or "").strip()
    if not cleaned:
        return ""
    label = {
        "email_marketing": "EMAIL MARKETING COPY",
        "blog_article": "BLOG / ARTICLE COPY",
    }.get(subtype, "TEXT CREATIVE")
    return f"{label}\n\n{cleaned}"


def analyze_media_with_gemini(local_path: str, subtype: str) -> str:
    """Upload a local media file to Gemini and run the subtype prompt."""
    try:
        client = get_client()
        prompt = prompt_for_subtype(subtype)

        logger.info(f"Uploading media to Gemini: {local_path}")
        uploaded_file = client.files.upload(file=local_path)
        logger.info(f"Uploaded file: {uploaded_file.name}")

        max_wait = 120
        wait_time = 0
        while getattr(uploaded_file, "state", None) == "PROCESSING":
            if wait_time >= max_wait:
                logger.error("Media processing timeout")
                return "Media processing timeout. Please try a smaller file."
            logger.info(f"Waiting for media processing... ({wait_time}s)")
            time.sleep(10)
            wait_time += 10
            uploaded_file = client.files.get(name=uploaded_file.name)

        if getattr(uploaded_file, "state", None) == "FAILED":
            logger.error("Media processing failed on Gemini side")
            return "Media processing failed. Please try a different file format."

        logger.info("Media ready, analyzing content...")
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-preview",
            contents=[uploaded_file, prompt],
        )

        try:
            client.files.delete(name=uploaded_file.name)
            logger.info("Cleaned up uploaded Gemini file")
        except Exception:
            pass

        if response.text:
            logger.info(f"Generated analysis: {len(response.text)} characters")
            return response.text
        return "No analysis could be generated for this media."

    except Exception as e:
        logger.error(f"Gemini media analysis failed: {e}")
        return f"Media analysis failed: {str(e)}"


def analyze_video_with_gemini(video_path: str) -> str:
    """Backward-compatible wrapper for video analysis."""
    local_path = None
    is_temp = False
    try:
        local_path, is_temp = _resolve_media_path(video_path)
        return analyze_media_with_gemini(local_path, "video_ad")
    finally:
        if is_temp and local_path and os.path.exists(local_path):
            os.remove(local_path)
            logger.info(f"Removed temp media file: {local_path}")


def process_video(video_path: str) -> Tuple[str, int]:
    """Backward-compatible video pipeline."""
    return process_media(
        media_path=video_path,
        modality="video",
        subtype="video_ad",
    )


def process_media(
    media_path: Optional[str] = None,
    modality: str = "video",
    subtype: str = "video_ad",
    text_content: Optional[str] = None,
) -> Tuple[str, int]:
    """
    Full media processing pipeline.

    Returns:
        (context_text, duration_seconds)
    """
    duration = 0

    # Paste-only text: no Gemini
    if modality == "text" and text_content and not media_path:
        logger.info(f"Normalizing pasted text for subtype={subtype}")
        return normalize_pasted_text(text_content, subtype), 0

    if not media_path:
        raise ValueError("media_path is required unless providing pasted text_content")

    logger.info(f"Processing media: path={media_path} modality={modality} subtype={subtype}")
    local_path, is_temp = _resolve_media_path(media_path)

    try:
        if modality == "video":
            duration = get_video_duration_cv2(local_path)

        if modality == "text":
            extracted = extract_text_from_file(local_path)
            if extracted.strip():
                # Prefer extracted text; lightly wrap with subtype label
                return normalize_pasted_text(extracted, subtype), 0
            # Scanned PDF / empty extract → fall back to Gemini vision
            logger.info("Text extraction empty; falling back to Gemini")
            descriptions = analyze_media_with_gemini(local_path, subtype)
            return descriptions, 0

        descriptions = analyze_media_with_gemini(local_path, subtype)
        return descriptions, duration
    finally:
        if is_temp and os.path.exists(local_path):
            os.remove(local_path)
            logger.info(f"Removed temp media file: {local_path}")
