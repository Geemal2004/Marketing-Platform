"""
Hugging Face Storage Service
Uploads media files to a Hugging Face repo and returns a public URL.

Repo/token are resolved at call time from (in order):
1. process env HF_VIDEO_REPO_ID / HF_ACCESS_TOKEN
2. backend/.env (explicit file read)
3. app Settings
"""
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

MODALITY_PREFIXES = {
    "video": "videos",
    "image": "images",
    "audio": "audio",
    "text": "text",
}

# Locked / legacy account — never upload project media here
BLOCKED_REPO_IDS = {
    "vish85521/videos",
    "vish85521/Videos",
}


def _backend_env_path() -> Path:
    """Absolute path to backend/.env (canonical)."""
    # hf_storage.py -> services -> app -> backend package -> backend root
    return Path(__file__).resolve().parents[3] / ".env"


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    try:
        text = path.read_text(encoding="utf-8-sig")  # utf-8-sig strips BOM
    except OSError as e:
        logger.warning("Could not read %s: %s", path, e)
        return values

    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key:
            values[key] = val
    return values


def _resolve_hf_config() -> tuple[str, str, str, str]:
    """
    Returns (token, repo_id, repo_type, path_prefix).
    Prefers live env + backend/.env over cached Settings defaults.
    """
    file_vals = _parse_env_file(_backend_env_path())

    def pick(env_key: str, settings_attr: str, default: str = "") -> str:
        if os.environ.get(env_key, "").strip():
            return os.environ[env_key].strip()
        if file_vals.get(env_key, "").strip():
            return file_vals[env_key].strip()
        try:
            from app.config import get_settings
            settings = get_settings()
            val = getattr(settings, settings_attr, None)
            if val is not None and str(val).strip():
                return str(val).strip()
        except Exception:
            pass
        return default

    token = pick("HF_ACCESS_TOKEN", "hf_access_token", "")
    repo_id = pick("HF_VIDEO_REPO_ID", "hf_video_repo_id", "Geemal204/Marketing")
    repo_type = pick("HF_VIDEO_REPO_TYPE", "hf_video_repo_type", "dataset") or "dataset"
    path_prefix = pick("HF_VIDEO_PATH_PREFIX", "hf_video_path_prefix", "videos") or "videos"
    return token, repo_id, repo_type, path_prefix


def _get_settings():
    from app.config import get_settings
    return get_settings()


def _clean_token(token: str) -> str:
    """Normalize secrets loaded from env/space settings (remove trailing newlines/spaces)."""
    return (token or "").strip()


def _clean_path_prefix(prefix: str) -> str:
    """Normalize optional repo path prefix and handle legacy placeholder value."""
    cleaned = (prefix or "").strip().strip("/")
    if cleaned.upper() == "HF_VIDEO_PATH_PREFIX":
        return "videos"
    return cleaned


def _build_public_url(repo_id: str, repo_type: str, remote_path: str) -> str:
    repo_type = (repo_type or "dataset").lower()
    if repo_type == "dataset":
        return f"https://huggingface.co/datasets/{repo_id}/resolve/main/{remote_path}"
    if repo_type == "space":
        return f"https://huggingface.co/spaces/{repo_id}/resolve/main/{remote_path}"
    return f"https://huggingface.co/{repo_id}/resolve/main/{remote_path}"


def _extract_remote_path_from_url(media_url: str, repo_id: str, repo_type: str) -> str | None:
    patterns = []
    repo_type = (repo_type or "dataset").lower()

    if repo_type == "dataset":
        patterns.append(f"/datasets/{repo_id}/resolve/main/")
    elif repo_type == "space":
        patterns.append(f"/spaces/{repo_id}/resolve/main/")
    else:
        patterns.append(f"/{repo_id}/resolve/main/")

    # Backward compatibility for previously stored bucket URLs.
    patterns.append(f"/buckets/{repo_id}/resolve/")

    for marker in patterns:
        if marker in media_url:
            return media_url.split(marker, 1)[1]
    return None


