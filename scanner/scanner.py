import json, logging, os, re, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scanner.adapters.greenhouse import GreenhouseAdapter
from scanner.adapters.lever import LeverAdapter
from scanner.adapters.teamtailor import TeamtailorAdapter
from scanner.adapters.custom_html import CustomHtmlAdapter
from scanner.adapters.workday import WorkdayAdapter
from scanner.adapters.workable import WorkableAdapter
from scanner.adapters.ashby import AshbyAdapter
from scanner.adapters.smartrecruiters import SmartRecruitersAdapter
from scanner.adapters.recruitee import RecruiteeAdapter
from scanner.adapters.personio import PersonioAdapter
from scanner.adapters.massive_wp import MassiveWPAdapter
from scanner.adapters.official_sites import MundfishAdapter, AxiomVfxAdapter
from scanner.adapters.ea import EaAdapter
from scanner.adapters.epic import EpicAdapter
from scanner.adapters.company_feeds import BambooAdapter, PinpointAdapter, Room8Adapter
from scanner.companies import detect_ats, dedupe_companies
from scanner.normalizer import preserve_first_seen, now_iso
from scanner.classify import enrich_job, SOURCE_LABEL
from scanner.lifecycle import reconcile, merge_aggregator_into_official, source_key
from scanner.company_category import classify_company_category
from scanner.sources.adzuna import fetch_adzuna_jobs, find_signal_matches, _normalize_company_name
from scanner.auto_discover import discover_direct_source, load_discovery_cache, save_discovery_cache

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("scanner")

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

COMPANIES_FILE = DATA_DIR / "companies.json"
JOBS_FILE = DATA_DIR / "jobs.json"
STATUS_FILE = DATA_DIR / "scanner-status.json"
REPORT_FILE = DATA_DIR / "scanner-report.json"
HISTORY_LIMIT = 20

ATS_MAP = {
    "greenhouse": GreenhouseAdapter,
    "lever": LeverAdapter,
    "ashby": AshbyAdapter,
    "smartrecruiters": SmartRecruitersAdapter,
    "recruitee": RecruiteeAdapter,
    "personio": PersonioAdapter,
    "teamtailor": TeamtailorAdapter,
    "workday": WorkdayAdapter,
    "workable": WorkableAdapter,
    "custom": CustomHtmlAdapter,
    "massive-wp": MassiveWPAdapter,
    "mundfish": MundfishAdapter,
    "axiomvfx": AxiomVfxAdapter,
    "ea": EaAdapter,
    "epic": EpicAdapter,
    "bamboo": BambooAdapter,
    "pinpoint": PinpointAdapter,
    "room8": Room8Adapter,
}


def load_existing_jobs(path: Path | None = None) -> dict[str, dict]:
    path = path or JOBS_FILE
    if not path.exists() or path.stat().st_size == 0:
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        logger.warning(f"{path} exists but is not valid JSON — starting fresh")
        return {}
    return {j["id"]: migrate_legacy_job(j) for j in data.get("jobs", [])}


def migrate_legacy_job(job: dict) -> dict:
    """Migración compatible de registros anteriores a V2 (idempotente).

    * Añade los campos V2 (elegibilidad, contrato...) sin inventar nada: lo que
      el registro antiguo no permite saber queda «unknown».
    * Corrige el «auto-upgrade» antiguo: una vacante de Adzuna (id az-*) a la
      que se le había cambiado la URL por la landing del tablero de la empresa
      y puesto viaAggregator=false vuelve a ser una señal de agregador, y la
      landing se conserva como companyCareersUrl (no es URL de la vacante).
    * Normaliza remoteScope a minúsculas de negocio no se toca (se conserva el
      valor histórico), pero 'Unknown'/'unknown' se unifica en 'unknown'.
    """
    if job.get("id", "").startswith("az-") and job.get("ats") not in ("adzuna", "adzuna-signal"):
        job["companyAts"] = job["ats"]
        job["companyCareersUrl"] = job.get("url", "")
        job["ats"] = "adzuna"
        job["viaAggregator"] = True
        job["urlIsLanding"] = True
    if (job.get("remoteScope") or "").lower() == "unknown":
        job["remoteScope"] = "unknown"
    if job.get("id", "").startswith("sig-"):
        job["urlIsLanding"] = True
    if "spainEligibility" not in job or "relevance" not in job:
        enrich_job(job)
    job.setdefault("directUrl", not job.get("urlIsLanding", False))
    job.setdefault("missCount", 0)
    return job


