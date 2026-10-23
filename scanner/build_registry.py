"""
Genera data/companies-registry.json: el registro de empresas EVALUADAS y candidatas.

Principios (spec §4): no inventar ATS ni endpoints; distinguir evaluada de conectada; cada dato
lleva su procedencia (`evidence`). Estados: active | unsupported | blocked | pending.
  - «active»  solo si el último escaneo de producción conectó con una API fiable.
  - «pending» es el valor por defecto: configurada pero sin primera ejecución real, o candidata sin
    verificar. El motivo siempre explica por qué.
Uso:  python -m scanner.build_registry           (reescribe data/companies-registry.json)
Las evidencias de «web-research» son la investigación manual del 2026-10-21 (EMPRESAS_Y_FUENTES.md).
"""
import json, re, sys
from pathlib import Path
from .companies import detect_ats

DATA = Path(__file__).parent.parent / "data"
RESEARCH_DATE = "2026-10-21"

# Investigación manual: solo hechos observados en páginas oficiales o anuncios citados.
RESEARCHED = {
    "Mundfish": dict(country="CY", officialUrl="https://mundfish.com", careersUrl="https://mundfish.com/en/careers", ats=None, method="html-adapter",
        reliability="baja", priority="alta", spainCompat="posible: la web declara «global remote work», no nombra España",
        reason="Sin ATS (solicitud por email/Telegram). Adaptador propio probado con HTML de muestra; falta la primera ejecución real.",
        observed="Web oficial lista «VFX Artist #remote #senior» (ficha /careers/vfx-artist) y «Technical Artist #remote #middle». Sin tipo de contrato, salario ni fecha."),
    "AXIOM VFX": dict(country=None, officialUrl="https://www.axiomvfx.com", careersUrl="https://www.axiomvfx.com/career", ats=None, method="html-adapter",
        reliability="baja", priority="media", spainCompat="posible: oficina en Valencia (España) y trabajo remoto asíncrono; no confirmado para el puesto",
        reason="Estudio de servicios; el anuncio ofrece «Remote, flexible engagement — full-time or contract»: contratación laboral NO acreditada.",
        observed="Una ficha abierta «Real-Time VFX Artist» (Niagara/UE5). Sedes: Austin (EE. UU.) y Valencia (España)."),
    "Larian Studios": dict(country=None, officialUrl="https://larian.com", careersUrl="https://jobs.lever.co/larian", ats="lever", method="api",
        reliability="alta", priority="media", spainCompat="estudio en Barcelona; los puestos VFX vistos exigen trabajo presencial (no remoto)",
        reason="Tablero Lever visto en una oferta real y sondeado por el scanner; falta la primera ejecución real con el adaptador V2.",
        observed="Ofertas «Senior VFX Artist» en Dublín, Quebec y Barcelona, a jornada completa y presenciales."),
    "IO Interactive": dict(country="DK", officialUrl=None, careersUrl=None, ats=None, method="none",
        reliability="desconocida", priority="media", spainCompat="estudio en Barcelona; ofertas VFX vistas como presenciales/híbridas, remoto no confirmado",
        reason="Las fichas viven en apply.ioi.dk (/jobs/<id>-<slug>) pero no se ha verificado qué ATS hay detrás ni la URL del listado.",
        observed="Estudios en Copenhague, Malmö, Barcelona, Brighton y Estambul; VFX Artist (007 First Light) publicado en Barcelona."),
    "Digital Sun Games": dict(country="ES", officialUrl="https://digitalsungames.com", careersUrl="https://digitalsungames.com/jobs/", ats=None, method="none",
        reliability="desconocida", priority="alta", spainCompat="Valencia (España); modalidad híbrida, no 100 % remota",
        reason="Web propia con fichas /jobs/<slug>/ cuyo slug de una sola palabra no lo detecta el scraper genérico: requiere adaptador propio.",
        observed="VFX Artist (Unity): contrato indefinido, jornada completa, híbrido (anuncio en Stratos de 2024-10-08). Proceso de selección «permanentemente abierto»."),
    "Escape Velocity Entertainment": dict(country=None, officialUrl=None, careersUrl=None, ats=None, method="none",
        reliability="desconocida", priority="alta", spainCompat="posible: puestos «Fully Remote» con restricción «North America, Europe» (según agregadores)",
        reason="Solo visto en agregadores (Built In, Remotive); falta localizar su web oficial de empleo y su ATS.",
        observed="Varias vacantes VFX/Tech Art remotas (Senior VFX Artist, Lead Outsourcing VFX Artist…). Contrato no indicado."),
    "MercurySteam": dict(country="ES", officialUrl=None, careersUrl=None, ats=None, method="none",
        reliability="desconocida", priority="baja", spainCompat="Madrid (San Sebastián de los Reyes); trabajo presencial",
        reason="Anunció un proceso de ajuste de plantilla (despidos) en mayo de 2026 según varios medios: baja probabilidad de contratar.",
        observed="Solicitud por email; sin ATS ni listado oficial verificado."),
}

