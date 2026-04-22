import json
import shutil
from pathlib import Path

STATE_PATH = Path("output/clone_state.json")
TMP_IMAGES_PATH = Path("tmp_images")

_current_source_shop: str | None = None


def load_state(source_shop: str) -> list[str]:
    global _current_source_shop
    _current_source_shop = source_shop

    if not STATE_PATH.exists():
        return []

    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        stored_shop = data.get("source_shop")
        if stored_shop != source_shop:
            print(f"[REPRISE] Boutique source différente ({stored_shop} ≠ {source_shop}), état ignoré.")
            STATE_PATH.unlink()
            return []
        completed: list[str] = data.get("completed_phases", [])
        print(f"[REPRISE] État trouvé : {len(completed)} phase(s) déjà complétée(s) : {completed}")
        return completed
    except Exception as e:
        print(f"[REPRISE] Avertissement : clone_state.json illisible ({e}), démarrage depuis zéro.")
        return []


def save_phase_completed(phase_name: str) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)

    data: dict = {}
    if STATE_PATH.exists():
        try:
            data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            data = {}

    completed: list[str] = data.get("completed_phases", [])
    if phase_name not in completed:
        completed.append(phase_name)

    data["source_shop"] = _current_source_shop
    data["completed_phases"] = completed
    STATE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def clear_state() -> None:
    if STATE_PATH.exists():
        STATE_PATH.unlink()


def cleanup_tmp_images() -> None:
    if TMP_IMAGES_PATH.exists():
        shutil.rmtree(TMP_IMAGES_PATH)
        print(f"[NETTOYAGE] Dossier {TMP_IMAGES_PATH}/ supprimé.")
    else:
        print(f"[NETTOYAGE] Dossier {TMP_IMAGES_PATH}/ absent, rien à supprimer.")