def _ensure_repo_exists(api, repo_id: str, repo_type: str, token: str) -> None:
    """Ensure target repo exists; create it if missing."""
    from huggingface_hub.utils import RepositoryNotFoundError

    try:
        api.repo_info(repo_id=repo_id, repo_type=repo_type, token=token)
    except RepositoryNotFoundError:
        logger.warning(
            "HF repo not found (%s/%s). Creating it automatically.",
            repo_type,
            repo_id,
        )
        api.create_repo(
            repo_id=repo_id,
            repo_type=repo_type,
            token=token,
            private=False,
            exist_ok=True,
        )


def upload_media_to_hf(local_path: str, filename: str, modality: str = "video") -> str:
    """
    Upload a local media file to the HuggingFace repo.

    Args:
        local_path: Absolute path to the local file.
        filename: Desired filename in the repo (e.g. "uuid.mp4").
        modality: video | image | audio | text — selects path prefix.

    Returns:
        Public download URL for the uploaded file.
    """
    from huggingface_hub import HfApi

    token, repo_id, repo_type, configured_prefix = _resolve_hf_config()
    token = _clean_token(token)

    if not token:
        raise ValueError(
            "HF_ACCESS_TOKEN is not configured. "
            "Please set it in backend/.env and restart the API."
        )

    if not repo_id:
        raise ValueError("HF_VIDEO_REPO_ID is not configured.")

    if repo_id.lower() in {r.lower() for r in BLOCKED_REPO_IDS} or "vish85521" in repo_id.lower():
        raise ValueError(
            f"Refusing to upload to locked/legacy HF repo '{repo_id}'. "
            f"Set HF_VIDEO_REPO_ID=Geemal204/Marketing in backend/.env and restart "
            f"all Backend terminals (kill anything on port 8001). "
            f"env_file={_backend_env_path()}"
        )

    # Prefer modality-specific prefix; fall back to configured video prefix for video
    if modality == "video":
        path_prefix = _clean_path_prefix(configured_prefix) or "videos"
    else:
        path_prefix = MODALITY_PREFIXES.get(modality, modality)

    remote_path = f"{path_prefix}/{filename}" if path_prefix else filename

    logger.info(
        "HF upload: repo=%s type=%s path=%s env_file=%s",
        repo_id,
        repo_type,
        remote_path,
        _backend_env_path(),
    )

    api = HfApi(token=token)
    _ensure_repo_exists(api=api, repo_id=repo_id, repo_type=repo_type, token=token)
    api.upload_file(
        path_or_fileobj=local_path,
        path_in_repo=remote_path,
        repo_id=repo_id,
        repo_type=repo_type,
        token=token,
    )

    url = _build_public_url(repo_id=repo_id, repo_type=repo_type, remote_path=remote_path)

    logger.info("Upload complete. Public URL: %s", url)
    return url


def delete_media_from_hf(media_url: str) -> None:
    """
    Delete a media file from the HuggingFace repo given its public URL.
    Silently ignores failures (e.g. file not found).
    """
    from huggingface_hub import HfApi

    token, repo_id, repo_type, _ = _resolve_hf_config()
    token = _clean_token(token)

    if not token:
        logger.warning("HF_ACCESS_TOKEN not configured, skipping HF delete.")
        return

    # Prefer repo id parsed from the URL itself (may be legacy assets)
    remote_path = _extract_remote_path_from_url(media_url, repo_id=repo_id, repo_type=repo_type)
    if not remote_path:
        # Try extracting with any dataset URL shape
        marker = "/resolve/main/"
        if marker in media_url:
            remote_path = media_url.split(marker, 1)[1]
            # Derive repo from URL if present
            if "/datasets/" in media_url:
                try:
                    after = media_url.split("/datasets/", 1)[1]
                    repo_id = after.split("/resolve/", 1)[0]
                except Exception:
                    pass
        else:
            logger.warning(f"Cannot parse HF URL for deletion: {media_url}")
            return

    try:
        api = HfApi(token=token)
        api.delete_file(
            path_in_repo=remote_path,
            repo_id=repo_id,
            repo_type=repo_type,
            token=token,
        )
        logger.info(f"Deleted HF file: {repo_id}/{remote_path}")
    except Exception as e:
        logger.warning(f"Failed to delete HF file {remote_path}: {e}")


# Backward-compatible aliases
def upload_video_to_hf(local_path: str, filename: str) -> str:
    return upload_media_to_hf(local_path, filename, modality="video")


def delete_video_from_hf(video_url: str) -> None:
    return delete_media_from_hf(video_url)
