"""
Smart content moderation with ML-like detection.

Layers:
1. Exact/substring match (existing behavior)
2. Elongation collapsing — "fuuuuck" → "fuck", "tanginamoooo" → "tanginamo"
3. Leetspeak normalization — "f*ck" → "fuck", "sh1t" → "shit"
4. Fuzzy matching — catch misspellings within edit distance 2
5. Toxic phrase detection — threats, harassment, negativity patterns
"""

import re
from difflib import SequenceMatcher

# --- Layer 2: Elongation Collapsing ---

def collapse_repeated_chars(text):
    """Collapse runs of 3+ identical characters to 1.
    'fuuuuck' → 'fuck', 'tanginamoooo' → 'tanginamo', 'shiiit' → 'shit'
    Also handles 2+ for short words.
    """
    # First pass: collapse 3+ to 1
    collapsed = re.sub(r'(.)\1{2,}', r'\1', text)
    return collapsed


def collapse_to_two(text):
    """Collapse 2+ identical chars to 1 (more aggressive)."""
    return re.sub(r'(.)\1+', r'\1', text)


# --- Layer 3: Leetspeak Normalization ---

LEET_MAP = {
    '0': 'o', '1': 'i', '3': 'e', '4': 'a', '5': 's',
    '7': 't', '8': 'b', '9': 'g',
    '@': 'a', '$': 's', '!': 'i', '+': 't',
    '*': 'u', '#': 'h', '.': '', '-': '', '_': '',
    '(': 'c', ')': '', '|': 'l', '/': 'l', '\\': 'l',
    '{': 'c', '}': '',
}


def normalize_leetspeak(text):
    """Replace common leetspeak substitutions."""
    result = []
    for ch in text:
        result.append(LEET_MAP.get(ch, ch))
    return ''.join(result)


# --- Layer 4: Fuzzy Matching ---

# Common short words that fuzzy-match profanity but are innocent
_FUZZY_WHITELIST = frozenset({
    'duck', 'ducks', 'ducking', 'luck', 'lucky', 'truck', 'struck', 'stuck',
    'shift', 'shirt', 'ship', 'ships', 'shut', 'shot', 'shop', 'shin', 'shed',
    'birch', 'batch', 'beach', 'bench', 'pitch', 'witch', 'ditch', 'hitch', 'rich',
    'bass', 'mass', 'pass', 'class', 'glass', 'grass',
    'pick', 'sick', 'kick', 'tick', 'thick', 'trick', 'brick', 'click',
    'put', 'puts', 'pull', 'push', 'pulse', 'pure', 'punt',
    'tang', 'tango', 'tank', 'tanks',
    'ago', 'sage', 'page', 'cage', 'wage',
    # Filipino common words that false-match against Hindi/other profanity
    'ganda', 'maganda', 'gandang', 'kagandahan', 'pagkaganda',
    'andi', 'randi', 'grandi', 'branding', 'randim',
    'lorem', 'ipsum', 'dolor', 'amet', 'adipi', 'consectetur',
})


def is_fuzzy_match(text, term, threshold=0.88):
    """Check if any word in text fuzzy-matches the term.
    Uses SequenceMatcher ratio. Skips matches that hit whitelisted words.
    Only matches against individual words to avoid false positives from
    substring windows across word boundaries.
    """
    term_len = len(term)
    if term_len < 5:
        return False  # too short for fuzzy matching — high false-positive rate

    # Split into words and check each word individually
    words = text.split() if ' ' in text else [text]
    for word in words:
        if word in _FUZZY_WHITELIST:
            continue
        if len(word) < term_len - 1 or len(word) > term_len + 2:
            continue
        ratio = SequenceMatcher(None, word, term).ratio()
        if ratio >= threshold:
            return True
    return False


# --- Layer 5: Toxic Phrase Detection ---

