
from __future__ import annotations
import os
import re
import subprocess
import time
from collections import Counter

from celery import Celery
from sqlalchemy.orm import Session
import database as db
from sqlalchemy import delete, select

STORAGE_DIR = os.getenv("STORAGE_DIR", "/app/storage")
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "small")

celery_app = Celery(
    "worker",
    broker=os.getenv("REDIS_URL", "redis://redis:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://redis:6379/0")
)

@celery_app.task(name="process_audio_task")
def process_audio_task(task_id: str):
    os.makedirs(STORAGE_DIR, exist_ok=True)
    engine = db.engine
    with Session(engine) as session:
        task = session.query(db.MediaTask).filter(db.MediaTask.id == task_id).first()
        if not task:
            return

        task.status = "PROCESSING"
        task.error_text = None
        session.commit()

        try:
            media_path = _ensure_media_file(session, task)
            transcript = _transcribe(media_path)
            summary = _summarize_extractive(transcript)

            task.transcript_text = transcript
            task.summary_text = summary
            task.result_text = summary  # keep legacy field populated

            _rebuild_chunks(session, task.id, transcript)

            task.status = "COMPLETED"
        except Exception as e:
            task.status = "FAILED"
            task.error_text = str(e)

        session.commit()


def _ensure_media_file(session: Session, task: db.MediaTask) -> str:
    if task.storage_path:
        return task.storage_path
    if task.source_type == "youtube" and task.source_url:
        out_path = os.path.join(STORAGE_DIR, f"{task.id}__youtube.mp3")
        _download_youtube_audio(task.source_url, out_path)
        task.storage_path = out_path
        task.filename = os.path.basename(out_path)
        session.commit()
        return out_path
    raise RuntimeError("No media source available (missing upload file or youtube url)")


def _download_youtube_audio(url: str, out_path: str) -> None:
    # yt-dlp + ffmpeg inside container
    tmp_tpl = out_path.rsplit(".", 1)[0] + ".%(ext)s"
    cmd = [
        "yt-dlp",
        "--no-playlist",
        "-x",
        "--audio-format",
        "mp3",
        "-o",
        tmp_tpl,
        url,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"yt-dlp failed: {proc.stderr.strip() or proc.stdout.strip()}")

    # yt-dlp will produce exactly one file using the template; normalize to out_path
    base = out_path.rsplit(".", 1)[0]
    for name in os.listdir(os.path.dirname(out_path) or "."):
        if name.startswith(os.path.basename(base)) and name.endswith(".mp3"):
            produced = os.path.join(os.path.dirname(out_path), name)
            if produced != out_path:
                os.replace(produced, out_path)
            return
    if not os.path.exists(out_path):
        raise RuntimeError("yt-dlp finished but output file not found")


def _transcribe(media_path: str) -> str:
    ext = os.path.splitext(media_path.lower())[1]
    if ext == ".pdf":
        return _extract_pdf_text(media_path)

    # audio/video → local Whisper (free)
    return _transcribe_with_faster_whisper(media_path)


def _extract_pdf_text(path: str) -> str:
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception as e:
        raise RuntimeError(f"Missing dependency for PDF extraction (pypdf). {e}")

    reader = PdfReader(path)
    parts: list[str] = []
    for i, page in enumerate(reader.pages):
        txt = page.extract_text() or ""
        txt = txt.strip()
        if txt:
            parts.append(f"[Page {i+1}]\n{txt}")
    out = "\n\n".join(parts).strip()
    if not out:
        raise RuntimeError("PDF text extraction returned empty text (scanned PDF?).")
    return out


def _transcribe_with_faster_whisper(media_path: str) -> str:
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "Missing dependency for local transcription (faster-whisper). "
            f"{e}"
        )

    model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
    segments, info = model.transcribe(media_path, vad_filter=True)
    lines: list[str] = []
    for seg in segments:
        start = int(seg.start)
        mm = start // 60
        ss = start % 60
        lines.append(f"[{mm:02d}:{ss:02d}] {seg.text.strip()}")
    text = "\n".join(lines).strip()
    if not text:
        raise RuntimeError(f"Transcription produced empty text (lang={getattr(info,'language',None)})")
    return text


