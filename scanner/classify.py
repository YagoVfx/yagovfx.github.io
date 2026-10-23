"""
Clasificación determinista y EXPLICABLE de una oferta (sin IA).

Principios (ver VFX_Job_Tracker_V2_Especificacion_Claude.md §2-§3):
  * Desconocido NO es evidencia negativa: se marca "unknown" y solo penaliza
    un poco el ranking; nunca se convierte en rechazo automático.
  * La elegibilidad geográfica (¿puedo trabajar desde España?) es independiente
    del contrato (¿asalariado indefinido?) y de la jornada. Nunca se mezclan.
  * Cada decisión guarda su motivo/evidencia (campos *Reason / *Evidence) para
    poder enseñar «Por qué aparece aquí» sin inventar nada.
  * Los valores de negocio son siempre minúsculas y de un conjunto cerrado.

Campos que añade enrich_job() (todos planos, fáciles de consumir desde la web
y desde una futura app Flutter):
  spainEligibility  confirmed | possible | unknown | restricted | contradiction
  spainReason       texto breve en español
  contractType      employee | freelance | temporary | unknown
  contractEvidence  fragmento literal que lo justifica ("" si unknown)
  hours             full | part | unknown
  seniority         junior | mid | senior | lead | unknown
  role              vfx | tech-vfx | technical-artist | other
  engines           lista: unreal, unity, ...
  verification      verified | unverified
  sourceKind        ats | official-site | aggregator | signal
  compatibility     compatible | review | incompatible
  relevance         {"score": int, "reasons": [str, ...]}
"""
from __future__ import annotations

import re

from .filters import US_ONLY_RE, UK_ONLY_RE

# ───────────────────────── elegibilidad España ─────────────────────────

_REMOTE = re.compile(r"\b(remote|remoto|teletrabajo|work\s*from\s*home|home[-\s]?office|telecommut\w*)\b", re.I)
_SPAIN = re.compile(r"\b(spain|españa|espana|spanish\s+resident)\b", re.I)
_EU_WIDE = re.compile(r"\b(europe|european\s+union|eu|emea|eea|schengen)\b", re.I)
_WORLD = re.compile(r"\b(worldwide|global(?:ly)?|anywhere|work\s*from\s*anywhere|across\s+time\s*zones)\b", re.I)
# Alcance remoto explícitamente limitado a un país NO compatible.
_REMOTE_US = re.compile(r"\b(remote|remoto)\b[^.\n]{0,25}\b(u\.?s\.?a?|united\s*states)\b|\b(u\.?s\.?a?|united\s*states)\b[^.\n]{0,25}\b(remote|remoto)\b", re.I)
_REMOTE_UK = re.compile(r"\b(remote|remoto)\b[^.\n]{0,25}\b(u\.?k\.?|united\s*kingdom)\b|\b(u\.?k\.?|united\s*kingdom)\b[^.\n]{0,25}\b(remote|remoto)\b", re.I)
_REMOTE_CA = re.compile(r"\b(remote|remoto)\b[^.\n]{0,25}\bcanada\b|\bcanada\b[^.\n]{0,25}\b(remote|remoto)\b", re.I)
_OTHER_RESTRICT = re.compile(
    r"(must\s*(?:be\s*)?(?:based|located|reside|residing)\s*in\s*(?:canada|australia|india|brazil|japan|korea|singapore))"
    r"|((?:canadian|australian)\s*(?:residents?|citizens?)\s*only)", re.I)
_SPAIN_OK = re.compile(
    r"(work(?:ing)?\s*(?:remotely\s*)?from\s*spain|remote\s*(?:within|in|from)\s*spain"
    r"|(?:based|located|living|residing)\s*in\s*spain[^.\n]{0,30}remote"
    r"|(?:spain|españa)\s*[-–(/,]?\s*(?:100\s*%\s*)?remote|remote\s*[-–(/,]?\s*(?:spain|españa)"
    r"|teletrabajo\s*(?:desde|en)\s*españa)", re.I)


_SCOPE_RESTRICTED = {"us": "EE. UU.", "uk": "Reino Unido", "canada": "Canadá"}
_SCOPE_POSSIBLE = {"eu/europe": "UE/Europa", "worldwide": "worldwide/global"}