# Patterns that indicate toxic/negative content regardless of specific banned words.
# These are regex patterns matched against normalized text.
TOXIC_PATTERNS = [
    # Direct threats
    r'\b(?:i will|ima|i\'?m gonna|we will|we\'?ll)\s+(?:kill|hurt|beat|stab|shoot|destroy|end)\s+(?:you|u|him|her|them)\b',
    r'\b(?:kill|murder|stab|shoot)\s+(?:yourself|urself|your\s*self)\b',
    # Self-harm encouragement
    r'\b(?:go\s+)?(?:kill|hang|cut)\s+(?:yourself|urself|your\s*self)\b',
    r'\bkys\b',
    # Dehumanization
    r'\b(?:you(?:\'?re| are)\s+(?:worthless|garbage|trash|nothing|pathetic|disgusting|useless))\b',
    r'\b(?:nobody\s+(?:loves|likes|cares\s+about|wants)\s+(?:you|u))\b',
    # Slurs and hate speech patterns (common English)
    r'\b(?:fag|faggot|dyke|tranny|retard|retarded|nigger|nigga|chink|spic|kike|wetback)\b',
    # Filipino toxic patterns
    r'\b(?:bobo\s*ka|tanga\s*ka|gago\s*ka|gaga\s*ka|ulol\s*ka)\b',
    r'\b(?:walang\s+kwenta|walang\s+silbi|mag\s*pa\s*kamatay)\b',
    r'\b(?:hayop\s+ka|hayup\s+ka|animal\s+ka)\b',
    r'\b(?:pangit\s*(?:mo|ka)|ang\s+pangit\s*(?:mo|ka))\b',
    # Harassment
    r'\b(?:i\s+hope\s+(?:you|u)\s+(?:die|rot|suffer|fail))\b',
    r'\b(?:(?:you|u)\s+(?:deserve|should)\s+(?:to\s+)?(?:die|suffer|rot|be\s+killed))\b',
]

_COMPILED_TOXIC = [re.compile(p, re.IGNORECASE) for p in TOXIC_PATTERNS]


def detect_toxic_pattern(text):
    """Check text against toxic phrase patterns. Returns matched pattern or None."""
    for pattern in _COMPILED_TOXIC:
        match = pattern.search(text)
        if match:
            return match.group(0)
    return None


# --- Main Entry Point ---

def smart_profanity_check(content, forbidden_terms):
    """Multi-layer profanity and toxicity detection.

    Args:
        content: Raw user input text
        forbidden_terms: List of normalized forbidden terms (from load_forbidden_terms)

    Returns:
        tuple: (matched_term_or_phrase, detection_layer) or (None, None)
        detection_layer is one of: 'exact', 'elongation', 'leetspeak', 'fuzzy', 'toxic'
    """
    if not content or not content.strip():
        return None, None

    # Normalize the input
    lowered = content.lower()
    # Remove non-word chars but keep spaces
    normalized = re.sub(r'[^\w\s]+', '', lowered, flags=re.UNICODE)
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    stripped = re.sub(r'\s+', '', normalized)

    # Prepare variant texts
    collapsed_text = collapse_repeated_chars(normalized)
    collapsed_stripped = collapse_repeated_chars(stripped)
    aggressive_collapsed = collapse_to_two(normalized)
    aggressive_stripped = collapse_to_two(stripped)
    leet_normalized = normalize_leetspeak(lowered)
    leet_normalized = re.sub(r'[^\w\s]+', '', leet_normalized, flags=re.UNICODE)
    leet_normalized = re.sub(r'\s+', ' ', leet_normalized).strip()
    leet_stripped = re.sub(r'\s+', '', leet_normalized)
    leet_collapsed = collapse_to_two(leet_stripped)

    for term in forbidden_terms:
        if not term:
            continue
        term_stripped = re.sub(r'\s+', '', term)
        term_collapsed = collapse_to_two(term)
        term_stripped_collapsed = collapse_to_two(term_stripped)

        # Layer 1: Exact substring
        if term in normalized or term_stripped in stripped:
            return term, 'exact'

        # Layer 2: Elongation — collapse repeated chars then match
        if term in collapsed_text or term_stripped in collapsed_stripped:
            return term, 'elongation'
        if term_collapsed in aggressive_collapsed or term_stripped_collapsed in aggressive_stripped:
            return term, 'elongation'

        # Layer 3: Leetspeak — normalize leet then match
        if term in leet_normalized or term_stripped in leet_stripped:
            return term, 'leetspeak'
        if term_collapsed in leet_collapsed or term_stripped_collapsed in leet_collapsed:
            return term, 'leetspeak'

        # Layer 4: Fuzzy — catch misspellings (terms >= 5 chars only)
        if len(term_stripped) >= 5:
            if is_fuzzy_match(aggressive_collapsed, term_stripped_collapsed):
                return term, 'fuzzy'
            # Also fuzzy-match against leetspeak-normalized text
            if is_fuzzy_match(leet_collapsed, term_stripped_collapsed):
                return term, 'fuzzy'

    # Layer 5: Toxic phrase patterns (language-level toxicity)
    toxic_match = detect_toxic_pattern(normalized)
    if toxic_match:
        return toxic_match, 'toxic'

    # Also check against leet-normalized text for toxic patterns
    toxic_match_leet = detect_toxic_pattern(leet_normalized)
    if toxic_match_leet:
        return toxic_match_leet, 'toxic'

    return None, None
