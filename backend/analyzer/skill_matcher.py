import re
import difflib
import ahocorasick

from .skill_dictionary import load_skill_dictionary


# Explicit false-positive pairs that must never be considered partial matches
EXPLICIT_NON_MATCHES = {
    ("java", "javascript"),
    ("javascript", "java"),
    ("java", "js"),
    ("js", "java"),
    ("c", "c++"),
    ("c++", "c"),
    ("c", "c#"),
    ("c#", "c"),
    ("c", "css"),
    ("css", "c"),
    ("r", "react"),
    ("react", "r"),
    ("r", "rust"),
    ("rust", "r"),
    ("r", "ruby"),
    ("ruby", "r"),
    ("sql", "nosql"),
    ("nosql", "sql"),
}


def is_explicit_non_match(skill_a: str, skill_b: str) -> bool:
    a, b = skill_a.strip().lower(), skill_b.strip().lower()
    return (a, b) in EXPLICIT_NON_MATCHES or (b, a) in EXPLICIT_NON_MATCHES


def normalize_text(text: str) -> str:
    """
    Normalize extracted resume text before matching.
    """

    text = text.lower()
    text = text.replace("\n", " ")

    # Keep only useful characters.
    text = re.sub(r"[^\w#+.-]", " ", text)

    # Collapse multiple spaces.
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def build_automaton():
    """
    Build Aho-Corasick automaton for every canonical skill
    and all of its aliases.
    """

    dictionary = load_skill_dictionary()
    A = ahocorasick.Automaton()

    for category in dictionary.values():
        if not isinstance(category, list):
            continue

        for skill in category:
            canonical = skill.get("name")
            if not canonical:
                continue

            aliases = set(skill.get("aliases", []))
            aliases.add(canonical)

            for alias in aliases:
                alias_lower = alias.lower()
                # AhoCorasick stores (index, value) at each matched node.
                # We store both the alias and the canonical name.
                A.add_word(alias_lower, (alias_lower, canonical))

    A.make_automaton()
    return A

AUTOMATON = build_automaton()


#: Characters that continue a skill token rather than ending one.
#:
#: ``-`` is deliberately absent. It used to be here, which made every
#: hyphenated mention of a skill invisible: "Python-based", "React-Redux",
#: "Docker-compose" and "Kubernetes-managed" all extracted nothing at all,
#: because the hyphen on one side was read as "this match is part of a longer
#: word". A hyphen joins two words; it does not make them one.
#:
#: ``is_word_in_text`` in this same module has always disagreed — its
#: ``(?<!\w)…(?!\w)`` guard treats ``-`` as a boundary, since ``\w`` does not
#: include it. The two functions now agree.
#:
#: ``#`` and ``+`` stay, because they are the last character of a skill name
#: rather than a join: without them "C" matches inside "C#" and "C++".
SKILL_TOKEN_CHARS = ('_', '#', '+')


def is_word_boundary(text: str, start: int, end: int) -> bool:
    r"""
    Checks if a matched substring is bounded by non-word / non-skill characters.
    Prevents matching "react" inside "react.js" or "c" inside "c++".

    A hyphen counts as a boundary. The hyphenated skill names that exist in the
    dictionary — objective-c, react-native, scikit-learn — are matched as whole
    aliases by the automaton, and the shorter matches now sitting inside them
    ("c" in "objective-c") are discarded by :func:`_longest_matches` rather than
    by this function.
    """
    # Check preceding character
    if start > 0:
        prev_char = text[start - 1]
        if prev_char.isalnum() or prev_char in SKILL_TOKEN_CHARS:
            return False
        if prev_char == '.' and start - 1 > 0 and text[start - 2].isalnum():
            return False

    # Check following character
    if end < len(text):
        next_char = text[end]
        if next_char.isalnum() or next_char in SKILL_TOKEN_CHARS:
            return False
        if next_char == '.' and end + 1 < len(text) and text[end + 1].isalnum():
            return False

    return True