def classify_spain_eligibility(title: str, location: str, description: str = "",
                               workplace: str = "unknown", remote_scope: str = "") -> tuple[str, str]:
    """→ (estado, motivo). Solo evidencia explícita; la ubicación genérica o el
    título por sí solos NO confirman nada."""
    head = f"{title} {location}"
    text = f"{head} {description or ''}"

    restricted = None
    if US_ONLY_RE.search(text):
        restricted = "El texto limita la oferta a residentes/autorizados en EE. UU."
    elif UK_ONLY_RE.search(text):
        restricted = "El texto limita la oferta a residentes en Reino Unido."
    elif _OTHER_RESTRICT.search(text):
        restricted = "El texto limita la oferta a otro país fuera de España."
    elif _REMOTE_US.search(head):
        restricted = "Remoto limitado a EE. UU. según título/ubicación."
    elif _REMOTE_UK.search(head):
        restricted = "Remoto limitado a Reino Unido según título/ubicación."
    elif _REMOTE_CA.search(head):
        restricted = "Remoto limitado a Canadá según título/ubicación."

    scope = (remote_scope or "").strip().lower()
    if not restricted and workplace == "remote" and scope in _SCOPE_RESTRICTED:
        restricted = f"Remoto limitado a {_SCOPE_RESTRICTED[scope]} según el alcance detectado en la fuente."

    positive = None
    if workplace == "remote" and scope == "spain":
        positive = ("confirmed", "Remoto con alcance España indicado por la fuente.")
    elif workplace == "remote" and scope in _SCOPE_POSSIBLE:
        positive = ("possible", f"Remoto {_SCOPE_POSSIBLE[scope]}: no garantiza contratación en España.")
    elif _SPAIN_OK.search(text) or (_REMOTE.search(head) and _SPAIN.search(head)):
        positive = ("confirmed", "La oferta indica explícitamente remoto en/desde España.")
    elif workplace == "remote" and _SPAIN.search(location or ""):
        positive = ("confirmed", "Remoto con ubicación en España indicada por la fuente.")
    elif _REMOTE.search(text) and _WORLD.search(text):
        positive = ("possible", "Remoto 'worldwide/global': no garantiza contratación en España.")
    elif _REMOTE.search(text) and _EU_WIDE.search(text):
        positive = ("possible", "Remoto UE/Europa: no garantiza contratación en España.")

    if restricted and positive:
        return "contradiction", f"Señales incompatibles: {positive[1]} Pero: {restricted}"
    if restricted:
        return "restricted", restricted
    if positive:
        return positive
    return "unknown", "La fuente no aclara si se puede trabajar desde España."


# ─────────────────────────── contrato y jornada ───────────────────────────

_FREELANCE = re.compile(r"\b(freelance|freelancer|b2b|self[-\s]?employed|aut[óo]nomo|independent\s+contractor|contractor\s+basis|1099|per[-\s]?diem|invoice\s+basis|service\s+agreement)\b", re.I)
_TEMPORARY = re.compile(r"\b(fixed[-\s]?term|temporary|temporal|maternity\s+cover|parental\s+leave\s+cover|duraci[óo]n\s+determinada|\d+[-\s]?month\s+(?:contract|position)|contract\s+(?:role|position)|short[-\s]?term\s+contract|seasonal)\b", re.I)
_EMPLOYEE = re.compile(r"\b(permanent|indefinido|open[-\s]?ended|contrato\s+indefinido|permanent\s+(?:contract|position|role|employee))\b", re.I)
_FULL = re.compile(r"\b(full[-\s]?time|jornada\s+completa|tiempo\s+completo)\b", re.I)
_PART = re.compile(r"\b(part[-\s]?time|media\s+jornada|jornada\s+parcial|tiempo\s+parcial)\b", re.I)


# «full-time or contract», «flexible engagement»…: la fuente deja abierta la forma de contratación.
# No es empleo ni freelance acreditado: se queda «unknown», pero con la frase como evidencia.
_AMBIGUOUS_PATTERNS = [re.compile(p, re.I) for p in (
    r"\bfull[-\s]?time\s+or\s+contract\b", r"\bcontract\s+or\s+full[-\s]?time\b",
    r"\bcontractor\s+or\s+employee\b", r"\bflexible\s+engagement\b")]


class _AmbiguousSearch:
    """Busca por orden de prioridad (la frase más informativa primero, no la que aparezca antes)."""
    def search(self, text):
        for rx in _AMBIGUOUS_PATTERNS:
            m = rx.search(text or "")
            if m:
                return m
        return None


_AMBIGUOUS = _AmbiguousSearch()


def classify_contract(text: str) -> tuple[str, str]:
    """→ (tipo, evidencia). 'full-time' NO implica empleo asalariado; solo
    'permanent/indefinido' lo acredita. Si hay señales cruzadas se prioriza la
    más restrictiva para el objetivo (freelance > temporal > empleo)."""
    t = text or ""
    for kind, rx in (("freelance", _FREELANCE), ("temporary", _TEMPORARY), ("employee", _EMPLOYEE)):
        m = rx.search(t)
        if m:
            return kind, m.group(0)
    m = _AMBIGUOUS.search(t)
    if m:
        return "unknown", m.group(0)
    return "unknown", ""