# Pendientes nombrados en la especificación sin investigar a fondo todavía.
SPEC_PENDING = {
    "2K Valencia / 31st Union": "Sin investigar: localizar página oficial de empleo y ATS.",
}

NOT_STUDIOS = {"smartrecruiters, inc.": "Es el proveedor del ATS, no un estudio (coincidencia de nombre).",
               "nextgen skills academy": "Academia de formación, no estudio de juegos/VFX.",
               "sourcing unicorns": "Empresa de selección de personal, no estudio.",
               "yo ai labs": "Empresa de IA, sin relación con VFX de videojuegos."}


def _slug(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _board_slug(url):
    m = re.search(r"(?:greenhouse\.io|lever\.co|ashbyhq\.com|smartrecruiters\.com|workable\.com)/([^/?#]+)", url) or \
        re.search(r"//([a-z0-9-]+)\.(?:jobs\.personio|recruitee)", url)
    return m.group(1) if m else ""


def _err_kind(msg):
    m = (msg or "").lower()
    return "blocked" if any(x in m for x in ("403", "401", "forbidden", "blocked", "captcha")) else "other"


def build(data_dir: Path = DATA) -> dict:
    load = lambda n, d: json.loads((data_dir / n).read_text(encoding="utf-8")) if (data_dir / n).exists() else d
    companies = load("companies.json", [])
    status = {s["company"]: s for s in load("scanner-status.json", []) if isinstance(s, dict) and s.get("company")}
    cache = load("ats-discovery-cache.json", {})
    audits = {a["name"].lower(): a for a in load("source-audit.json", {}).get("companies", [])}
    out, seen = [], set()

    for c in companies:
        name, url = c["name"], c["careersUrl"]
        s = status.get(name)
        declared = (c.get("type") or "custom").lower()
        detected = detect_ats(url)
        ats = detected if declared == "custom" else declared
        r = RESEARCHED.get(name, {})
        e = dict(name=name, country=c.get("country", r.get("country")), officialUrl=c.get("officialUrl", r.get("officialUrl")), careersUrl=url,
                 ats=None if ats in ("custom", "mundfish", "axiomvfx") else ats,
                 method="api" if ats not in ("custom", "mundfish", "axiomvfx", "teamtailor", "ea", "infiniteplus", "mercurysteam") else "html-adapter",
                 reliability="alta" if ats not in ("custom", "mundfish", "axiomvfx", "teamtailor", "ea", "infiniteplus", "mercurysteam") else "baja",
                 state="pending", reason="", priority=r.get("priority", "media"), spainCompat=r.get("spainCompat"),
                 configured=True, lastChecked=None, evidence=dict(kind="none", date=None, source=None))
        if name in RESEARCHED:
            e.update(reason=r["reason"], observed=r.get("observed"))
            e["evidence"] = dict(kind="web-research", date=RESEARCH_DATE, source=r.get("careersUrl") or r.get("officialUrl"))
            e["configuredNotYetRun"] = True
        elif s:
            e["lastChecked"] = s.get("lastAttempt") or None
            e["evidence"] = dict(kind="scanner-run", date="2026-10-08", source="data/scanner-status.json")
            if s.get("status") == "error":
                e["state"] = "blocked" if _err_kind(s.get("error")) == "blocked" else "pending"
                e["reason"] = "Último escaneo falló: " + (s.get("error") or "sin detalle")[:140]
            elif declared == "custom" and detected != "custom":
                e["reason"] = f"Estaba como «custom» pese a ser un tablero {detected}; V2 usa su adaptador oficial. Pendiente de primera ejecución."
            elif e["method"] == "html-adapter":
                e["reason"] = "Scraper HTML genérico: 0 resultados no distingue «sin vacantes» de «página con JavaScript»; revisar a mano."
            else:
                e["state"] = "active"
                e["reason"] = f"API fiable; último escaneo correcto con {s.get('jobsFound', 0)} oferta(s) VFX."
        else:
            e["reason"] = "Configurada en V2 sin ejecución real todavía."
            e["configuredNotYetRun"] = True
            e["evidence"] = dict(kind="discovery-cache", date=None, source="data/ats-discovery-cache.json")
        if s and s.get("lastSuccess") and s.get("ats") == ats:
            e["configuredNotYetRun"] = False
            e["lastChecked"] = s.get("lastAttempt")
            e["runtimeEvidence"] = {"kind": "scanner-run", "date": s.get("lastAttempt"), "source": "data/scanner-status.json"}
            if e["evidence"]["kind"] == "web-research":
                e["researchEvidence"] = dict(e["evidence"])
            e["evidence"] = dict(e["runtimeEvidence"])
            if s.get("status") == "error":
                e["state"] = "blocked" if _err_kind(s.get("error")) == "blocked" else "pending"
                e["reason"] = "Fallo en el ultimo escaneo: " + (s.get("error") or "sin detalle")[:140]
            elif s.get("status") == "ok":
                connected = s.get("reliable") or s.get("listingVerified") or s.get("jobsFound", 0) > 0
                e["state"] = "active" if connected else "pending"
                e["reason"] = (f"Portal directo consultado: {s.get('jobsFound', 0)} ofertas VFX; "
                               f"{s.get('totalPostingsSeen', 0)} anuncios examinados."
                               + (" Revisar scraper HTML sin resultados." if s.get("needsReview") else ""))
                if r:
                    e["historicalResearchReason"] = r["reason"]
                    if name == "AXIOM VFX":
                        e["reason"] += " contratación laboral NO acreditada: anuncio ambiguo, full-time or contract."
        out.append(e); seen.add(name.lower())

    # Investigadas a mano pero aún no configuradas en el scanner
    for name, r in RESEARCHED.items():
        if name.lower() in seen:
            continue
        out.append(dict(name=name, country=r.get("country"), officialUrl=r.get("officialUrl"), careersUrl=r.get("careersUrl"), ats=r.get("ats"),
                        method=r.get("method", "none"), reliability=r.get("reliability", "desconocida"), state="pending", reason=r["reason"],
                        priority=r.get("priority", "media"), spainCompat=r.get("spainCompat"), configured=False, lastChecked=None,
                        observed=r.get("observed"), evidence=dict(kind="web-research", date=RESEARCH_DATE, source=r.get("careersUrl") or r.get("officialUrl"))))
        seen.add(name.lower())

    urls = {c["careersUrl"].rstrip("/").lower() for c in companies}
    for key, v in sorted(cache.items()):
        if not v.get("found") or key in seen:
            continue
        audit = audits.get(key.lower())
        if audit and audit.get("canonicalCompany", "").lower() in seen:
            continue
        u = v["careersUrl"].rstrip("/").lower()
        if u in urls:                      # mismo tablero que una empresa ya configurada o ya listada
            continue
        urls.add(u)
        if key in NOT_STUDIOS:
            out.append(dict(name=key.title(), country=None, officialUrl=None, careersUrl=v["careersUrl"], ats=v["ats"], method="none",
                            reliability="desconocida", state="unsupported", reason=NOT_STUDIOS[key], priority="baja", spainCompat=None,
                            configured=False, lastChecked=None, evidence=dict(kind="discovery-cache", date=None, source="data/ats-discovery-cache.json")))
            continue
        exact = _slug(key) == _slug(_board_slug(v["careersUrl"]))
        out.append(dict(name=key.title() if key.islower() else key, country=None, officialUrl=None, careersUrl=v["careersUrl"], ats=v["ats"],
                        method="api", reliability="alta" if exact else "media", state="pending",
                        reason=("Tablero hallado por el sondeo del scanner con slug idéntico al nombre; " if exact else
                                "Tablero hallado por el sondeo con slug parcial (posible otra empresa); ") + "identidad sin verificar. No configurada.",
                        priority="media", spainCompat=None, configured=False, lastChecked=None,
                        evidence=dict(kind="discovery-cache", date=None, source="data/ats-discovery-cache.json"), slugMatch="exacta" if exact else "parcial"))
    for name, why in SPEC_PENDING.items():
        if name.lower() in seen:
            continue
        out.append(dict(name=name, country=None, officialUrl=None, careersUrl=None, ats=None, method="none", reliability="desconocida",
                        state="pending", reason=why, priority="media", spainCompat=None, configured=False, lastChecked=None,
                        evidence=dict(kind="none", date=None, source=None)))
    # Audited studios may have no discovered ATS at all. Keep them visible
    # with their actual public site and the precise remaining limitation.
    listed = {entry["name"].lower() for entry in out}
    for key, audit in audits.items():
        if key in listed or audit.get("canonicalCompany", "").lower() in listed:
            continue
        out.append(dict(name=audit["name"], country=audit.get("country"), officialUrl=audit.get("officialUrl"),
                        careersUrl=None, ats=None, method="none", reliability="desconocida",
                        state="pending", reason=audit["reason"], priority="media", spainCompat=None,
                        configured=False, lastChecked=None, evidence=dict(kind="none", date=None, source=None)))
        listed.add(key)
    for entry in out:
        audit = audits.get(entry["name"].lower())
        if audit and not entry.get("configured"):
            entry.update(state=audit["state"], reason=audit["reason"],
                         careersUrl=audit.get("replacementCareersUrl"),
                         candidateRejected=audit.get("candidateRejected", False),
                         evidence=dict(kind="web-research", date="2026-10-23", source=audit["candidateUrl"]))
            if audit.get("officialUrl"):
                entry["officialUrl"] = audit["officialUrl"]
            if audit.get("country"):
                entry["country"] = audit["country"]
    states = {}
    for e in out:
        states[e["state"]] = states.get(e["state"], 0) + 1
    direct = sum(1 for e in out if e["evidence"]["kind"] in ("scanner-run", "web-research"))
    return {"generatedAt": max([RESEARCH_DATE + "T00:00:00Z"] + [v.get("lastAttempt") or "" for v in status.values()]), "note": "Evaluada = evidencia directa del portal o su identidad (scanner-run o web-research). Conectada = consulta correcta con listado reconocido; no implica vacantes VFX ni elegibilidad para España.",
            "totals": {"registered": len(out), "withDirectEvidence": direct, "byState": states}, "companies": out}


if __name__ == "__main__":
    reg = build()
    (DATA / "companies-registry.json").write_text(json.dumps(reg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(reg["totals"], ensure_ascii=False))
