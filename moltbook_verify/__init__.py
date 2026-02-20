"""
moltbook-verify — Verification challenge solver for Moltbook.com

Moltbook uses garbled "lobster math" challenges to verify agent posts/comments.
This module degarbles the text, extracts numbers, detects the operation, and
solves the challenge.

Usage:
    from moltbook_verify import solve_challenge, verify_content

    # Just solve a challenge string
    answer = solve_challenge(garbled_text)  # Returns "42.00" or None

    # Full flow: post comment + auto-verify
    result = verify_content(api_key, verification_dict)
"""

__version__ = "1.0.1"

import re
from collections import Counter

# ── Word corrections for degarbling ──────────────────────────────────────────

WORD_CORRECTIONS = {
    'thre': 'three', 'fourten': 'fourteen', 'fiften': 'fifteen',
    'sixten': 'sixteen', 'seventen': 'seventeen', 'eighten': 'eighteen',
    'nineten': 'nineteen', 'twety': 'twenty', 'thrty': 'thirty',
    'fty': 'fifty', 'sxty': 'sixty', 'sevnty': 'seventy',
    'eghty': 'eighty', 'nnety': 'ninety',
    'hundrd': 'hundred', 'thousnd': 'thousand',
    'lobstr': 'lobster', 'twnty': 'twenty', 'thrte': 'thirty',
    'fife': 'five', 'fve': 'five', 'hre': 'three',
    'hirty': 'thirty', 'irty': 'thirty', 'hirteen': 'thirteen',
    'ourteen': 'fourteen', 'ifteen': 'fifteen', 'ixteen': 'sixteen',
    'ighteen': 'eighteen', 'ineteen': 'nineteen',
    'wenty': 'twenty', 'enty': 'twenty',
    'orty': 'forty', 'ighty': 'eighty', 'inety': 'ninety',
    'sped': 'speed', 'gans': 'gains', 'gan': 'gain',
}

NUMBER_WORDS = {
    'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
    'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
    'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14, 'fifteen': 15,
    'sixteen': 16, 'seventeen': 17, 'eighteen': 18, 'nineteen': 19, 'twenty': 20,
    'thirty': 30, 'forty': 40, 'fifty': 50, 'sixty': 60, 'seventy': 70,
    'eighty': 80, 'ninety': 90, 'hundred': 100, 'thousand': 1000,
}

NUMBER_TARGETS = list(NUMBER_WORDS.keys()) + [
    'total', 'force', 'distance', 'lobster', 'newtons', 'meters', 'seconds',
    'minutes', 'centimeters', 'kilometers', 'increases', 'decreases',
    'accelerates', 'decelerates', 'molting', 'antenna', 'exerts',
]


def degarble(challenge: str) -> tuple:
    """Clean garbled verification text.

    Moltbook inserts random punctuation, case changes, and letter repetitions
    into challenge text. This function cleans it to readable English.

    Args:
        challenge: Raw garbled challenge text from Moltbook API

    Returns:
        Tuple of (cleaned_text, explicit_operator_or_None)
        explicit_operator is one of: 'add', 'subtract', 'multiply', 'divide'
    """
    # Detect explicit math operators in raw text (before cleaning)
    explicit_op = None
    if re.search(r'\d\s*\+\s*\d', challenge):
        explicit_op = 'add'
    elif re.search(r'\d\s*[*\u00d7]\s*\d', challenge) or re.search(r'[*\u00d7]', challenge):
        explicit_op = 'multiply'
    elif re.search(r'\d\s*/\s*\d', challenge):
        explicit_op = 'divide'
    elif re.search(r'\d\s+-\s+\d', challenge):
        explicit_op = 'subtract'

    # Strip non-alphanumeric, lowercase, collapse repeated chars
    clean = re.sub(r"[^a-zA-Z0-9\s]", "", challenge).lower()
    degarbled = re.sub(r'(.)\1{2,}', r'\1', clean)
    degarbled = re.sub(r'(.)\1+', r'\1', degarbled)

    # Apply word corrections
    words = degarbled.split()
    fixed_words = [WORD_CORRECTIONS.get(w, w) for w in words]

    # Rejoin space-split number fragments (e.g., "thi rty" → "thirty")
    rejoined = []
    i = 0
    while i < len(fixed_words):
        matched = False
        for span in [5, 4, 3, 2]:
            if i + span <= len(fixed_words):
                combined = ''.join(fixed_words[i:i + span])
                if combined in NUMBER_TARGETS:
                    rejoined.append(combined)
                    i += span
                    matched = True
                    break
                corrected = WORD_CORRECTIONS.get(combined, combined)
                if corrected in NUMBER_TARGETS:
                    rejoined.append(corrected)
                    i += span
                    matched = True
                    break
        if not matched:
            rejoined.append(fixed_words[i])
            i += 1

    return ' '.join(rejoined), explicit_op


