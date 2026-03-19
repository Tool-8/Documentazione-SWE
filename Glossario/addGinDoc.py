from pathlib import Path
import re
import logging
from typing import List, Tuple, Pattern, Optional, Set

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s | %(message)s')

SRC_DIR: Path = Path(__file__).resolve().parent.parent
EXCLUDE_DIRS: Set[str] = {"Candidatura", "Glossario"}
IGNORE_FILENAMES: Set[str] = {"heading.tex", "table.tex", "title.tex", "modifiche.tex", "Lettera_di_Presentazione_RTB.tex"}


def find_glossary() -> Optional[Path]:
    gloss_path: Path = SRC_DIR / "Glossario" / "Glossario.tex"
    if gloss_path.exists():
        logging.info(f"Glossario trovato: {gloss_path}")
        return gloss_path
    logging.error("Glossario non trovato nella cartella Glossario")
    return None


def estrai_termini_da_file(fpath: Path) -> List[str]:
    text: str = fpath.read_text(encoding="utf-8")
    termini: List[str] = []
    pos: int = 0
    while True:
        idx: int = text.find(r"\term{", pos)
        if idx == -1:
            break
        idx += len(r"\term{")
        brace: int = 1
        start: int = idx
        while idx < len(text) and brace > 0:
            if text[idx] == "{":
                brace += 1
            elif text[idx] == "}":
                brace -= 1
            idx += 1
        termine_raw: str = text[start:idx - 1].strip()
        termine_clean: str = re.sub(r'\\[a-zA-Z]+\{[^}]*\}', '', termine_raw).strip()
        if termine_clean:
            termini.append(termine_clean)
        pos = idx
    return termini


def build_patterns(termini: List[str]) -> List[Tuple[str, Pattern]]:
    termini_filtered: List[str] = [t for t in termini if t and t.strip()]
    termini_sorted: List[str] = sorted(set(termini_filtered), key=len, reverse=True)
    patterns: List[Tuple[str, Pattern]] = []
    for term in termini_sorted:
        pat: Pattern = re.compile(
            rf'(?<!\\)(?<!\w)({re.escape(term)})(?!\$\^G\$)(?!\w)',
            flags=re.IGNORECASE | re.MULTILINE
        )
        patterns.append((term, pat))
    return patterns


def should_skip(tex_file: Path) -> bool:
    if any(part in EXCLUDE_DIRS for part in tex_file.parts):
        return True
    if tex_file.name in IGNORE_FILENAMES:
        return True
    parent_name: str = tex_file.parent.name.replace(" ", "_")
    if tex_file.stem == parent_name:
        return True
    return False


