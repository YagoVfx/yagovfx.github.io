import re

EXACT_PATTERNS = re.compile(
    r'\b('
    r'vfx\s*artist|visual\s*effects?\s*artist|fx\s*artist'
    r'|realtime\s*vfx|real[-\s]time\s*vfx|real[-\s]time\s*fx'
    r'|vfx\s*director|vfx\s*supervisor|vfx\s*lead|lead\s*vfx'
    r'|senior\s*vfx|junior\s*vfx|principal\s*vfx|technical\s*vfx'
    r'|senior\s*fx|junior\s*fx|lead\s*fx|principal\s*fx'
    r'|game\s*vfx|game\s*fx|gameplay\s*vfx|gameplay\s*fx'
    r'|niagara\s*artist|particle\s*artist'
    # Added per user report: "Effects Artist" (no vfx/fx abbreviation at
    # all) is a very common real-world title on several studios' own
    # career sites (Ubisoft, Massive, etc.) and was previously invisible
    # to this filter entirely — not even possibleMatch, just silently
    # dropped, because POSSIBLE_TITLE below still required "fx"/"vfx" too.
    r'|senior\s*effects\s*artist|junior\s*effects\s*artist|lead\s*effects\s*artist'
    r'|principal\s*effects\s*artist|effects\s*artist|effects\s*td|fx\s*td|vfx\s*td'
    r'|environment\s*fx\s*artist|creature\s*fx\s*artist|character\s*fx\s*artist'
    r'|cloth\s*fx\s*artist|rigid\s*body\s*fx'
    r')',
    re.IGNORECASE
)

POSSIBLE_TITLE = re.compile(
    r'\b(vfx|visual\s*effects?|particle|fx\b|real[-\s]time\s*art|effects)',
    re.IGNORECASE
)
POSSIBLE_DESC = re.compile(
    r'\b(niagara|unreal\s*engine\s*vfx|realtime\s*fx|real[-\s]time\s*fx|game\s*vfx|particle\s*system)',
    re.IGNORECASE
)

EXCLUSIONS = re.compile(
    r'\b(compositor|compositing|nuke|flame|houdini\s*fx\s*td|motion\s*graphic|after\s*effects?\s*artist'
    r'|film\s*vfx|cinematic\s*vfx\s*director|post\s*production)\b',
    re.IGNORECASE
)

BARE_VFX_RE = re.compile(r'\bvfx\b', re.IGNORECASE)

# "Remote" en el título no significa "remoto desde cualquier sitio": muchas
# ofertas son remote-pero-solo-dentro-de-un-país, y eso solo se sabe por
# cómo está redactada la descripción (no hay un campo aparte para esto en
# ninguno de los ATS que leemos). Cubre las formas más comunes en inglés;
# es heurístico a propósito — mejor descartar una oferta válida rara vez
# que dejar pasar basura que luego da "not available in your region".
US_ONLY_RE = re.compile(
    r'\b(u\.?s\.?\s*citizens?\s*only|us[-\s]based\s*only'
    r'|must\s*be\s*(?:currently\s*)?(?:based|located|residing)\s*in\s*the\s*(?:u\.?s\.?|united\s*states)'
    r'|must\s*reside\s*in\s*the\s*(?:u\.?s\.?|united\s*states)'
    r'|authorized\s*to\s*work\s*in\s*the\s*u\.?s\.?\s*without\s*(?:visa\s*)?sponsorship'
    r'|(?:no|unable\s*to\s*provide)\s*(?:visa\s*)?sponsorship'
    r'|this\s*(?:role|position|job)\s*is\s*(?:only\s*)?(?:open|available)\s*to\s*(?:u\.?s\.?|united\s*states)\s*(?:residents|candidates)'
    r'|u\.?s\.?\s*work\s*authorization\s*required'
    r')\b', re.IGNORECASE
)
UK_ONLY_RE = re.compile(
    r'\b(uk\s*residents?\s*only|u\.?k\.?\s*citizens?\s*only'
    r'|must\s*be\s*(?:based|located)\s*in\s*the\s*uk\b'
    r'|right\s*to\s*work\s*in\s*the\s*uk\s*(?:is\s*)?required'
    r')\b', re.IGNORECASE
)

def is_region_restricted(text):
    """True si el texto deja claro que la oferta está cerrada a un país
    fuera de España/UE (EEUU o Reino Unido en sus formas más habituales)."""
    return bool(US_ONLY_RE.search(text) or UK_ONLY_RE.search(text))

def classify_job(title, description=""):
    if EXCLUSIONS.search(title):
        return None
    if is_region_restricted(f"{title} {description}"):
        return None
    if EXACT_PATTERNS.search(title):
        return "exactMatch"
    if POSSIBLE_TITLE.search(title) and POSSIBLE_DESC.search(description):
        return "possibleMatch"
    if BARE_VFX_RE.search(title):
        return "possibleMatch"
    return None

REMOTE_RE = re.compile(r'\bremote\b', re.IGNORECASE)
HYBRID_RE = re.compile(r'\bhybrid\b', re.IGNORECASE)
ONSITE_RE = re.compile(r'\b(on[-\s]?site|in[-\s]?office|in\s+person)\b', re.IGNORECASE)

def detect_workplace(title, location, extra=None):
    combined = f"{title} {location} {extra or ''}"
    if REMOTE_RE.search(combined): return "remote"
    if HYBRID_RE.search(combined): return "hybrid"
    if ONSITE_RE.search(combined): return "onsite"
    return "unknown"

SCOPE_MAP = [
    (re.compile(r'\b(worldwide|global|anywhere)\b', re.IGNORECASE), "Worldwide"),
    (re.compile(r'\b(europe|eu\b|emea)\b', re.IGNORECASE), "EU/Europe"),
    (re.compile(r'\bspain\b', re.IGNORECASE), "Spain"),
    (re.compile(r'\b(united\s*kingdom|uk\b)\b', re.IGNORECASE), "UK"),
    (re.compile(r'\b(united\s*states|usa?\b)\b', re.IGNORECASE), "US"),
    (re.compile(r'\bcanada\b', re.IGNORECASE), "Canada"),
]

def detect_remote_scope(title, location):
    combined = f"{title} {location}"
    for pattern, label in SCOPE_MAP:
        if pattern.search(combined):
            return label
    return "Unknown"
