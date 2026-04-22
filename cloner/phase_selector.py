import json
import msvcrt
import os
import sys
from pathlib import Path

from cloner.state import ALL_PHASES

PHASE_LABELS = {
    "products": "Produits + variantes",
    "collections": "Collections",
    "pages": "Pages statiques",
    "blogs": "Articles de blog",
    "menus": "Menus",
    "policies": "Politiques du site",
    "discounts": "Reductions",
    "theme": "Tous les themes installes",
}

PHASE_DEPS: dict[str, list[str]] = {
    "collections": ["products"],
    "menus": ["collections", "pages"],
}

SELECTION_PATH = Path("output/phase_selection.json")


def load_saved_selection() -> list[str]:
    if not SELECTION_PATH.exists():
        return ALL_PHASES[:]
    try:
        data = json.loads(SELECTION_PATH.read_text(encoding="utf-8"))
        saved = data.get("selected_phases", ALL_PHASES[:])
        return [phase for phase in saved if phase in ALL_PHASES]
    except Exception:
        return ALL_PHASES[:]


def save_selection(selected: list[str]) -> None:
    SELECTION_PATH.parent.mkdir(parents=True, exist_ok=True)
    SELECTION_PATH.write_text(
        json.dumps({"selected_phases": selected}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _get_key() -> str:
    key = msvcrt.getch()
    if key in (b"\xe0", b"\x00"):
        key2 = msvcrt.getch()
        mapping = {
            b"H": "UP",
            b"P": "DOWN",
        }
        return mapping.get(key2, "")
    if key == b" ":
        return "SPACE"
    if key in (b"\r", b"\n"):
        return "ENTER"
    if key in (b"a", b"A"):
        return "ALL"
    return ""


def _warnings(selected: set[str]) -> list[str]:
    out = []
    for phase, deps in PHASE_DEPS.items():
        if phase in selected:
            missing = [PHASE_LABELS[dep] for dep in deps if dep not in selected]
            if missing:
                out.append(f"  !  '{PHASE_LABELS[phase]}' depend de : {', '.join(missing)}")
    return out


def _render(selected: set[str], cursor: int, error: str) -> int:
    lines = []
    lines.append("")
    lines.append("  Choisissez les phases a cloner")
    lines.append("  ----------------------------------------")

    for index, phase in enumerate(ALL_PHASES):
        check = "●" if phase in selected else "○"
        arrow = "▶" if index == cursor else " "
        label = PHASE_LABELS[phase]
        if index == cursor:
            lines.append(f"  {arrow} [{check}]  \033[1m{label}\033[0m")
        else:
            lines.append(f"  {arrow} [{check}]  {label}")

    lines.append("  ----------------------------------------")
    lines.append("  ↑↓ Naviguer   Espace Cocher/decocher   A Tout/rien   Entree Confirmer")

    warnings = _warnings(selected)
    if warnings:
        lines.append("")
        for warning in warnings:
            lines.append(f"\033[33m{warning}\033[0m")

    if error:
        lines.append(f"\n  \033[31m{error}\033[0m")

    print("\n".join(lines), flush=True)
    return len(lines)


def select_phases() -> list[str]:
    os.system("")

    selected: set[str] = set(load_saved_selection())
    cursor = 0
    error = ""
    line_count = _render(selected, cursor, error)

    while True:
        key = _get_key()

        sys.stdout.write(f"\033[{line_count}A\033[J")
        sys.stdout.flush()
        error = ""

        if key == "UP":
            cursor = (cursor - 1) % len(ALL_PHASES)
        elif key == "DOWN":
            cursor = (cursor + 1) % len(ALL_PHASES)
        elif key == "SPACE":
            phase = ALL_PHASES[cursor]
            if phase in selected:
                selected.discard(phase)
            else:
                selected.add(phase)
        elif key == "ALL":
            if len(selected) == len(ALL_PHASES):
                selected.clear()
            else:
                selected = set(ALL_PHASES)
        elif key == "ENTER":
            if not selected:
                error = "Selectionnez au moins une phase."
            else:
                line_count = _render(selected, cursor, error)
                break

        line_count = _render(selected, cursor, error)

    result = [phase for phase in ALL_PHASES if phase in selected]
    save_selection(result)
    return result
