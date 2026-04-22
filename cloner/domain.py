import re


class DomainRemapper:
    def __init__(
        self,
        source_myshopify: str,
        target_domain: str,
        source_custom: str | None = None,
        source_shop_name: str | None = None,
        target_shop_name: str | None = None,
    ):
        self._replacements: list[tuple[str, str]] = []

        if source_myshopify:
            self._replacements.append((re.escape(source_myshopify), target_domain))
        if source_custom:
            self._replacements.append((re.escape(source_custom), target_domain))

        self._pattern = re.compile("|".join(p for p, _ in self._replacements)) if self._replacements else None
        self._source_shop_name = source_shop_name
        self._target_shop_name = target_shop_name

    def remap(self, text: str | None) -> str | None:
        if not text:
            return text

        if self._pattern:
            def _replace(match: re.Match) -> str:
                for pattern, replacement in self._replacements:
                    if re.fullmatch(pattern, match.group(0)):
                        return replacement
                return match.group(0)

            text = self._pattern.sub(_replace, text)

        if self._source_shop_name and self._target_shop_name:
            text = text.replace(self._source_shop_name, self._target_shop_name)

        return text
