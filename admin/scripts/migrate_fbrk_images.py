#!/usr/bin/env python3
"""Download legacy fbrk.kz article images and rewrite articles to local uploads."""
from __future__ import annotations

import argparse
import json
import logging
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse, urlsplit, urlunsplit
from urllib.request import Request, build_opener

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.admin_platform.audit import record_audit
from app.admin_platform.uploads import ALLOWED_IMAGE_MIME, store_optimized_image, validate_image_upload
from app.config import settings
from app.image_migration import (
    MigratedImage,
    collect_external_image_urls,
    normalize_fbrk_source_image_url,
    rewrite_article_images,
)
from app.publish import regenerate_data_js


LOG = logging.getLogger("migrate_fbrk_images")
UA = "Mozilla/5.0 (compatible; FBRK-image-migrator/1.0; +https://fbrk.qdev.run)"
STATE_VERSION = 1
DEFAULT_STATE_FILE = Path(__file__).resolve().parents[1] / ".cache" / "fbrk-image-migration-state.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Write optimized uploads and update article rows.")
    parser.add_argument("--slug", help="Only process a single article slug.")
    parser.add_argument("--limit", type=int, default=0, help="Limit the number of candidate articles.")
    parser.add_argument("--throttle", type=float, default=0.05, help="Seconds to sleep between source downloads.")
    parser.add_argument("--state-file", type=Path, default=DEFAULT_STATE_FILE, help="Persistent cache of migrated source URLs.")
    parser.add_argument("--no-backup", action="store_true", help="Skip DB backup before --apply.")
    parser.add_argument("--no-regen", action="store_true", help="Skip regenerate_data_js() after updates.")
    parser.add_argument("--force-redownload", action="store_true", help="Ignore cached migrated URLs and fetch again.")
    parser.add_argument("--debug", action="store_true")
    return parser.parse_args()


