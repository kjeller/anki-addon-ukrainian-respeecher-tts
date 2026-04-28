"""Ukrainian Audio Generator — Anki add-on.

Generates Ukrainian TTS audio files for every note using the Respeecher
Ukrainian Real-Time TTS API and embeds a [sound:…] tag into the note.

Minimum Anki version: 2.1.45
"""

import hashlib
import html
import os
import re
from typing import Optional

from aqt import mw
from aqt.qt import (
    QAction, QDialog, QDialogButtonBox, QLabel, QListWidget,
    QListWidgetItem, QMenu, QVBoxLayout, Qt,
)
from aqt.utils import showCritical, showInfo, showWarning

from . import respeecher_client as rc

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _config() -> dict:
    return mw.addonManager.getConfig(__name__) or {}


def _strip_html(text: str) -> str:
    """Remove HTML/Anki tags, decode entities, and normalise whitespace."""
    text = re.sub(r"<br\s*/?>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\[[^\]]+\]", "", text)   # strip [sound:…] etc.
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _cache_basename(text: str, voice_id: str) -> str:
    digest = hashlib.md5(f"{voice_id}\x00{text}".encode()).hexdigest()[:16]
    return f"respeecher_ukr_{digest}"


def _find_cached(media_dir: str, basename: str) -> Optional[str]:
    for ext in rc.AUDIO_EXTENSIONS:
        filename = f"{basename}.{ext}"
        if os.path.exists(os.path.join(media_dir, filename)):
            return filename
    return None


# ---------------------------------------------------------------------------
# Deck selection dialog
# ---------------------------------------------------------------------------

class _DeckDialog(QDialog):
    def __init__(self, deck_names: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Decks")
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Select decks to generate audio for:"))

        self._list = QListWidget()
        for name in deck_names:
            item = QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self._list.addItem(item)
        layout.addWidget(self._list)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selected_decks(self) -> list[str]:
        return [
            self._list.item(i).text()
            for i in range(self._list.count())
            if self._list.item(i).checkState() == Qt.CheckState.Checked
        ]


# ---------------------------------------------------------------------------
# Background worker
# ---------------------------------------------------------------------------

def _run_generation(
    api_key: str,
    voice_id: str,
    source_field: str,
    audio_field: str,
    skip_existing: bool,
    deck_names: list[str],
) -> dict:
    stats = {"processed": 0, "skipped": 0, "errors": 0, "error_details": []}

    mw.taskman.run_on_main(lambda: mw.progress.start(
        label="Starting…", immediate=True
    ))

    try:
        # Collect note IDs from all selected decks (deduplicated)
        note_id_set: set[int] = set()
        for deck in deck_names:
            note_id_set.update(mw.col.find_notes(f'deck:"{deck}"'))
        note_ids = list(note_id_set)
        total = len(note_ids)
        media_dir = mw.col.media.dir()

        for i, note_id in enumerate(note_ids):
            note = mw.col.get_note(note_id)

            if source_field not in note:
                stats["skipped"] += 1
                continue

            plain_text = _strip_html(note[source_field])
            if not plain_text:
                stats["skipped"] += 1
                continue

            target_field = audio_field if (audio_field and audio_field in note) else source_field

            if skip_existing and "[sound:" in note[target_field]:
                stats["skipped"] += 1
                continue

            label_text = plain_text[:50] + "…" if len(plain_text) > 50 else plain_text
            mw.taskman.run_on_main(
                lambda lbl=f"({i + 1}/{total}) {label_text}", iv=i, tv=total:
                    mw.progress.update(label=f"Generating audio…\n{lbl}", value=iv, max=tv)
            )

            try:
                basename = _cache_basename(plain_text, voice_id)
                cached = _find_cached(media_dir, basename)

                if cached:
                    filename = cached
                else:
                    audio_data, ext = rc.synthesize(api_key, plain_text, voice_id)
                    filename = f"{basename}.{ext}"
                    with open(os.path.join(media_dir, filename), "wb") as fh:
                        fh.write(audio_data)

                sound_tag = f"[sound:{filename}]"
                if sound_tag not in note[target_field]:
                    if audio_field and audio_field in note:
                        note[audio_field] = sound_tag
                    else:
                        note[source_field] = note[source_field] + sound_tag
                    mw.col.update_note(note)

                stats["processed"] += 1

            except Exception as exc:  # noqa: BLE001
                stats["errors"] += 1
                stats["error_details"].append(f"Note {note_id}: {exc}")

    finally:
        mw.taskman.run_on_main(mw.progress.finish)

    return stats


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

def _action_generate() -> None:
    cfg = _config()
    api_key = cfg.get("api_key", "").strip()
    voice_id = cfg.get("voice_id", "").strip()
    source_field = cfg.get("source_field", "Front")
    audio_field = cfg.get("audio_field", "")
    skip_existing = cfg.get("skip_if_audio_exists", True)

    if not api_key:
        showCritical(
            "No API key configured.\n\n"
            "Go to Tools › Add-ons, select this add-on, click Config "
            "and set your api_key."
        )
        return

    if not voice_id:
        showCritical(
            "No voice configured.\n\n"
            "Run Tools › Ukrainian Audio Generator › List Voices, "
            "then set voice_id in the add-on config (e.g. \"olesia-media\")."
        )
        return

    # Show deck selection dialog
    deck_names = sorted(mw.col.decks.all_names())
    dialog = _DeckDialog(deck_names, parent=mw)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return

    selected = dialog.selected_decks()
    if not selected:
        showWarning("No decks selected.")
        return

    def on_done(future):
        try:
            stats = future.result()
        except Exception as exc:  # noqa: BLE001
            showCritical(f"Generation failed:\n\n{exc}")
            return

        msg = (
            f"✅  Audio generation complete!\n\n"
            f"  Processed : {stats['processed']}\n"
            f"  Skipped   : {stats['skipped']}\n"
            f"  Errors    : {stats['errors']}"
        )
        if stats["error_details"]:
            msg += "\n\nFirst errors:\n" + "\n".join(stats["error_details"][:5])
        showInfo(msg)

    mw.taskman.run_in_background(
        lambda: _run_generation(api_key, voice_id, source_field, audio_field, skip_existing, selected),
        on_done,
    )


def _action_list_voices() -> None:
    cfg = _config()
    api_key = cfg.get("api_key", "").strip()

    if not api_key:
        showCritical("Please configure your api_key first.")
        return

    def on_done(future):
        try:
            voices = future.result()
        except Exception as exc:  # noqa: BLE001
            showCritical(f"Could not fetch voices:\n\n{exc}")
            return

        if not voices:
            showWarning("No voices found.")
            return

        lines = [f"• {v['id']:<30} {v.get('full_name', '')}" for v in voices]
        showInfo(
            "Available voices  (use the ID as voice_id in config):\n\n"
            + "\n".join(lines)
        )

    mw.taskman.run_in_background(lambda: rc.list_voices(api_key), on_done)


# ---------------------------------------------------------------------------
# Menu
# ---------------------------------------------------------------------------

def _build_menu() -> None:
    submenu = QMenu("Ukrainian Audio Generator", mw)

    act_generate = QAction("Generate Audio", mw)
    act_generate.triggered.connect(_action_generate)
    submenu.addAction(act_generate)

    act_voices = QAction("List Voices", mw)
    act_voices.triggered.connect(_action_list_voices)
    submenu.addAction(act_voices)

    mw.form.menuTools.addMenu(submenu)


_build_menu()