def _strict_company_match(a: str, b: str) -> bool:
    """Coincidencia CONSERVADORA de empresa para fusionar duplicados: igual tras
    quitar sufijos legales o conjunto de palabras contenido en el otro por
    palabras completas ('EA' ~ 'EA Vancouver', pero NO 'EA' ~ 'Sea Games')."""
    ta = set(_normalize_company_name(a).split())
    tb = set(_normalize_company_name(b).split())
    if not ta or not tb:
        return False
    return ta == tb or ta <= tb or tb <= ta


def _normalize_for_dedup(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def dedupe_adzuna_against_direct_matches(adzuna_jobs: list[dict], direct_jobs: dict) -> list[dict]:
    """DATA-02: gana la evidencia oficial. Si la vacante ya está en un ATS
    oficial se descarta la copia de Adzuna y la oficial anota alsoSeenIn."""
    kept, merged = merge_aggregator_into_official(adzuna_jobs, direct_jobs, _strict_company_match)
    if merged:
        logger.info(f"[Adzuna] Merged {merged} job(s) already found via a direct company adapter")
    return kept


def compute_jobs_by_ats(active_jobs: list[dict]) -> dict[str, int]:
    """Cuenta ofertas activas por valor de 'ats' (greenhouse, lever, ...,
    adzuna, adzuna-signal). Desde V2 una vacante de Adzuna SIGUE contando como
    'adzuna' aunque se haya descubierto el tablero de su empresa."""
    counts: dict[str, int] = {}
    for j in active_jobs:
        key = j.get("ats", "unknown")
        counts[key] = counts.get(key, 0) + 1
    return counts


def compute_jobs_by_source(active_jobs: list[dict]) -> dict[str, int]:
    counts = {"ats": 0, "official-site": 0, "aggregator": 0, "signal": 0}
    for j in active_jobs:
        counts[j.get("sourceKind", "aggregator")] = counts.get(j.get("sourceKind", "aggregator"), 0) + 1
    return counts


def build_signal_job(company: dict, now: str) -> dict:
    name = company["name"]
    job = {
        "id": f"sig-{re.sub(r'[^a-z0-9]', '-', name.lower())}",
        "company": name,
        "title": "Posible oferta VFX detectada — ver listado completo",
        "url": company["careersUrl"],
        "location": "",
        "workplaceType": "unknown",
        "remoteScope": "unknown",
        "ats": "adzuna-signal",
        "matchType": "possibleMatch",
        "companyCategory": classify_company_category(name, company.get("category")),
        "viaAggregator": False,
        "signalOnly": True,
        "urlIsLanding": True,  # enlaza a la página de empleo, no a una vacante
        "directUrl": False,
        "firstSeen": now,
        "lastSeen": now,
        "status": "active",
    }
    return enrich_job(job)


def attach_company_careers_links(adzuna_jobs: list[dict], cache: dict) -> tuple[list[dict], int]:
    """Sustituye al antiguo «upgrade_adzuna_jobs_to_direct_links».

    CAUSA RAÍZ corregida: el antiguo upgrade reescribía la URL de la vacante
    por la landing del tablero de la empresa, cambiaba ats al del tablero y
    ponía viaAggregator=false. Resultado real auditado: 29 de 68 ofertas
    «oficiales» eran en realidad señales de Adzuna, sin verificar que la
    vacante existiera en ese ATS y sin enlace a la vacante concreta.

    Ahora: la oferta sigue siendo de Adzuna (url, ats y viaAggregator no se
    tocan); si se descubre el tablero oficial de la empresa solo se anota como
    companyCareersUrl/companyAts para ofrecer un enlace de contraste.
    """
    attached = 0
    out = []
    checked: dict[str, dict | None] = {}
    for job in adzuna_jobs:
        name = job["company"]
        if name not in checked:
            checked[name] = discover_direct_source(name, cache=cache)
        discovery = checked[name]
        if discovery:
            job = dict(job)
            job["companyCareersUrl"] = discovery["careersUrl"]
            job["companyAts"] = discovery["ats"]
            attached += 1
        out.append(job)
    return out, attached


def _error_kind(msg: str) -> str:
    m = (msg or "").lower()
    if "403" in m or "401" in m or "blocked" in m or "forbidden" in m or "captcha" in m:
        return "blocked"
    if "name or service not known" in m or "nameresolution" in m or "failed to resolve" in m or "connection refused" in m or "max retries exceeded" in m:
        return "network"
    if "timeout" in m or "timed out" in m or "no response" in m:
        return "timeout"
    if "422" in m or "404" in m or "400" in m or "500" in m or "502" in m or "503" in m or "request failed" in m:
        return "http"
    if "json" in m or "parse" in m:
        return "parse"
    return "unknown"


def _metadata_completeness(jobs: list[dict]) -> float | None:
    """% de campos clave conocidos (ubicación, modalidad, elegibilidad,
    contrato, jornada) sobre el total posible. None si no hay ofertas."""
    if not jobs:
        return None
    known = total = 0
    for j in jobs:
        for ok in (bool(j.get("location")), j.get("workplaceType", "unknown") != "unknown",
                   j.get("spainEligibility", "unknown") != "unknown",
                   j.get("contractType", "unknown") != "unknown", j.get("hours", "unknown") != "unknown"):
            total += 1
            known += 1 if ok else 0
    return round(100 * known / total, 1)


def _load_json(path: Path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


def _write_json_atomic(path: Path, payload) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def resolve_ats(company: dict) -> str:
    """Un «type» explícito manda, SALVO «custom»/vacío: si la URL pertenece a un ATS conocido se usa
    su adaptador oficial. Antes, "type":"custom" en companies.json forzaba el scraper HTML genérico
    aunque la URL fuese un tablero de Greenhouse/Lever (caso real: Guerrilla, Frontier)."""
    declared = (company.get("type") or "").lower()
    detected = detect_ats(company.get("careersUrl", ""))
    if declared in ("", "custom"):
        return detected
    return declared


def scan_companies(companies: list[dict], existing: dict, adapters: dict, previous_status: dict, now: str):
    """Escanea cada empresa. Devuelve (jobs_vistos, statuses, outcomes,
    empresas_a_revisar, nº_ok, nº_error). Una empresa con enabled=false se
    omite (no cuenta como fallo)."""
    seen: dict[str, dict] = {}
    statuses, outcomes, needs_review_companies = [], {}, []
    succeeded = failed = 0

    for company in companies:
        name = company["name"]
        key = f"company:{name}"
        prev = previous_status.get(name, {})
        if company.get("enabled") is False:
            statuses.append({"company": name, "status": "disabled", "ats": company.get("type"), "lastAttempt": now,
                             "lastSuccess": prev.get("lastSuccess")})
            continue
        ats = resolve_ats(company)
        cls = adapters.get(ats, CustomHtmlAdapter)
        logger.info(f"Scanning {name} via {ats}…")
        t0 = time.monotonic()
        try:
            adapter = cls(company)
            found = adapter.fetch_jobs()
            incomplete = bool(getattr(adapter, "incomplete", False))
            for job in found:
                preserve_first_seen(existing, job, now)
                seen[job["id"]] = job
            total_seen = getattr(adapter, "total_seen", None)
            reliable = getattr(adapter, "uses_reliable_api", True)
            listing_verified = bool(getattr(adapter, "listing_verified", False))
            needs_review = (len(found) == 0) and not reliable and not listing_verified
            if needs_review:
                needs_review_companies.append(company)
            outcomes[key] = {"ok": True, "reliable": reliable, "complete": not incomplete}
            statuses.append({
                "company": name, "status": "ok", "ats": ats, "reliable": reliable,
                "listingVerified": listing_verified or reliable,
                "incomplete": incomplete, "jobsFound": len(found), "totalPostingsSeen": total_seen,
                "needsReview": needs_review, "metadataComplete": _metadata_completeness(found),
                "durationMs": int((time.monotonic() - t0) * 1000),
                "lastAttempt": now, "lastSuccess": now, "consecutiveFailures": 0,
            })
            succeeded += 1
        except Exception as e:
            logger.error(f"Error scanning {name}: {e}")
            outcomes[key] = {"ok": False, "error": str(e)[:300]}
            statuses.append({
                "company": name, "status": "error", "ats": ats, "error": str(e)[:300], "errorKind": _error_kind(str(e)),
                "durationMs": int((time.monotonic() - t0) * 1000), "lastAttempt": now,
                "lastSuccess": prev.get("lastSuccess"), "consecutiveFailures": int(prev.get("consecutiveFailures", 0)) + 1,
            })
            failed += 1
            needs_review_companies.append(company)
    return seen, statuses, outcomes, needs_review_companies, succeeded, failed


def build_report(now, duration_s, statuses, active, history, adzuna_status, merged):
    kinds = compute_jobs_by_source(active)
    n = len(active) or 1
    src_ok = sum(1 for s in statuses if s.get("status") == "ok")
    src_fail = sum(1 for s in statuses if s.get("status") in ("error", "partial"))
    summary = {
        "activeJobs": len(active),
        "officialJobs": kinds["ats"] + kinds["official-site"],
        "aggregatorJobs": kinds["aggregator"],
        "signalJobs": kinds["signal"],
        "aggregatorShare": round(100 * (kinds["aggregator"] + kinds["signal"]) / n, 1) if active else 0,
        "verifiedJobs": sum(1 for j in active if j.get("verification") == "verified"),
        "duplicatesMerged": merged,
        "unknownWorkplace": sum(1 for j in active if j.get("workplaceType", "unknown") == "unknown"),
        "unknownEligibility": sum(1 for j in active if j.get("spainEligibility") == "unknown"),
        "unknownContract": sum(1 for j in active if j.get("contractType") == "unknown"),
        "sourcesOk": src_ok, "sourcesFailed": src_fail,
        "metadataComplete": _metadata_completeness(active),
    }
    entry = {"ranAt": now, "durationSec": round(duration_s, 1), "sourcesOk": src_ok, "sourcesFailed": src_fail,
             "activeJobs": len(active), "officialJobs": summary["officialJobs"],
             "aggregatorJobs": summary["aggregatorJobs"] + summary["signalJobs"]}
    return {
        "generatedAt": now, "durationSec": round(duration_s, 1), "summary": summary,
        "adzuna": {k: v for k, v in adzuna_status.items() if k not in ("company",)},
        "history": ([entry] + (history or []))[:HISTORY_LIMIT],
        "workflowUrl": "https://github.com/YagoVfx/yagovfx.github.io/actions/workflows/vfx-jobs-scanner.yml",
    }


def is_direct_job(job: dict) -> bool:
    """El prefijo hist?rico prevalece sobre etiquetas antiguas incorrectas."""
    return (not str(job.get("id", "")).startswith(("az-", "sig-"))
            and job.get("ats") not in ("adzuna", "adzuna-signal")
            and not job.get("viaAggregator") and not job.get("signalOnly")
            and job.get("sourceKind") not in ("aggregator", "signal")
            and job.get("ats") in set(ATS_MAP) | {"custom"})


def run(now: str | None = None, data_dir: Path | None = None, adapters: dict | None = None,
        adzuna_fetcher=None, discover_cache_loader=None, discover_cache_saver=None,
        include_aggregators: bool = False):
    data_dir = Path(data_dir) if data_dir else DATA_DIR
    data_dir.mkdir(exist_ok=True)
    companies_file, jobs_file = data_dir / "companies.json", data_dir / "jobs.json"
    status_file, report_file = data_dir / "scanner-status.json", data_dir / "scanner-report.json"
    adapters = adapters or ATS_MAP
    adzuna_fetcher = adzuna_fetcher or fetch_adzuna_jobs
    load_cache = discover_cache_loader or load_discovery_cache
    save_cache = discover_cache_saver or save_discovery_cache
    t_start = time.monotonic()
    now = now or now_iso()

    if not companies_file.exists():
        logger.error(f"companies.json not found at {companies_file}")
        sys.exit(1)
    with open(companies_file, encoding="utf-8") as f:
        companies = dedupe_companies(json.load(f))

    existing = load_existing_jobs(jobs_file)
    excluded_aggregators = 0
    if not include_aggregators:
        direct = {jid: j for jid, j in existing.items() if is_direct_job(j)}
        excluded_aggregators = len(existing) - len(direct)
        existing = direct
    previous_status = {s.get("company"): s for s in _load_json(status_file, []) if isinstance(s, dict)}
    previous_report = _load_json(report_file, {})

    seen, statuses, outcomes, needs_review_companies, succeeded, failed = scan_companies(
        companies, existing, adapters, previous_status, now)

    if include_aggregators:
        adzuna_jobs, adzuna_status = adzuna_fetcher()
        adz_ok = adzuna_status.get("status") == "ok"
        # Adzuna es un índice truncado (nº limitado de páginas): su ausencia es una
        # evidencia débil -> fuente NO fiable (varias ausencias seguidas para cerrar).
        outcomes["adzuna"] = {"ok": adz_ok, "reliable": False,
                              "complete": adz_ok and not adzuna_status.get("truncated"),
                              "error": None if adz_ok else f"Adzuna {adzuna_status.get('status')}"}
        if adzuna_status.get("status") in ("partial", "error"):
            failed += 1

        signals, matched_adzuna_ids = find_signal_matches(adzuna_jobs, needs_review_companies)
        matched = set(matched_adzuna_ids)
        adzuna_jobs = [j for j in adzuna_jobs if j["id"] not in matched]

        cache = load_cache()
        adzuna_jobs, careers_attached = attach_company_careers_links(adzuna_jobs, cache)
        save_cache(cache)

        signal_jobs_added = 0
        for company in needs_review_companies:
            if signals.get(company["name"]):
                job = build_signal_job(company, now)
                preserve_first_seen(existing, job, now)
                seen[job["id"]] = job
                signal_jobs_added += 1

        before_dedupe = len(adzuna_jobs)
        adzuna_jobs = dedupe_adzuna_against_direct_matches(adzuna_jobs, seen)
        merged = before_dedupe - len(adzuna_jobs)
        adzuna_status["jobsFound"] = len(adzuna_jobs)
        adzuna_status["signalOnlyJobsAdded"] = signal_jobs_added
        adzuna_status["companyBoardsLinked"] = careers_attached
        adzuna_status["duplicatesMerged"] = merged
        for job in adzuna_jobs:
            preserve_first_seen(existing, job, now)
            seen[job["id"]] = job
        statuses.append(adzuna_status)

    else:
        # Nunca consultar Adzuna ni descubrimiento de ATS en el catalogo directo.
        merged = 0
        adzuna_status = {"company": "Adzuna", "status": "disabled", "jobsFound": 0,
                         "reason": "Catalogo limitado a portales oficiales; agregadores desactivados."}
        statuses.append(adzuna_status)
        seen = {jid: j for jid, j in seen.items() if is_direct_job(j)}

    final = reconcile(existing, seen, outcomes, now)
    active = [j for j in final.values() if j["status"] == "active"]
    stale = [j for j in final.values() if j["status"] == "stale"]

    output = {
        "schemaVersion": 2,
        "sourcePolicy": "mixed" if include_aggregators else "direct-only",
        "lastUpdated": now,
        "companiesScanned": len(companies),
        "companiesSucceeded": succeeded,
        "companiesFailed": failed,
        "totalVfxJobs": len(active),
        "totalStale": len(stale),
        "jobsByAts": compute_jobs_by_ats(active),
        "jobsBySource": compute_jobs_by_source(active),
        "jobs": list(final.values()),
    }
    _write_json_atomic(jobs_file, output)
    _write_json_atomic(status_file, statuses)
    report = build_report(now, time.monotonic() - t_start, statuses, active, previous_report.get("history"), adzuna_status, merged)
    report["sourcePolicy"] = output["sourcePolicy"]
    report["excludedAggregatorRecords"] = excluded_aggregators
    _write_json_atomic(report_file, report)

    logger.info(f"Done. {len(active)} active ({report['summary']['officialJobs']} official, "
                f"{report['summary']['aggregatorJobs'] + report['summary']['signalJobs']} aggregator/signal), "
                f"{len(stale)} stale, from {succeeded}/{len(companies)} studios.")
    return output, statuses, report


if __name__ == "__main__":
    run()
