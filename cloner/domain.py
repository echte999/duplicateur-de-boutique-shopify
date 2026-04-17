import re


class DomainRemapper:
    def __init__(self, source_myshopify: str, target_domain: str, source_custom: str | None = None):
        self._replacements: list[tuple[str, str]] = []

        if source_myshopify:
            self._replacements.append((re.escape(source_myshopify), target_domain))
        if source_custom:
            self._replacements.append((re.escape(source_custom), target_domain))

        self._pattern = re.compile("|".join(p for p, _ in self._replacements)) if self._replacements else None

    def remap(self, text: str | None) -> str | None:
        if not text or not self._pattern:
            return text

        def _replace(match: re.Match) -> str:
            for pattern, replacement in self._replacements:
                if re.fullmatch(pattern, match.group(0)):
                    return replacement
            return match.group(0)

        return self._pattern.sub(_replace, text)
