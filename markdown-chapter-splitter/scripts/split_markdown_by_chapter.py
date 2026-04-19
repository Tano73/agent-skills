#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

CARDINAL_NUMBER_WORDS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
}
ORDINAL_NUMBER_WORDS = {
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
    "sixth": 6,
    "seventh": 7,
    "eighth": 8,
    "ninth": 9,
    "tenth": 10,
    "eleventh": 11,
    "twelfth": 12,
    "thirteenth": 13,
    "fourteenth": 14,
    "fifteenth": 15,
    "sixteenth": 16,
    "seventeenth": 17,
    "eighteenth": 18,
    "nineteenth": 19,
}
TENS_NUMBER_WORDS = {
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}
TENS_ORDINAL_WORDS = {
    "twentieth": 20,
    "thirtieth": 30,
    "fortieth": 40,
    "fiftieth": 50,
    "sixtieth": 60,
    "seventieth": 70,
    "eightieth": 80,
    "ninetieth": 90,
}
NUMBER_WORD_TOKENS = tuple(
    sorted(
        (
            *CARDINAL_NUMBER_WORDS.keys(),
            *ORDINAL_NUMBER_WORDS.keys(),
            *TENS_NUMBER_WORDS.keys(),
            *TENS_ORDINAL_WORDS.keys(),
            "hundred",
            "thousand",
        ),
        key=len,
        reverse=True,
    )
)
NUMBER_WORD_TOKEN_PATTERN = "|".join(re.escape(token) for token in NUMBER_WORD_TOKENS)
CHAPTER_NUMBER_PATTERN = (
    rf"(?:[0-9]+|[ivxlcdm]+|(?:{NUMBER_WORD_TOKEN_PATTERN})"
    rf"(?:[ -](?:{NUMBER_WORD_TOKEN_PATTERN}))*)"
)

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)(?:\s+#+\s*)?$")
FENCE_RE = re.compile(r"^([`~]{3,})")
PAGE_COMMENT_RE = re.compile(r"^<!--\s*Page\s+\d+\s*-->$", re.IGNORECASE)
IMAGE_COMMENT_RE = re.compile(r"^<!--\s*image\s*-->$", re.IGNORECASE)
TEAM_LIB_RE = re.compile(r"^\[\s*Team LiB\s*\]$", re.IGNORECASE)
TOC_LEADER_RE = re.compile(r"\.{2,}")
CHAPTER_RE = re.compile(
    rf"^chapter\s+({CHAPTER_NUMBER_PATTERN})(?:(?:\s*[:.\-]\s*|\s+)(.*))?$",
    re.IGNORECASE,
)
STANDALONE_CHAPTER_RE = re.compile(
    rf"^chapter\s+({CHAPTER_NUMBER_PATTERN})\s*$", re.IGNORECASE
)
PART_RE = re.compile(r"^(?:#+\s*)?part\s+[0-9ivxlcdm]+\b", re.IGNORECASE)
NUMERIC_HEADING_RE = re.compile(r"^(#{1,6})\s+([0-9]+|[IVXLCDM]+)\s*$")
NUMBERED_HEADING_WITH_TITLE_RE = re.compile(
    r"^(#{1,6})\s+([0-9]+|[IVXLCDM]+)\s+(.+?)\s*$"
)

RAW_KIND_SCORE = {
    "paired-heading": 42,
    "numbered-heading": 41,
    "heading-chapter": 36,
    "plain-chapter-block": 40,
    "plain-chapter-inline": 32,
}


@dataclass
class ChapterCandidate:
    start_index: int
    number: int
    title: str
    kind: str
    source_line: str
    score: int = 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Split a Markdown file into one file per chapter or heading level."
    )
    parser.add_argument("input_file", type=Path, help="Path to the source .md file")
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory where the generated chapter files will be written",
    )
    parser.add_argument(
        "--heading-level",
        type=int,
        choices=(1, 2),
        default=1,
        help="Heading level to split on: 1 for '#', 2 for '##' (default: 1)",
    )
    parser.add_argument(
        "--allow-single-section",
        action="store_true",
        help="Allow writing output even if only one section is found at the chosen level",
    )
    return parser.parse_args()