def configure_logging(debug: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": STATE_VERSION, "images": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return {"version": STATE_VERSION, "images": {}}
    if not isinstance(data, dict):
        return {"version": STATE_VERSION, "images": {}}
    images = data.get("images")
    if not isinstance(images, dict):
        images = {}
    return {"version": STATE_VERSION, "images": images}


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def backup_database(db_path: Path) -> Path:
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    backup_dir = db_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"{db_path.stem}-{timestamp}-pre-image-migration.db"
    src = sqlite3.connect(str(db_path))
    dst = sqlite3.connect(str(backup_path))
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    return backup_path


def open_db() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def fetch_candidate_rows(conn: sqlite3.Connection, slug: str | None, limit: int) -> list[sqlite3.Row]:
    where = """
        WHERE (
               image LIKE '%fbrk.kz%'
            OR image LIKE '%/sites/default/files/%'
            OR body_json LIKE '%fbrk.kz%'
            OR body_json LIKE '%/sites/default/files/%'
            OR sections_json LIKE '%fbrk.kz%'
            OR sections_json LIKE '%/sites/default/files/%'
        )
    """
    args: list[Any] = []
    if slug:
        where += " AND slug = ?"
        args.append(slug)
    sql = f"""
        SELECT id, slug, title, image, body_json, sections_json
        FROM articles
        {where}
        ORDER BY date_iso DESC, id DESC
    """
    if limit > 0:
        sql += " LIMIT ?"
        args.append(limit)
    return list(conn.execute(sql, args))


def build_migrated_image(state_entry: dict[str, Any]) -> MigratedImage | None:
    source_url = str(state_entry.get("source_url") or "").strip()
    thumb_url = str(state_entry.get("thumb_url") or "").strip()
    full_url = str(state_entry.get("full_url") or "").strip()
    if not source_url or not thumb_url or not full_url:
        return None
    return MigratedImage(source_url=source_url, thumb_url=thumb_url, full_url=full_url)


def guess_content_type(url: str, declared: str | None) -> str:
    value = (declared or "").split(";", 1)[0].strip().lower()
    if value == "image/jpg":
        value = "image/jpeg"
    if value in ALLOWED_IMAGE_MIME:
        return value
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".png":
        return "image/png"
    if suffix == ".gif":
        return "image/gif"
    if suffix == ".webp":
        return "image/webp"
    return "image/jpeg"


def requestable_url(url: str) -> str:
    parts = urlsplit(url)
    path = quote(parts.path or "", safe="/%:@+~,.-")
    query = quote(parts.query or "", safe="=&%:@+~,.-")
    return urlunsplit((parts.scheme, parts.netloc, path, query, parts.fragment))


def migrate_source_image(
    opener,
    conn: sqlite3.Connection,
    state: dict[str, Any],
    source_url: str,
    *,
    force_redownload: bool,
) -> MigratedImage:
    cached = state["images"].get(source_url)
    if isinstance(cached, dict) and not force_redownload:
        migrated = build_migrated_image(cached)
        if migrated is not None:
            return migrated

    request = Request(requestable_url(source_url), headers={"User-Agent": UA})
    with opener.open(request, timeout=45) as response:
        raw = response.read()
        declared = guess_content_type(source_url, response.headers.get("content-type"))
    validation = validate_image_upload(raw, content_type=declared)
    if not validation.ok:
        raise RuntimeError(validation.error)

    stored = store_optimized_image(
        raw,
        uploads_dir=settings.uploads_dir,
        uploads_url_prefix=settings.uploads_url_prefix,
    )
    conn.execute(
        "INSERT INTO uploads (filename, url, size_bytes) VALUES (?, ?, ?)",
        (stored.basename, stored.thumb_url, stored.full_size_bytes),
    )
    record_audit(
        conn,
        user="image-migration",
        action="upload",
        entity="media",
        entity_id=stored.basename,
        details={"source_url": source_url, "mime": validation.detected_mime},
    )
    migrated = MigratedImage(
        source_url=source_url,
        thumb_url=stored.thumb_url,
        full_url=stored.full_url,
    )
    state["images"][source_url] = {
        "source_url": source_url,
        "thumb_url": stored.thumb_url,
        "full_url": stored.full_url,
        "filename": stored.basename,
        "stored_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }
    return migrated


def main() -> int:
    args = parse_args()
    configure_logging(args.debug)

    state = load_state(args.state_file)
    db_path = Path(settings.db_path)
    if args.apply and not args.no_backup:
        backup_path = backup_database(db_path)
        LOG.info("db backup created: %s", backup_path)

    opener = build_opener()
    conn = open_db()

    uploaded = 0
    failed = 0
    updated_articles = 0
    unchanged_articles = 0

    try:
        rows = fetch_candidate_rows(conn, args.slug, args.limit)
        unique_sources: set[str] = set()
        article_sources: dict[str, set[str]] = {}
        for row in rows:
            sources = collect_external_image_urls(row["image"], row["body_json"], row["sections_json"])
            if not sources:
                continue
            article_sources[str(row["id"])] = sources
            unique_sources.update(sources)

        cached_sources = {
            key for key, value in state["images"].items()
            if isinstance(value, dict) and build_migrated_image(value) is not None
        }
        pending_sources = unique_sources - cached_sources if not args.force_redownload else unique_sources
        LOG.info(
            "articles=%d with_external_images=%d unique_source_images=%d cached=%d pending=%d",
            len(rows),
            len(article_sources),
            len(unique_sources),
            len(unique_sources & cached_sources),
            len(pending_sources),
        )

        if not args.apply:
            sample = sorted(list(pending_sources))[:10]
            for item in sample:
                LOG.info("pending source: %s", item)
            print("STATUS=dry-run")
            return 0

        migrated_by_source: dict[str, MigratedImage] = {}
        for source_url, cached in state["images"].items():
            if isinstance(cached, dict):
                migrated = build_migrated_image(cached)
                if migrated is not None:
                    migrated_by_source[source_url] = migrated

        total_rows = len(rows)
        for index, row in enumerate(rows, 1):
            raw_sources = article_sources.get(str(row["id"]))
            if not raw_sources:
                if index % 100 == 0:
                    LOG.info("[%d/%d] no external refs yet updated=%d uploaded=%d failed=%d", index, total_rows, updated_articles, uploaded, failed)
                continue

            available_for_article = migrated_by_source
            for source_url in sorted(raw_sources):
                normalized = normalize_fbrk_source_image_url(source_url)
                if not normalized or normalized in available_for_article:
                    continue
                try:
                    migrated = migrate_source_image(
                        opener,
                        conn,
                        state,
                        normalized,
                        force_redownload=args.force_redownload,
                    )
                    available_for_article[normalized] = migrated
                    migrated_by_source[normalized] = migrated
                    uploaded += 1
                    conn.commit()
                    save_state(args.state_file, state)
                    if args.throttle > 0:
                        time.sleep(args.throttle)
                except Exception as exc:
                    failed += 1
                    LOG.exception("image migrate failed for %s: %s", normalized, exc)

            rewrite = rewrite_article_images(
                row["image"],
                row["body_json"],
                row["sections_json"],
                available_for_article,
            )
            if not rewrite.changed:
                unchanged_articles += 1
                if index % 25 == 0:
                    LOG.info("[%d/%d] unchanged=%d updated=%d uploaded=%d failed=%d", index, total_rows, unchanged_articles, updated_articles, uploaded, failed)
                continue

            if (
                rewrite.image == (row["image"] or "")
                and rewrite.body_json == (row["body_json"] or "")
                and rewrite.sections_json == (row["sections_json"] or "")
            ):
                unchanged_articles += 1
                if index % 25 == 0:
                    LOG.info("[%d/%d] unchanged=%d updated=%d uploaded=%d failed=%d", index, total_rows, unchanged_articles, updated_articles, uploaded, failed)
                continue

            conn.execute(
                """
                UPDATE articles
                   SET image = ?,
                       body_json = ?,
                       sections_json = ?,
                       updated_at = CURRENT_TIMESTAMP
                 WHERE id = ?
                """,
                (rewrite.image, rewrite.body_json, rewrite.sections_json, row["id"]),
            )
            record_audit(
                conn,
                user="image-migration",
                action="migrate_images",
                entity="article",
                entity_id=str(row["id"]),
                details={
                    "slug": row["slug"],
                    "cover_refs": rewrite.stats.cover_refs,
                    "body_refs": rewrite.stats.body_refs,
                    "section_refs": rewrite.stats.section_refs,
                },
            )
            conn.commit()
            updated_articles += 1
            if index % 25 == 0:
                LOG.info("[%d/%d] updated=%d unchanged=%d uploaded=%d failed=%d", index, total_rows, updated_articles, unchanged_articles, uploaded, failed)

        save_state(args.state_file, state)

        if updated_articles and not args.no_regen:
            result = regenerate_data_js()
            LOG.info("regenerate_data_js: %s", result)

        LOG.info(
            "done updated_articles=%d unchanged_articles=%d uploaded=%d failed=%d",
            updated_articles,
            unchanged_articles,
            uploaded,
            failed,
        )
        print(
            "STATUS=ok"
            if failed == 0
            else f"STATUS=partial failures={failed} updated_articles={updated_articles} uploaded={uploaded}"
        )
        return 0 if failed == 0 else 1
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