_STOPWORDS = {
    # minimal FR/DE/EN stopwords to keep scoring sane
    "und","oder","der","die","das","ein","eine","ist","sind","war","waren","mit","von","für","auf","im","in","am","an","zu","zum","zur",
    "et","ou","le","la","les","un","une","des","est","sont","avec","pour","dans","sur","au","aux","de","du","ce","cet","cette",
    "and","or","the","a","an","is","are","was","were","with","for","in","on","to","of","from","this","that","these","those",
}


def _split_sentences(text: str) -> list[str]:
    t = re.sub(r"\s+", " ", text.strip())
    if not t:
        return []
    # keep bracket timestamps/pages as sentence boundaries too
    rough = re.split(r"(?<=[\.\!\?])\s+|\s+(?=\[Page\s+\d+\])", t)
    return [s.strip() for s in rough if len(s.strip()) >= 25]


def _summarize_extractive(text: str, max_sentences: int = 8) -> str:
    sentences = _split_sentences(text)
    if not sentences:
        return text[:1200]

    words = re.findall(r"[a-zA-Z0-9äöüÄÖÜß]+", text.lower())
    words = [w for w in words if len(w) >= 3 and w not in _STOPWORDS]
    freq = Counter(words)

    def score_sentence(s: str) -> float:
        ws = re.findall(r"[a-zA-Z0-9äöüÄÖÜß]+", s.lower())
        ws = [w for w in ws if len(w) >= 3 and w not in _STOPWORDS]
        if not ws:
            return 0.0
        # average word frequency with a small length penalty
        base = sum(freq.get(w, 0) for w in ws) / (len(ws) ** 0.5)
        return base

    scored = [(i, s, score_sentence(s)) for i, s in enumerate(sentences)]
    scored.sort(key=lambda x: x[2], reverse=True)
    top = sorted(scored[:max_sentences], key=lambda x: x[0])

    bullets = "\n".join([f"- {s}" for _, s, _ in top])
    return f"Résumé (extractif):\n{bullets}"


def _chunk_text(text: str, max_chars: int = 900, overlap: int = 120) -> list[str]:
    cleaned = re.sub(r"\n{3,}", "\n\n", text.strip())
    if not cleaned:
        return []
    chunks: list[str] = []
    i = 0
    while i < len(cleaned):
        end = min(len(cleaned), i + max_chars)
        chunk = cleaned[i:end].strip()
        if chunk:
            chunks.append(chunk)
        i = end - overlap
        if i < 0:
            i = 0
        if end >= len(cleaned):
            break
    return chunks


def _rebuild_chunks(session: Session, task_id: str, transcript: str) -> None:
    session.execute(delete(db.MediaChunk).where(db.MediaChunk.task_id == task_id))
    session.commit()

    chunks = _chunk_text(transcript)
    for idx, text in enumerate(chunks):
        session.add(db.MediaChunk(task_id=task_id, idx=idx, text=text, embedding_json=None))
    session.commit()


def _tokenize(s: str) -> set[str]:
    return {t for t in re.findall(r"[a-zA-Z0-9äöüÄÖÜß]+", s.lower()) if len(t) >= 2}


def _score(question: str, chunk: str) -> float:
    q = _tokenize(question)
    c = _tokenize(chunk)
    if not q or not c:
        return 0.0
    return len(q & c) / (len(q) ** 0.5 * len(c) ** 0.5)


def answer_question(session: Session, task_id: str, question: str, top_k: int = 5) -> dict:
    rows = session.execute(
        select(db.MediaChunk).where(db.MediaChunk.task_id == task_id).order_by(db.MediaChunk.idx.asc())
    ).scalars().all()

    scored = [(c, _score(question, c.text)) for c in rows]
    scored.sort(key=lambda x: x[1], reverse=True)
    picked = [c for (c, s) in scored[:top_k] if s > 0]

    context = "\n\n---\n\n".join([c.text for c in picked]) if picked else ""
    # Free mode: return context + short extractive answer
    answer = _summarize_extractive(context, max_sentences=5) if context else "Aucun contexte trouvé pour cette question."
    return {
        "task_id": task_id,
        "question": question,
        "answer": answer,
        "chunks": [{"idx": c.idx, "text": c.text} for c in picked],
    }