def apply_tags_to_text(text: str, patterns: List[Tuple[str, Pattern]], tex_file: Path) -> str:
    """
    Applica i patterns su `text` aggiungendo $^G$ solo se:
      - subito dopo il match non c'è già $^G$
      - il match NON è all'interno di un titolo (section, subsection, subsubsection, ...)
      - il carattere successivo è spazio o fine stringa
      - non si trova all'interno di comandi come label, url, hyperref, ref ecc...
    """
    text = text.replace('$^G$', '')
    title_ranges: List[Tuple[int, int]] = []
    link_ranges: List[Tuple[int, int]] = []

    # Sezioni/subsezioni
    for m in re.finditer(r'\\(?:sub)*section\{(.*?)\}', text, flags=re.MULTILINE):
        start, end = m.start(1), m.end(1)
        title_ranges.append((start, end))

    # Caption
    for m in re.finditer(r'\\caption\{(.*?)\}', text, flags=re.MULTILINE):
        start, end = m.start(1), m.end(1)
        title_ranges.append((start, end))

    # \href{URL}
    for m in re.finditer(r'\\href\s*\{([^}]*)\}', text, flags=re.MULTILINE):
        start, end = m.start(1), m.end(1)
        link_ranges.append((start, end))

    # \ref{URL}
    for m in re.finditer(r'\\ref\s*\{([^}]*)\}', text, flags=re.MULTILINE):
        start, end = m.start(1), m.end(1)
        link_ranges.append((start, end))

    # \url{URL}
    for m in re.finditer(r'\\(?:url|path)\s*\{([^}]*)\}', text, flags=re.MULTILINE):
        start, end = m.start(1), m.end(1)
        link_ranges.append((start, end))

    # \label{etichetta}
    for m in re.finditer(r'\\label\s*\{([^}]*)\}', text, flags=re.MULTILINE):
        start, end = m.start(1), m.end(1)
        link_ranges.append((start, end))

    # \hyperref[ref]
    for m in re.finditer(r'\\hyperref\s*\[([^\]]*)\]', text, flags=re.MULTILINE):
        start, end = m.start(1), m.end(1)
        link_ranges.append((start, end))

    # \textbf{...}
    for m in re.finditer(r'\\textbf\s*\{([^}]*)\}', text, flags=re.MULTILINE):
        start, end = m.start(1), m.end(1)
        link_ranges.append((start, end))

    # Ambienti tabella  <-- NUOVO
    for m in re.finditer(
        r'\\begin\{(tabular|table|longtable|tabularx|tabulary|array)\*?\}.*?\\end\{\1\*?\}',
        text,
        flags=re.MULTILINE | re.DOTALL
    ):
        link_ranges.append((m.start(), m.end()))

    # \node TikZ
    for m in re.finditer(r'\\node\b.*?;', text, flags=re.MULTILINE | re.DOTALL):
        start, end = m.start(), m.end()
        link_ranges.append((start, end))

    # \usepackage{...}, \RequirePackage{...}, \documentclass{...}
    for m in re.finditer(r'\\(?:usepackage|RequirePackage|documentclass)\s*(?:\[[^\]]*\])?\s*\{([^}]*)\}', text, flags=re.MULTILINE):
        start, end = m.start(1), m.end(1)
        link_ranges.append((start, end))

    # \input, \include, \includegraphics, \bibliography
    for m in re.finditer(r'\\(?:input|include|includegraphics|bibliography)\s*(?:\[[^\]]*\])?\s*\{([^}]*)\}', text, flags=re.MULTILINE):
        start, end = m.start(1), m.end(1)
        link_ranges.append((start, end))

    def in_title(pos: int) -> bool:
        return any(start <= pos < end for start, end in title_ranges)

    def in_link(pos: int) -> bool:
        return any(start <= pos < end for start, end in link_ranges)

    occupied: List[Tuple[int, int]] = []
    inserts: List[Tuple[int, str, str]] = []

    def overlaps_or_contained(start: int, end: int) -> bool:
        """Verifica se il range [start, end) si sovrappone o è contenuto in un range già occupato"""
        for occ_start, occ_end in occupied:
            if not (end <= occ_start or start >= occ_end):
                return True
        return False

    for _, pat in patterns:
        for m in pat.finditer(text):
            start, end = m.start(1), m.end(1)

            if in_title(start):
                continue
            if in_link(start):
                continue
            if overlaps_or_contained(start, end):
                continue
            if text[end:end + 4] == "$^G$":
                continue

            before_char: str = text[start-1:start] if start > 0 else ""
            after_char: str = text[end:end + 1]

            if before_char == "." or after_char == ".":
                continue
            if after_char and not (after_char.isspace() or after_char in {",", ";", ":", ")", "]", "}"}):
                continue

            inserts.append((end, "$^G$", m.group(1)))
            occupied.append((start, end))

    for pos, insert_text, matched in sorted(inserts, key=lambda x: x[0], reverse=True):
        text = text[:pos] + insert_text + text[pos:]
        logging.debug(f"Aggiunto $^G$ a '{matched}' in file {tex_file}")

    return text


def process_all_tex(root_dir: Path, patterns: List[Tuple[str, Pattern]]) -> None:
    for tex_file in root_dir.rglob("*.tex"):
        if should_skip(tex_file):
            continue
        original_text: str = tex_file.read_text(encoding="utf-8")
        modified_text: str = apply_tags_to_text(original_text, patterns, tex_file)
        if modified_text != original_text:
            tex_file.write_text(modified_text, encoding="utf-8")
            logging.info(f"Modificato: {tex_file}")


if __name__ == "__main__":
    logging.info("Inizio elaborazione")
    gloss: Optional[Path] = find_glossary()
    termini: List[str] = []

    if gloss:
        termini.extend(estrai_termini_da_file(gloss))
        letters_dir: Path = gloss.parent / "Contents"
        if letters_dir.exists():
            for f in sorted(letters_dir.glob("*.tex")):
                termini.extend(estrai_termini_da_file(f))

    termini_filtered: List[str] = [t for t in termini if t and t.strip()]
    patterns: List[Tuple[str, Pattern]] = build_patterns(termini_filtered)
    logging.info(f"Pattern creati per {len(patterns)} termini")
    print(termini_filtered)

    process_all_tex(SRC_DIR, patterns)
    logging.info("Elaborazione completata")