def _longest_matches(spans):
    """Drop any match that sits entirely inside a longer one.

    The automaton reports every alias it finds, including aliases nested in
    other aliases. While ``-`` blocked a match on either side that nesting was
    invisible, because the inner match was rejected as unbounded. Now that a
    hyphen is a boundary, "objective-c" also reports "c" and "react-native"
    also reports "react", so the overlap has to be resolved explicitly.

    Longest wins, which is the usual rule for this: "Objective-C" names one
    language, not two.

    ``spans`` is an iterable of ``(start, end, alias, canonical)`` with ``end``
    exclusive. Equal spans from different aliases are a genuine ambiguity in
    the dictionary rather than nesting, so the first is kept.
    """
    # Start ascending, then longest first, so a container is always visited
    # before anything nested inside it.
    ordered = sorted(spans, key=lambda span: (span[0], -(span[1] - span[0])))

    kept = []
    covered_to = -1
    for span in ordered:
        start, end = span[0], span[1]
        # Every span already visited starts at or before this one, so being
        # inside the furthest end reached means being inside one of them.
        if end <= covered_to:
            continue
        kept.append(span)
        covered_to = max(covered_to, end)

    return kept


def _scan(text: str):
    """Boundary-checked automaton hits in ``text`` as ``(start, end, alias, canonical)``."""
    spans = []
    # pyahocorasick returns (end_index, (alias_lower, canonical));
    # end_index is inclusive.
    for end_index, (alias_lower, canonical) in AUTOMATON.iter(text):
        start_index = end_index - len(alias_lower) + 1
        # Match complete words only, to prevent false positives
        # (e.g. "react" inside "reactive").
        if is_word_boundary(text, start_index, end_index + 1):
            spans.append((start_index, end_index + 1, alias_lower, canonical))
    return spans


def _iter_skill_matches(normalized_text: str):
    """Every non-nested, correctly bounded skill match in already-normalised text.

    Returns ``(start, end, alias_lower, canonical)`` tuples, ordered by where
    the match starts.

    The text is scanned twice. The second pass replaces every hyphen with a
    space, because a hyphen is also how people join the words of a
    multi-word skill name: the dictionary carries ``node js``,
    ``machine learning`` and ``deep learning`` as aliases, and someone writing
    "node-js", "machine-learning" or "deep-learning" means exactly those.
    Substituting one character for another keeps the string the same length,
    so offsets from both passes refer to the same positions and can be
    compared directly.

    Hyphenated skill names in the dictionary (objective-c, react-native,
    scikit-learn) still match on the first pass, and win over anything the
    second pass finds inside them because they are longer.
    """
    spans = _scan(normalized_text)

    if "-" in normalized_text:
        # Same length, so the spans are directly comparable.
        spans.extend(_scan(normalized_text.replace("-", " ")))

    return _longest_matches(spans)


def is_word_in_text(word: str, text: str) -> bool:
    """Check if word is bounded as a word in text."""
    pattern = r"(?<!\w)" + re.escape(word.lower()) + r"(?!\w)"
    return bool(re.search(pattern, text, re.IGNORECASE))


def get_skill_alias_map():
    """
    Build mappings:
    - alias_to_canonical: dict[str, str]
    - canonical_to_aliases: dict[str, set[str]]
    """
    dictionary = load_skill_dictionary()
    alias_to_canonical = {}
    canonical_to_aliases = {}

    for category in dictionary.values():
        if not isinstance(category, list):
            continue

        for skill in category:
            canonical = skill.get("name")
            if not canonical:
                continue

            canonical_lower = canonical.lower()
            aliases = set(a.lower() for a in skill.get("aliases", []))
            aliases.add(canonical_lower)

            canonical_to_aliases[canonical_lower] = aliases
            for alias in aliases:
                alias_to_canonical[alias] = canonical_lower

    return alias_to_canonical, canonical_to_aliases


def extract_skills(text: str):
    """
    Extract canonical skills from resume text using Aho-Corasick.

    Returns:
        list[str]
    """
    normalized = normalize_text(text)
    detected = [canonical for _, _, _, canonical in _iter_skill_matches(normalized)]

    # Preserve insertion order and remove duplicates.
    return list(dict.fromkeys(detected))


def extract_skills_detailed(text: str):
    """
    Extract canonical skills and the exact matched aliases/variants from text.

    Returns:
        dict[str, list[str]]: Map of canonical skill name to list of matched aliases in text.
    """
    normalized = normalize_text(text)
    matched_details = {}

    for _, _, alias_lower, canonical in _iter_skill_matches(normalized):
        if canonical not in matched_details:
            matched_details[canonical] = []
        if alias_lower not in matched_details[canonical]:
            matched_details[canonical].append(alias_lower)

    return matched_details


