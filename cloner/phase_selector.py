import sys
import os
import json
import msvcrt
from pathlib import Path
from cloner.state import ALL_PHASES

PHASE_LABELS = {
    "products":    "Produits + variantes",
    "collections": "Collections",
    "pages":       "Pages statiques",
    "blogs":       "Articles de blog",
    "menus":       "Menus",
    "policies":    "Politiques du site",
    "discounts":   "Réductions",
    "theme":       "Thème actif",
}

PHASE_DEPS: dict[str, list[str]] = {
    "collections": ["products"],
    "menus":       ["collections", "pages"],
}

SELECTION_PATH = Path("output/phase_selection.json")


def load_saved_selection() -> list[str]:
    if not SELECTION_PATH.exists():
        return ALL_PHASES[:]
    try:
        data = json.loads(SELECTION_PATH.read_text(encoding="utf-8"))
        saved = data.get("selected_phases", ALL_PHASES[:])
        return [p for p in saved if p in ALL_PHASES]
    except Exception:
        return ALL_PHASES[:]


def save_selection(selected: list[str]) -> None:
    SELECTION_PATH.parent.mkdir(parents=True, exist_ok=True)
    SELECTION_PATH.write_text(
        json.dumps({"selected_phases": selected}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _get_key() -> str:
    """Read a keypress and return a normalized key name."""
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
            missing = [PHASE_LABELS[d] for d in deps if d not in selected]
            if missing:
                out.append(f"  ⚠  '{PHASE_LABELS[phase]}' dépend de : {', '.join(missing)}")
    return out


def _render(selected: set[str], cursor: int, error: str) -> int:
    """Draw the menu, return number of lines printed."""
    lines = []
    lines.append("")
    lines.append("  Choisissez les phases à cloner")
    lines.append("  ────────────────────────────────────────")

    for i, phase in enumerate(ALL_PHASES):
        check = "●" if phase in selected else "○"
        arrow = "▶" if i == cursor else " "
        label = PHASE_LABELS[phase]
        # Highlight the current line
        if i == cursor:
            lines.append(f"  {arrow} [{check}]  \033[1m{label}\033[0m")
        else:
            lines.append(f"  {arrow} [{check}]  {label}")

    lines.append("  ────────────────────────────────────────")
    lines.append("  ↑↓ Naviguer   Espace Cocher/décocher   A Tout/rien   Entrée Confirmer")

    warn = _warnings(selected)
    if warn:
        lines.append("")
        for w in warn:
            lines.append(f"\033[33m{w}\033[0m")

    if error:
        lines.append(f"\n  \033[31m{error}\033[0m")

    print("\n".join(lines), flush=True)
    return len(lines)


def select_phases() -> list[str]:
    """Interactive arrow-key checkbox menu. Returns ordered list of selected phases."""
    # Enable ANSI codes on Windows
    os.system("")

    selected: set[str] = set(load_saved_selection())
    cursor: int = 0
    error: str = ""
    line_count: int = 0

    # Initial render
    line_count = _render(selected, cursor, error)

    while True:
        key = _get_key()

        # Erase previous render
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
                error = "Sélectionnez au moins une phase."
            else:
                line_count = _render(selected, cursor, error)
                break

        line_count = _render(selected, cursor, error)

    result = [p for p in ALL_PHASES if p in selected]
    save_selection(result)
    return result