def classify_hours(text: str) -> str:
    t = text or ""
    if _AMBIGUOUS.search(t):
        return "unknown"        # «full-time or contract» no acredita jornada completa
    if _PART.search(t):
        return "part"
    if _FULL.search(t):
        return "full"
    return "unknown"


# ─────────────────────── seniority, rol, motor ───────────────────────

def detect_seniority(title: str) -> str:
    t = title or ""
    if re.search(r"\b(lead|principal|head\s+of|director|supervisor|staff)\b", t, re.I):
        return "lead"
    if re.search(r"\b(senior|sr\.?)\b", t, re.I):
        return "senior"
    if re.search(r"\b(junior|jr\.?|intern|trainee|graduate|entry)\b", t, re.I):
        return "junior"
    if re.search(r"\b(mid|intermediate|ii)\b", t, re.I):
        return "mid"
    return "unknown"


_NON_ARTIST = re.compile(r"\b(producer|coordinator|manager|recruit\w*|assistant|executive|accountant|sales|marketing|payroll|legal|hr|talent|administrator|office)\b", re.I)


def detect_role(title: str, description: str = "") -> str:
    t = title or ""
    # «VFX Producer», «VFX Coordinator»... no son puestos de artista VFX.
    if _NON_ARTIST.search(t) and not re.search(r"\bartist\b", t, re.I):
        return "other"
    if re.search(r"\b(technical|tech)\s*(vfx|fx|effects)\b|\b(vfx|fx)\s*(td|technical\s*artist)\b|\beffects\s*td\b", t, re.I):
        return "tech-vfx"
    if re.search(r"\b(vfx|fx|effects|particle|niagara|visual\s*effects?)\b", t, re.I):
        return "vfx"
    if re.search(r"\btechnical\s*artist\b|\btech\s*artist\b", t, re.I):
        return "technical-artist"
    return "other"


_ENGINES = (
    ("unreal", re.compile(r"\b(unreal(?:\s*engine)?|ue[45]|niagara)\b", re.I)),
    ("unity", re.compile(r"\bunity(?:\s*3d)?\b|\bvfx\s*graph\b", re.I)),
    ("houdini", re.compile(r"\bhoudini\b", re.I)),
    ("proprietary", re.compile(r"\b(proprietary|in[-\s]house)\s+engine\b", re.I)),
)


def detect_engines(title: str, description: str = "") -> list[str]:
    text = f"{title or ''} {description or ''}"
    return [name for name, rx in _ENGINES if rx.search(text)]


# ───────────────────── fuente / verificación / compatibilidad ─────────────────────

OFFICIAL_ATS = {
    "greenhouse", "lever", "ashby", "smartrecruiters", "recruitee", "personio",
    "teamtailor", "workday", "workable", "massive-wp",
}


def source_kind(job: dict) -> str:
    ats = job.get("ats", "")
    if ats == "adzuna-signal" or job.get("signalOnly"):
        return "signal"
    if ats == "adzuna" or job.get("viaAggregator"):
        return "aggregator"
    if ats in OFFICIAL_ATS:
        return "ats"
    if ats == "custom":
        return "official-site"
    return "aggregator"


SOURCE_LABEL = {
    "ats": "ATS oficial",
    "official-site": "Web oficial",
    "aggregator": "Agregador (señal)",
    "signal": "Señal sin oferta concreta",
}


def verification_of(job: dict, kind: str) -> str:
    """verified solo si procede de una fuente oficial Y apunta a una vacante
    concreta (no a una landing)."""
    if kind in ("ats", "official-site") and job.get("url") and not job.get("signalOnly"):
        return "verified"
    return "unverified"


def compatibility_of(eligibility: str, contract: str, hours: str) -> str:
    """compatible: se puede trabajar desde España (confirmado/posible) y el
    contrato no es freelance/B2B ni la jornada parcial.
    incompatible: restringida o freelance (evidencia explícita).
    review: todo lo demás (incertidumbre o contradicción)."""
    if eligibility == "restricted" or contract == "freelance" or hours == "part":
        return "incompatible"
    if eligibility in ("confirmed", "possible") and contract != "temporary":
        return "compatible"
    return "review"


# ───────────────────────── relevancia explicable ─────────────────────────

