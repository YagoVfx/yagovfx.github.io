
import re

# ── VFX exact match patterns ──────────────────────────
EXACT_PATTERNS = re.compile(
    r'\b('
    r'vfx\s*artist|visual\s*effects?\s*artist|fx\s*artist'
    r'|realtime\s*vfx|real[-\s]time\s*vfx|real[-\s]time\s*fx'
    r'|vfx\s*director|vfx\s*supervisor|vfx\s*lead|lead\s*vfx'
    r'|senior\s*vfx|junior\s*vfx|principal\s*vfx|technical\s*vfx'
    r'|senior\s*fx|junior\s*fx|lead\s*fx|principal\s*fx'
    r'|game\s*vfx|game\s*fx|gameplay\s*vfx|gameplay\s*fx'
    r'|niagara\s*artist|particle\s*artist'
    r')',
    re.IGNORECASE
)

# ── Possible match: title not exact but description hints ─
POSSIBLE_TITLE = re.compile(
    r'\b(vfx|visual\s*effects?|particle|fx\b|real[-\s]time\s*art)',
    re.IGNORECASE
)
POSSIBLE_DESC = re.compile(
    r'\b(niagara|unreal\s*engine\s*vfx|realtime\s*fx|real[-\s]time\s*fx|game\s*vfx|particle\s*system)',
    re.IGNORECASE
)

# ── Exclusions: clearly not game realtime VFX ─────────
EXCLUSIONS = re.compile(
    r'\b(compositor|compositing|nuke|flame|houdini\s*fx\s*td|motion\s*graphic|after\s*effects?\s*artist'
    r'|film\s*vfx|cinematic\s*vfx\s*director|post\s*production)\b',
    re.IGNORECASE
)


def classify_job(title: str, description: str = "") -> str | None:
    """Returns 'exactMatch', 'possibleMatch', or None."""
    if EXCLUSIONS.search(title):
        return None
    if EXACT_PATTERNS.search(title):
        return "exactMatch"
    if POSSIBLE_TITLE.search(title) and POSSIBLE_DESC.search(description):
        return "possibleMatch"
    return None


# ── Workplace detection ───────────────────────────────
REMOTE_RE = re.compile(r'\bremote\b', re.IGNORECASE)
HYBRID_RE = re.compile(r'\bhybrid\b', re.IGNORECASE)
ONSITE_RE = re.compile(r'\b(on[-\s]?site|in[-\s]?office|in\s+person)\b', re.IGNORECASE)

def detect_workplace(title: str, location: str, extra=None) -> str:
    combined = f"{title} {location} {extra or ''}"
    if REMOTE_RE.search(combined): return "remote"
    if HYBRID_RE.search(combined): return "hybrid"
    if ONSITE_RE.search(combined): return "onsite"
    return "unknown"


# ── Remote scope detection ────────────────────────────
SCOPE_MAP = [
    (re.compile(r'\b(worldwide|global|anywhere)\b', re.IGNORECASE), "Worldwide"),
    (re.compile(r'\b(europe|eu\b|emea)\b', re.IGNORECASE), "EU/Europe"),
    (re.compile(r'\bspain\b', re.IGNORECASE), "Spain"),
    (re.compile(r'\b(united\s*kingdom|uk\b)\b', re.IGNORECASE), "UK"),
    (re.compile(r'\b(united\s*states|usa?\b)\b', re.IGNORECASE), "US"),
    (re.compile(r'\bcanada\b', re.IGNORECASE), "Canada"),
]

def detect_remote_scope(title: str, location: str) -> str:
    combined = f"{title} {location}"
    for pattern, label in SCOPE_MAP:
        if pattern.search(combined):
            return label
    return "Unknown"