def match_skills_with_partial(required_skills, text, detected_skills=None):
    """
    Categorizes required skills into matched (full match), partial (near match), and missing.

    Returns:
        tuple[list[str], list[dict], list[str]]:
            - matched_skills: list of exact/full matched required skill strings
            - partial_skills: list of dicts with keys {"skill", "matched_variant", "note"}
            - missing_skills: list of truly missing required skill strings
    """
    if detected_skills is None:
        detected_skills = extract_skills(text)

    normalized_text = normalize_text(text)
    detailed_matches = extract_skills_detailed(text)
    alias_to_canonical, canonical_to_aliases = get_skill_alias_map()

    matched = []
    partial = []
    missing = []

    for req in required_skills:
        req_clean = req.strip()
        req_lower = req_clean.lower()
        canonical_req = alias_to_canonical.get(req_lower, req_lower)
        req_matched_exact = False

        # Check 1: Exact full match
        matched_aliases_in_text = detailed_matches.get(canonical_req, [])

        if matched_aliases_in_text:
            if req_lower in matched_aliases_in_text:
                req_matched_exact = True
            else:
                req_matched_exact = False
        elif is_word_in_text(req_lower, normalized_text):
            req_matched_exact = True
        elif req_lower in [s.lower() for s in detected_skills]:
            req_matched_exact = True

        if req_matched_exact:
            matched.append(req_clean)
            continue

        # Check 2: Near / Partial Match
        partial_info = None

        # (a) Found an alias in text for this required skill (e.g. React.js for React, or Postgres for PostgreSQL)
        if matched_aliases_in_text:
            variant = matched_aliases_in_text[0]
            if not is_explicit_non_match(req_lower, variant):
                variant_display = variant.upper() if variant in ("js", "ts", "css", "html", "sql") else variant.title()
                partial_info = {
                    "skill": req_clean,
                    "matched_variant": variant_display,
                    "note": f"Resume mentions '{variant_display}' (partial match for '{req_clean}')"
                }

        # (b) Or detected skills contain a canonical/alias of required skill
        if not partial_info:
            for det in detected_skills:
                det_lower = det.lower()
                canonical_det = alias_to_canonical.get(det_lower, det_lower)
                if is_explicit_non_match(req_lower, det_lower):
                    continue

                if canonical_req == canonical_det or req_lower in canonical_to_aliases.get(canonical_det, set()):
                    det_display = det.title()
                    partial_info = {
                        "skill": req_clean,
                        "matched_variant": det_display,
                        "note": f"Resume mentions '{det_display}' (partial match for '{req_clean}')"
                    }
                    break

        # (c) Formatting / String similarity check for custom skills or JD terms
        if not partial_info:
            req_alpha = re.sub(r"[^\w]", "", req_lower)
            for det in detected_skills:
                det_lower = det.lower()
                if is_explicit_non_match(req_lower, det_lower):
                    continue
                det_alpha = re.sub(r"[^\w]", "", det_lower)

                if len(req_alpha) >= 3 and len(det_alpha) >= 3:
                    # Substring or formatting match (e.g. "unittest" vs "unittesting")
                    if req_alpha in det_alpha or det_alpha in req_alpha:
                        partial_info = {
                            "skill": req_clean,
                            "matched_variant": det.title(),
                            "note": f"Resume mentions '{det.title()}' (formatting variant of '{req_clean}')"
                        }
                        break
                    
                    # High similarity ratio
                    ratio = difflib.SequenceMatcher(None, req_alpha, det_alpha).ratio()
                    if ratio >= 0.82:
                        partial_info = {
                            "skill": req_clean,
                            "matched_variant": det.title(),
                            "note": f"Resume mentions '{det.title()}' (near match for '{req_clean}')"
                        }
                        break

        # (d) Fallback check raw text for formatting variants (e.g. "React.js" when req is "React")
        if not partial_info and len(req_clean) >= 3:
            possible_variants = [f"{req_lower}.js", f"{req_lower}js", f"{req_lower} css", f"{req_lower} framework"]
            for pv in possible_variants:
                if is_word_in_text(pv, normalized_text) and not is_explicit_non_match(req_lower, pv):
                    partial_info = {
                        "skill": req_clean,
                        "matched_variant": pv,
                        "note": f"Resume mentions '{pv}' (near match for '{req_clean}')"
                    }
                    break

        if partial_info:
            partial.append(partial_info)
        else:
            missing.append(req_clean)

    return matched, partial, missing
