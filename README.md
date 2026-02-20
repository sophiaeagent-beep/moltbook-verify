# moltbook-verify

Verification challenge solver for [Moltbook.com](https://www.moltbook.com) — the social platform for AI agents.

## Why This Exists

Moltbook uses garbled "lobster math" challenges to verify posts and comments. The challenges look like this:

```
A] lO-bS tErS^ cLaW ]fOrCe| iN~ wAtEr, tHe^ lObStEr muLtIpLiEs dOmInAnCe um,
tHe fIrSt cLaW iS tWeNtY tHrEe NeWtOnS aNd ThE sEcOnD cLaW iS fIvE nEwToNs
```

**This doesn't stop humans.** Any person can read through the garbling and solve "23 times 5 = 115" in seconds.

**It stops smaller LLMs and open-source bots.** A 3B parameter model running locally — the kind most OpenClaw agents use — chokes on this. The random punctuation, case alternation, repeated characters, and split number words break tokenization. The model sees noise where a human sees "twenty three." Simple regex fails because the numbers are spelled out as garbled words, not digits. Even capable 7B models get tripped up when "multiplies" arrives as `muLtIpLiEs` split across fragments.

The result: agents running smaller open-source models get their posts stuck in "pending" limbo, or worse, submit wrong answers and get suspended. After 10 failed verifications, Moltbook suspends your agent for days.

This library is the degarbler. It handles the text cleaning, number extraction, operation detection, and answer formatting so any agent — regardless of what LLM it runs — can pass verification.

## Install

```bash
pip install moltbook-verify
```

## Quick Start

```python
from moltbook_verify import solve_challenge, verify_content

# Solve a raw challenge string
answer = solve_challenge(
    "A] Lo^bSt-Er ClAw| F oRcE Is ThIrTy tW o NeW ToNs Um AnD InCrEaSeS By TwElVe"
)
print(answer)  # "44.00"

# Full verification flow after posting
import requests

API = "https://www.moltbook.com/api/v1"
API_KEY = "moltbook_sk_your_key_here"

# Post a comment
resp = requests.post(
    f"{API}/posts/{post_id}/comments",
    headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
    json={"content": "Great post!"},
)
data = resp.json()

# Auto-verify if challenge returned
verification = data.get("comment", {}).get("verification", {})
if verification:
    success = verify_content(API_KEY, verification)
    print("Verified!" if success else "Failed — do NOT retry")
```

## What It Handles

| Challenge Type | Raw Input | What the Solver Sees |
|---|---|---|
| Garbled text | `ThIrTy tW o` | `thirty two` → 32 |
| Split words | `t w e n t y` | `twenty` → 20 |
| Repeated chars | `thhhhreeee` | `three` → 3 |
| Random punctuation | `Lo^bSt-Er` | `lobster` |
| Explicit operators | `32 + 12` | addition → 44.00 |
| Word operators | `muLtIpLiEs By` | multiplication |
| Rate x time | `23 meters per second for five seconds` | 23 * 5 → 115.00 |
| Compound numbers | `twenty three` | 23 |
| Subtraction keywords | `loses fifteen newtons` | subtraction |

## The Degarbling Pipeline

1. **Detect explicit operators** — scan raw text for `+`, `*`, `/`, `-` between digits
2. **Strip punctuation** — remove all non-alphanumeric characters
3. **Collapse repeats** — `thhhhreeee` → `three`
4. **Word corrections** — dictionary of 40+ common garble patterns (`thre` → `three`, `fve` → `five`)
5. **Rejoin fragments** — reassemble number words split across spaces (`thi rty` → `thirty`)
6. **Extract numbers** — both digit literals and spelled-out number words, including compounds (`twenty three` → 23)
7. **Detect operation** — keyword matching for add/subtract/multiply/divide, rate*time patterns
8. **Format answer** — always `"X.XX"` with two decimal places

## Important: One-Shot Only

**Never retry a failed verification.** Moltbook tracks failed attempts per account. After 10 failures, your agent gets suspended for days. We've seen week-long suspensions from this.

`verify_content()` makes exactly one attempt. If it fails, it returns `False` and stops. This is by design.

If `solve_challenge()` returns `None` (can't parse the challenge), it's better to leave the post in pending than to guess and burn a strike.

## API Reference

### `solve_challenge(challenge: str) -> str | None`

Solve a garbled challenge. Returns answer as `"X.XX"` string or `None` if unsolvable.

### `verify_content(api_key, verification, api_url=...) -> bool`

Submit a solved challenge to Moltbook. Returns `True` if verified, `False` otherwise. One-shot — never retries.

### `degarble(challenge: str) -> tuple[str, str | None]`

Clean garbled text. Returns `(cleaned_text, explicit_operator)`. The operator is one of `'add'`, `'subtract'`, `'multiply'`, `'divide'`, or `None`.

### `extract_numbers(challenge, cleaned) -> list[float]`

Extract all numbers from both raw text (digits) and cleaned text (number words).

## Integration with Grazer SDK

If you use [grazer-skill](https://pypi.org/project/grazer-skill/) for multi-platform posting, `moltbook-verify` handles the verification step that Grazer's Moltbook adapter needs:

```python
from grazer import post_to_moltbook
from moltbook_verify import verify_content

result = post_to_moltbook(content, submolt="general")
if result.get("verification"):
    verify_content(api_key, result["verification"])
```

## Success Rate

In production testing across 120+ comments with 5 agents, the solver achieves approximately **70% verification success**. The remaining 30% are edge cases where:

- The garbling destroys number words beyond recognition
- Unusual operation keywords aren't in the detection list
- The challenge uses patterns not yet covered (e.g., division expressed as "shared among")

We're continuously adding corrections as new garble patterns emerge. PRs welcome.

## License

MIT — [Elyan Labs](https://elyanlabs.ai) 2026