def extract_numbers(challenge: str, cleaned: str) -> list:
    """Extract numbers from both raw and cleaned challenge text.

    Handles digit literals (e.g., "32") and number words (e.g., "thirty two").

    Returns:
        List of floats found in the text.
    """
    # Find digit-based numbers in raw text
    digit_nums = re.findall(r'\b(\d+(?:\.\d+)?)\b', challenge)

    # Find word-based numbers in cleaned text
    words = cleaned.split()
    found = []
    i = 0
    while i < len(words):
        w = words[i].lower()
        if w in NUMBER_WORDS:
            val = NUMBER_WORDS[w]
            # Handle compound numbers like "thirty two" = 32
            if i + 1 < len(words) and words[i + 1].lower() in NUMBER_WORDS:
                next_val = NUMBER_WORDS[words[i + 1].lower()]
                if val >= 20 and next_val < 10:
                    val += next_val
                    i += 1
                elif val >= 100 and next_val < 100:
                    val += next_val
                    i += 1
            found.append(float(val))
        i += 1

    # Add digit numbers
    for n in digit_nums:
        try:
            found.append(float(n))
        except ValueError:
            pass

    return found


def solve_challenge(challenge: str) -> str | None:
    """Solve a garbled Moltbook verification challenge.

    This is the main entry point. Pass the raw `challenge_text` from the
    Moltbook API verification response.

    Args:
        challenge: Raw garbled challenge text

    Returns:
        Answer as "X.XX" string, or None if unsolvable.

    Example:
        >>> solve_challenge("A] Lo^bSt-Er ClAw| F oRcE Is ThIrTy tW o NeW ToNs...")
        "44.00"
    """
    cleaned, explicit_op = degarble(challenge)

    found_nums = extract_numbers(challenge, cleaned)

    # Deduplicate (preserving order), handling same-number patterns
    same_num_pattern = re.search(r'(\d+)\s*[+\-*/\u00d7]\s*\1', challenge)
    if not same_num_pattern and len(found_nums) >= 2:
        num_counts = Counter(found_nums)
        if any(c >= 2 for c in num_counts.values()) and explicit_op:
            same_num_pattern = True

    if same_num_pattern:
        unique_nums = found_nums[:2] if len(found_nums) >= 2 else found_nums
    else:
        seen = set()
        unique_nums = []
        for n in found_nums:
            if n not in seen:
                seen.add(n)
                unique_nums.append(n)

    if len(unique_nums) < 2:
        return None

    # Priority 1: Explicit operator from raw text (+ - * /)
    if explicit_op:
        a, b = unique_nums[0], unique_nums[1]
        if explicit_op == 'add':
            result = a + b
        elif explicit_op == 'subtract':
            result = a - b
        elif explicit_op == 'multiply':
            result = a * b
        elif explicit_op == 'divide':
            result = a / b if b != 0 else 0
        return f"{result:.2f}"

    text = cleaned

    # Priority 2: Rate * time pattern
    rate_words = ['per second', 'per sec', 'per minute', 'per min', 'per hour',
                  'cm per', 'meters per']
    subtract_words = ['slow', 'slows', 'reduce', 'reduces', 'resistance',
                      'decelerate', 'loses', 'drops', 'decreases', 'minus',
                      'subtract', 'less', 'gave away', 'spent', 'remaining',
                      'left over']
    has_rate = any(w in text for w in rate_words)
    has_subtract = any(w in text for w in subtract_words)
    duration_match = re.search(
        r'\bfor\s+(\d+|' + '|'.join(
            w for w in NUMBER_WORDS if NUMBER_WORDS[w] <= 100
        ) + r')\s+(seconds?|minutes?|hours?|secs?|mins?)\b', text)

    if has_rate and duration_match and not has_subtract:
        rate_val = unique_nums[0]
        dur_str = duration_match.group(1)
        time_val = (float(dur_str) if dur_str.isdigit()
                    else float(NUMBER_WORDS.get(dur_str, 0)))
        if time_val:
            return f"{rate_val * time_val:.2f}"

    # Priority 3: Keyword-based operation detection
    a, b = unique_nums[0], unique_nums[1]

    if 'each' in text:
        result = a * b
    elif any(w in text for w in ['plus', 'added', 'adds', 'more than',
             'additional', 'gained', 'gains', 'gain', 'accelerates',
             'faster', 'increases', 'speeds', 'more', 'earns', 'collects',
             'gathers', 'receives', 'gets']):
        result = a + b
    elif any(w in text for w in subtract_words):
        result = a - b
    elif any(w in text for w in ['times', 'multiply', 'multiplied', 'multiplies', 'multi']):
        result = a * b
    elif any(w in text for w in ['divided', 'divide', 'split',
             'shared equally']):
        result = a / b if b != 0 else 0
    elif any(w in text for w in ['total', 'combined', 'altogether', 'sum',
             'how many']):
        result = sum(unique_nums)
    else:
        result = sum(unique_nums)

    return f"{result:.2f}"


def verify_content(api_key: str, verification: dict,
                   api_url: str = "https://www.moltbook.com/api/v1/verify"
                   ) -> bool:
    """Solve and submit a verification challenge.

    IMPORTANT: One-shot only. If the answer is wrong, this function returns
    False and does NOT retry. Repeated wrong answers lead to account suspension.

    Args:
        api_key: Moltbook API key (moltbook_sk_...)
        verification: Dict with 'challenge_text' and 'verification_code'
        api_url: Verification endpoint URL

    Returns:
        True if verified, False otherwise.
    """
    import requests

    challenge = verification.get("challenge_text", "")
    code = verification.get("verification_code", "")

    if not challenge or not code:
        return False

    answer = solve_challenge(challenge)
    if answer is None:
        return False

    resp = requests.post(
        api_url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={"verification_code": code, "answer": answer},
        timeout=15,
    )

    data = resp.json()
    return bool(data.get("success"))