def normalize_text(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = text.replace("\t", " ")
    return re.sub(r"\s+", " ", text.strip())


def extract_heading(line: str) -> tuple[int, str] | None:
    stripped = line.lstrip(" ")
    if len(line) - len(stripped) > 3:
        return None

    match = HEADING_RE.match(stripped.rstrip("\r\n"))
    if not match:
        return None

    return len(match.group(1)), normalize_text(match.group(2))


def extract_heading_title(line: str, level: int) -> str | None:
    heading = extract_heading(line)
    if heading is None or heading[0] != level:
        return None
    return heading[1]


def update_fence_state(
    line: str, in_fence: bool, fence_char: str, fence_len: int
) -> tuple[bool, str, int]:
    stripped = line.lstrip(" ")
    if len(line) - len(stripped) > 3:
        return in_fence, fence_char, fence_len

    match = FENCE_RE.match(stripped)
    if not match:
        return in_fence, fence_char, fence_len

    marker = match.group(1)
    marker_char = marker[0]
    marker_len = len(marker)

    if not in_fence:
        return True, marker_char, marker_len

    if marker_char == fence_char and marker_len >= fence_len:
        return False, "", 0

    return in_fence, fence_char, fence_len


def roman_to_int(value: str) -> int | None:
    digits = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    text = value.upper()
    total = 0
    previous = 0

    for character in reversed(text):
        digit = digits.get(character)
        if digit is None:
            return None
        if digit < previous:
            total -= digit
        else:
            total += digit
            previous = digit

    return total if total > 0 else None


def word_number_to_int(value: str) -> int | None:
    normalized = re.sub(r"[.:]+$", "", normalize_text(value).lower())
    normalized = normalized.replace("-", " ")
    tokens = [token for token in normalized.split() if token and token != "and"]
    if not tokens:
        return None

    total = 0
    current = 0
    parsed_any = False

    for token in tokens:
        if token in CARDINAL_NUMBER_WORDS:
            current += CARDINAL_NUMBER_WORDS[token]
            parsed_any = True
            continue
        if token in ORDINAL_NUMBER_WORDS:
            current += ORDINAL_NUMBER_WORDS[token]
            parsed_any = True
            continue
        if token in TENS_NUMBER_WORDS:
            current += TENS_NUMBER_WORDS[token]
            parsed_any = True
            continue
        if token in TENS_ORDINAL_WORDS:
            current += TENS_ORDINAL_WORDS[token]
            parsed_any = True
            continue
        if token == "hundred":
            current = max(1, current) * 100
            parsed_any = True
            continue
        if token == "thousand":
            total += max(1, current) * 1000
            current = 0
            parsed_any = True
            continue
        return None

    value = total + current
    return value if parsed_any and value > 0 else None


def parse_chapter_number(text: str) -> int | None:
    normalized = normalize_text(text)
    if normalized.isdigit():
        return int(normalized)
    roman_value = roman_to_int(normalized)
    if roman_value is not None:
        return roman_value
    return word_number_to_int(normalized)


def parse_chapter_title(text: str) -> tuple[int, str] | None:
    normalized = normalize_text(text)
    match = CHAPTER_RE.match(normalized)
    if not match:
        return None

    number = parse_chapter_number(match.group(1))
    if number is None:
        return None

    title = (match.group(2) or "").strip(" :.-")
    return number, title


def is_auxiliary_line(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return True
    if PAGE_COMMENT_RE.match(stripped):
        return True
    if IMAGE_COMMENT_RE.match(stripped):
        return True
    if TEAM_LIB_RE.match(normalize_text(stripped)):
        return True
    return False


def looks_like_toc_entry(text: str) -> bool:
    normalized = normalize_text(text)
    if not normalized:
        return False
    if TOC_LEADER_RE.search(normalized):
        return True
    if normalized.startswith("|") and normalized.endswith("|"):
        return True
    return False


def is_plausible_title(text: str) -> bool:
    normalized = normalize_text(text)
    if not normalized:
        return False
    if looks_like_toc_entry(normalized):
        return False
    if PART_RE.match(normalized):
        return False
    if parse_chapter_title(normalized) is not None:
        return False
    if parse_chapter_number(normalized) is not None:
        return False
    return any(character.isalpha() for character in normalized)


def starts_with_uppercase_letter(text: str) -> bool:
    for character in text:
        if character.isalpha():
            return character.isupper()
    return False


def is_plausible_inline_chapter_title(text: str) -> bool:
    normalized = normalize_text(text)
    if not is_plausible_title(normalized):
        return False
    return starts_with_uppercase_letter(normalized)


def find_next_nonempty_line(
    lines: list[str], start_index: int, max_scan: int = 4
) -> tuple[int, str] | None:
    limit = min(len(lines), start_index + max_scan + 1)
    for index in range(start_index, limit):
        raw_line = lines[index]
        if is_auxiliary_line(raw_line):
            continue
        normalized = normalize_text(raw_line)
        if not normalized:
            continue
        return index, normalized
    return None


def find_next_nonempty_heading(
    lines: list[str], start_index: int, max_scan: int = 4
) -> tuple[int, int, str] | None:
    limit = min(len(lines), start_index + max_scan + 1)
    for index in range(start_index, limit):
        if is_auxiliary_line(lines[index]):
            continue
        heading = extract_heading(lines[index])
        if heading is not None:
            return index, heading[0], heading[1]
        normalized = normalize_text(lines[index])
        if normalized:
            return None
    return None


def slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text.lower()).strip("-")
    return slug or "chapter"


def count_headings(lines: list[str], levels: tuple[int, ...] = (1, 2)) -> dict[int, int]:
    in_fence = False
    fence_char = ""
    fence_len = 0
    counts = {level: 0 for level in levels}

    for line in lines:
        if not in_fence:
            for level in levels:
                if extract_heading_title(line, level) is not None:
                    counts[level] += 1

        in_fence, fence_char, fence_len = update_fence_state(
            line, in_fence, fence_char, fence_len
        )

    return counts


def split_by_heading_level(
    lines: list[str], heading_level: int
) -> tuple[list[str], list[tuple[str, list[str]]]]:
    preface_lines: list[str] = []
    sections: list[tuple[str, list[str]]] = []

    in_fence = False
    fence_char = ""
    fence_len = 0
    current_title: str | None = None
    current_lines: list[str] | None = None

    for line in lines:
        title = None
        if not in_fence:
            title = extract_heading_title(line, heading_level)

        in_fence, fence_char, fence_len = update_fence_state(
            line, in_fence, fence_char, fence_len
        )

        if title is not None:
            if current_title is not None and current_lines is not None:
                sections.append((current_title, current_lines))
            current_title = title
            current_lines = [line]
            continue

        if current_lines is None:
            preface_lines.append(line)
        else:
            current_lines.append(line)

    if current_title is not None and current_lines is not None:
        sections.append((current_title, current_lines))

    return preface_lines, sections


def collect_raw_chapter_candidates(lines: list[str]) -> list[ChapterCandidate]:
    candidates: list[ChapterCandidate] = []
    in_fence = False
    fence_char = ""
    fence_len = 0

    for index, line in enumerate(lines):
        if in_fence:
            in_fence, fence_char, fence_len = update_fence_state(
                line, in_fence, fence_char, fence_len
            )
            continue

        heading = extract_heading(line)
        if heading is not None:
            _, heading_title = heading
            parsed_chapter = parse_chapter_title(heading_title)
            if parsed_chapter is not None:
                number, title = parsed_chapter
                candidates.append(
                    ChapterCandidate(
                        start_index=index,
                        number=number,
                        title=title or f"chapter-{number}",
                        kind="heading-chapter",
                        source_line=heading_title,
                    )
                )
            else:
                inline_numeric_heading = NUMBERED_HEADING_WITH_TITLE_RE.match(
                    line.rstrip("\r\n")
                )
                if inline_numeric_heading is not None:
                    number = parse_chapter_number(inline_numeric_heading.group(2))
                    title = normalize_text(inline_numeric_heading.group(3))
                    if number is not None and is_plausible_title(title):
                        candidates.append(
                            ChapterCandidate(
                                start_index=index,
                                number=number,
                                title=title,
                                kind="numbered-heading",
                                source_line=heading_title,
                            )
                        )

                numeric_match = NUMERIC_HEADING_RE.match(line.rstrip("\r\n"))
                if numeric_match is not None:
                    number = parse_chapter_number(numeric_match.group(2))
                    if number is not None:
                        next_heading = find_next_nonempty_heading(lines, index + 1)
                        if next_heading is not None:
                            _, _, next_title = next_heading
                            if is_plausible_title(next_title):
                                candidates.append(
                                    ChapterCandidate(
                                        start_index=index,
                                        number=number,
                                        title=next_title,
                                        kind="paired-heading",
                                        source_line=heading_title,
                                    )
                                )
        else:
            normalized = normalize_text(line)
            parsed_chapter = parse_chapter_title(normalized)
            if parsed_chapter is not None and len(normalized) <= 120:
                number, inline_title = parsed_chapter
                title = inline_title
                kind = "plain-chapter-inline"
                if title and is_plausible_inline_chapter_title(title):
                    candidates.append(
                        ChapterCandidate(
                            start_index=index,
                            number=number,
                            title=title,
                            kind=kind,
                            source_line=normalized,
                        )
                    )
                elif STANDALONE_CHAPTER_RE.match(normalized):
                    next_line = find_next_nonempty_line(lines, index + 1)
                    if next_line is not None and is_plausible_inline_chapter_title(
                        next_line[1]
                    ):
                        title = next_line[1]
                        kind = "plain-chapter-block"
                        candidates.append(
                            ChapterCandidate(
                                start_index=index,
                                number=number,
                                title=title,
                                kind=kind,
                                source_line=normalized,
                            )
                        )

        in_fence, fence_char, fence_len = update_fence_state(
            line, in_fence, fence_char, fence_len
        )

    deduped: dict[tuple[int, int], ChapterCandidate] = {}
    for candidate in candidates:
        key = (candidate.start_index, candidate.number)
        existing = deduped.get(key)
        if existing is None or RAW_KIND_SCORE[candidate.kind] > RAW_KIND_SCORE[existing.kind]:
            deduped[key] = candidate

    return sorted(deduped.values(), key=lambda candidate: candidate.start_index)


def count_meaningful_lines(lines: list[str], start_index: int, end_index: int) -> int:
    count = 0
    for index in range(start_index, end_index):
        raw_line = lines[index]
        normalized = normalize_text(raw_line)
        if is_auxiliary_line(raw_line):
            continue
        if looks_like_toc_entry(normalized):
            continue
        if PART_RE.match(normalized):
            continue
        if parse_chapter_title(normalized) is not None:
            continue
        count += 1
    return count


def has_long_body_line(lines: list[str], start_index: int, end_index: int) -> bool:
    for index in range(start_index, end_index):
        raw_line = lines[index]
        normalized = normalize_text(raw_line)
        if is_auxiliary_line(raw_line):
            continue
        if looks_like_toc_entry(normalized):
            continue
        if PART_RE.match(normalized):
            continue
        if parse_chapter_title(normalized) is not None:
            continue
        if len(normalized) >= 60:
            return True
    return False


def score_chapter_candidates(
    lines: list[str], raw_candidates: list[ChapterCandidate]
) -> list[ChapterCandidate]:
    scored: list[ChapterCandidate] = []
    for index, candidate in enumerate(raw_candidates):
        next_candidates = raw_candidates[index + 1 :]
        next_index = next_candidates[0].start_index if next_candidates else len(lines)
        nearby_future = sum(
            1
            for other in next_candidates
            if other.start_index - candidate.start_index <= 20
        )
        meaningful_lines = count_meaningful_lines(
            lines, candidate.start_index + 1, next_index
        )
        long_body = has_long_body_line(
            lines, candidate.start_index + 1, min(next_index, candidate.start_index + 40)
        )

        score = RAW_KIND_SCORE[candidate.kind]
        score += min(meaningful_lines, 10)
        if long_body:
            score += 10
        score -= nearby_future * 15
        if looks_like_toc_entry(candidate.source_line):
            score -= 30

        scored.append(
            ChapterCandidate(
                start_index=candidate.start_index,
                number=candidate.number,
                title=candidate.title,
                kind=candidate.kind,
                source_line=candidate.source_line,
                score=score,
            )
        )

    return scored


def longest_increasing_chapter_sequence(
    candidates: list[ChapterCandidate],
) -> list[ChapterCandidate]:
    if not candidates:
        return []

    best_length = [1] * len(candidates)
    best_score = [candidate.score for candidate in candidates]
    previous_index: list[int | None] = [None] * len(candidates)

    for index, candidate in enumerate(candidates):
        for previous, previous_candidate in enumerate(candidates[:index]):
            chapter_gap = candidate.number - previous_candidate.number
            if chapter_gap <= 0 or chapter_gap > 5:
                continue

            candidate_length = best_length[previous] + 1
            candidate_score = best_score[previous] + candidate.score
            if candidate_length > best_length[index] or (
                candidate_length == best_length[index]
                and candidate_score > best_score[index]
            ):
                best_length[index] = candidate_length
                best_score[index] = candidate_score
                previous_index[index] = previous

    end_index = max(
        range(len(candidates)),
        key=lambda index: (best_length[index], best_score[index]),
    )

    sequence: list[ChapterCandidate] = []
    current: int | None = end_index
    while current is not None:
        sequence.append(candidates[current])
        current = previous_index[current]

    sequence.reverse()
    return sequence


def detect_text_chapter_candidates(lines: list[str]) -> list[ChapterCandidate]:
    raw_candidates = collect_raw_chapter_candidates(lines)
    scored_candidates = score_chapter_candidates(lines, raw_candidates)

    best_by_number: dict[int, ChapterCandidate] = {}
    for candidate in scored_candidates:
        existing = best_by_number.get(candidate.number)
        if existing is None or candidate.score > existing.score or (
            candidate.score == existing.score
            and candidate.start_index > existing.start_index
        ):
            best_by_number[candidate.number] = candidate

    filtered_candidates = sorted(
        (
            candidate
            for candidate in best_by_number.values()
            if candidate.score >= 35
        ),
        key=lambda candidate: candidate.start_index,
    )

    sequence = longest_increasing_chapter_sequence(filtered_candidates)
    return sequence if len(sequence) >= 2 else []


def split_by_candidates(
    lines: list[str], candidates: list[ChapterCandidate]
) -> tuple[list[str], list[tuple[str, list[str]]]]:
    sorted_candidates = sorted(candidates, key=lambda candidate: candidate.start_index)
    preface_lines = lines[: sorted_candidates[0].start_index]
    sections: list[tuple[str, list[str]]] = []

    for index, candidate in enumerate(sorted_candidates):
        end_index = (
            sorted_candidates[index + 1].start_index
            if index + 1 < len(sorted_candidates)
            else len(lines)
        )
        sections.append((candidate.title, lines[candidate.start_index:end_index]))

    return preface_lines, sections


def unique_filename(base_slug: str, used: dict[str, int]) -> str:
    count = used.get(base_slug, 0) + 1
    used[base_slug] = count
    if count == 1:
        return base_slug
    return f"{base_slug}-{count}"


def write_output(
    output_dir: Path,
    preface_lines: list[str],
    sections: list[tuple[str, list[str]]],
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    written_files: list[Path] = []
    if "".join(preface_lines).strip():
        preface_path = output_dir / "00-preface.md"
        preface_path.write_text("".join(preface_lines), encoding="utf-8")
        written_files.append(preface_path)

    width = max(2, len(str(len(sections))))
    used_slugs: dict[str, int] = {}

    for index, (title, section_lines) in enumerate(sections, start=1):
        slug = unique_filename(slugify(title), used_slugs)
        filename = f"{index:0{width}d}-{slug}.md"
        section_path = output_dir / filename
        section_path.write_text("".join(section_lines), encoding="utf-8")
        written_files.append(section_path)

    return written_files


def default_output_dir(input_file: Path) -> Path:
    return input_file.with_name(input_file.stem)


def print_detection_counts(
    heading_counts: dict[int, int], text_candidates: list[ChapterCandidate]
) -> None:
    print(f"H1 headings found: {heading_counts.get(1, 0)}", file=sys.stderr)
    print(f"H2 headings found: {heading_counts.get(2, 0)}", file=sys.stderr)
    print(
        f"Text chapter candidates found: {len(text_candidates)}",
        file=sys.stderr,
    )


def main() -> int:
    args = parse_args()
    input_file = args.input_file.expanduser().resolve()

    if not input_file.exists():
        print(f"Input file does not exist: {input_file}", file=sys.stderr)
        return 1

    if not input_file.is_file():
        print(f"Input path is not a file: {input_file}", file=sys.stderr)
        return 1

    if input_file.suffix.lower() != ".md":
        print(
            f"Input file must have a .md extension: {input_file}",
            file=sys.stderr,
        )
        return 1

    content = input_file.read_text(encoding="utf-8")
    lines = content.splitlines(keepends=True)
    heading_counts = count_headings(lines)
    text_candidates = detect_text_chapter_candidates(lines)

    split_mode = f"H{args.heading_level}"
    if args.heading_level == 1 and heading_counts[1] <= 1 and len(text_candidates) >= 2:
        preface_lines, sections = split_by_candidates(lines, text_candidates)
        split_mode = "TEXT_CHAPTER"
    else:
        preface_lines, sections = split_by_heading_level(lines, args.heading_level)

    if args.heading_level == 1 and split_mode != "TEXT_CHAPTER":
        if heading_counts[1] == 0:
            print_detection_counts(heading_counts, text_candidates)
            print(
                "No top-level '# ' chapters were found and no reliable text-based chapter sequence was detected. The file was not split.",
                file=sys.stderr,
            )
            return 2

        if heading_counts[1] == 1 and not args.allow_single_section:
            print_detection_counts(heading_counts, text_candidates)
            print(
                "Only 1 top-level '# ' chapter was found and no reliable text-based chapter sequence was detected. The file was not split. Rerun with --allow-single-section to keep that single H1 section.",
                file=sys.stderr,
            )
            return 3

    if not sections:
        print_detection_counts(heading_counts, text_candidates)
        if args.heading_level == 1:
            print(
                "No top-level '# ' chapters were found and no reliable text-based chapter sequence was detected. The file was not split.",
                file=sys.stderr,
            )
            return 2

        print(
            "No level-2 '##' sections were found. There is nothing to split at H2 level.",
            file=sys.stderr,
        )
        return 4

    output_dir = (
        args.output_dir.expanduser().resolve()
        if args.output_dir is not None
        else default_output_dir(input_file)
    )
    written_files = write_output(output_dir, preface_lines, sections)

    print(f"Output directory: {output_dir}")
    print(
        f"Preface file created: {'yes' if any(path.name == '00-preface.md' for path in written_files) else 'no'}"
    )
    print(f"Section files created: {len(sections)}")
    print(f"Split mode used: {split_mode}")
    print(f"H1 headings found: {heading_counts[1]}")
    print(f"H2 headings found: {heading_counts[2]}")
    print(f"Text chapter candidates found: {len(text_candidates)}")
    for path in written_files:
        print(path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