WEIGHTS = {
    "role_vfx": 30, "role_tech_vfx": 35, "role_technical_artist": 15,
    "senior_or_lead": 20, "engine_unreal": 15,
    "spain_confirmed": 40, "spain_possible": 15, "spain_unknown": -5, "spain_contradiction": -10,
    "spain_restricted": -60,
    "contract_employee": 30, "contract_unknown": -3, "contract_temporary": -15, "contract_freelance": -80,
    "hours_part": -40,
    "not_remote": -25, "elsewhere_no_remote": -10,
    "verified": 10, "unverified": -10,
}


def score_job(job: dict) -> dict:
    s, why = 0, []

    def add(key, text):
        nonlocal s
        s += WEIGHTS[key]
        why.append(f"{WEIGHTS[key]:+d} {text}")

    role = job.get("role", "other")
    if role == "tech-vfx":
        add("role_tech_vfx", "Rol Technical VFX")
    elif role == "vfx":
        add("role_vfx", "Rol VFX especializado")
    elif role == "technical-artist":
        add("role_technical_artist", "Rol Technical Artist cercano")
    if job.get("seniority") in ("senior", "lead"):
        add("senior_or_lead", f"Nivel {'Lead' if job['seniority'] == 'lead' else 'Senior'}")
    if "unreal" in (job.get("engines") or []):
        add("engine_unreal", "Menciona Unreal/Niagara")

    el = job.get("spainEligibility", "unknown")
    add(f"spain_{el}", {
        "confirmed": "Remoto desde España confirmado por la fuente",
        "possible": "Remoto UE/global (España posible, sin confirmar)",
        "unknown": "Elegibilidad España desconocida (no es rechazo)",
        "contradiction": "Señales contradictorias sobre ubicación: revisar",
        "restricted": "Restringida a otro país",
    }[el])

    wp, loc = job.get("workplaceType", "unknown"), job.get("location", "") or ""
    if wp in ("onsite", "hybrid"):
        add("not_remote", "Presencial/híbrida: no es 100 % remota")
    elif wp == "unknown" and loc and not _SPAIN.search(loc) and el not in ("confirmed", "possible"):
        add("elsewhere_no_remote", "Ubicación fuera de España sin indicación de remoto (incertidumbre, no rechazo)")

    ct = job.get("contractType", "unknown")
    add(f"contract_{ct}", {
        "employee": "Empleo asalariado indefinido con evidencia",
        "unknown": ("Contratación ambigua según la fuente: «%s» (verificar si es laboral)" % job["contractEvidence"])
                   if job.get("contractEvidence") else "Contrato desconocido (no es rechazo)",
        "temporary": "Contrato temporal",
        "freelance": "Freelance/B2B: incompatible con el objetivo",
    }[ct])
    if job.get("hours") == "part":
        add("hours_part", "Jornada parcial")
    add("verified" if job.get("verification") == "verified" else "unverified",
        "Fuente oficial con enlace directo" if job.get("verification") == "verified"
        else "Sin verificar en fuente oficial")
    return {"score": s, "reasons": why}


# ─────────────────────────── API pública ───────────────────────────

def enrich_job(job: dict, description: str = "") -> dict:
    """Añade los campos V2 a `job` (mutación in situ; devuelve el mismo dict).
    Idempotente. Compatible con registros antiguos: solo usa campos que ya
    tenían (title, location, workplaceType, ats, url...). Con `description`
    (oficial, si el adaptador la tiene) extrae además evidencia de contrato y
    elegibilidad; la descripción en sí NUNCA se almacena."""
    title, loc = job.get("title", ""), job.get("location", "")
    text = f"{title} {loc} {description or ''}"
    wp = job.get("workplaceType", "unknown")

    elig, reason = classify_spain_eligibility(title, loc, description, wp, job.get("remoteScope", ""))
    ctype, cev = classify_contract(text)
    kind = source_kind(job)
    # «Confirmado» exige que lo diga una fuente oficial; un indicio que solo
    # viene de un agregador se queda en «posible» (spec §2).
    if elig == "confirmed" and kind in ("aggregator", "signal"):
        elig = "possible"
        reason = "Indicio de remoto en España según un agregador; sin confirmar en la fuente oficial."

    job["spainEligibility"], job["spainReason"] = elig, reason
    job["contractType"], job["contractEvidence"] = ctype, cev
    job["hours"] = classify_hours(text)
    job["seniority"] = detect_seniority(title)
    job["role"] = detect_role(title, description)
    job["engines"] = detect_engines(title, description)
    job["sourceKind"] = kind
    job["verification"] = verification_of(job, kind)
    # directUrl: ¿la URL lleva a la vacante concreta? (False para landings/señales)
    job["directUrl"] = not (job.get("signalOnly") or job.get("urlIsLanding"))
    job["compatibility"] = compatibility_of(elig, ctype, job["hours"])
    job["relevance"] = score_job(job)
    return job
