import json
import shutil
from pathlib import Path

STATE_PATH = Path("output/clone_state.json")
TMP_IMAGES_PATH = Path("tmp_images")

ALL_PHASES = ["products", "collections", "pages", "blogs", "menus", "policies", "discounts", "theme"]

_current_source_shop: str | None = None
_selected_phases: list[str] = ALL_PHASES[:]


def load_state(source_shop: str, selected_phases: list[str] | None = None) -> tuple[list[str], list[str]]:
    """
    Returns (completed_phases, effective_selected_phases).
    effective_selected_phases comes from the state file if resuming, else from the argument.
    """
    global _current_source_shop, _selected_phases
    _current_source_shop = source_shop
    _selected_phases = selected_phases if selected_phases is not None else ALL_PHASES[:]

    if not STATE_PATH.exists():
        return [], _selected_phases

    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        stored_shop = data.get("source_shop")
        if stored_shop != source_shop:
            print(f"[REPRISE] Boutique source différente ({stored_shop} ≠ {source_shop}), état ignoré.")
            STATE_PATH.unlink()
            return [], _selected_phases

        completed: list[str] = data.get("completed_phases", [])
        # Compatibilité ascendante : si absent, toutes les phases sont sélectionnées
        saved_selected: list[str] = data.get("selected_phases", ALL_PHASES[:])
        _selected_phases = saved_selected
        print(f"[REPRISE] État trouvé : {len(completed)} phase(s) complétée(s) : {completed}")
        print(f"[REPRISE] Phases sélectionnées pour ce run : {saved_selected}")
        return completed, saved_selected
    except Exception as e:
        print(f"[REPRISE] Avertissement : clone_state.json illisible ({e}), démarrage depuis zéro.")
        return [], _selected_phases


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
    data["selected_phases"] = _selected_phases
    STATE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def is_clone_complete(completed_phases: list[str]) -> bool:
    """True when all selected phases are completed."""
    return all(p in completed_phases for p in _selected_phases)


def clear_state() -> None:
    if STATE_PATH.exists():
        STATE_PATH.unlink()


def cleanup_tmp_images() -> None:
    if TMP_IMAGES_PATH.exists():
        shutil.rmtree(TMP_IMAGES_PATH)
        print(f"[NETTOYAGE] Dossier {TMP_IMAGES_PATH}/ supprimé.")
    else:
        print(f"[NETTOYAGE] Dossier {TMP_IMAGES_PATH}/ absent, rien à supprimer.")
