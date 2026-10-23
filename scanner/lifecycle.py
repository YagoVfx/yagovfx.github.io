"""
Ciclo de vida de las ofertas entre escaneos (spec §4, DATA-01 y DATA-02).

CAUSA RAÍZ corregida: antes, toda oferta conocida que no apareciera en el
escaneo actual se marcaba «closed» y se le sobrescribía lastSeen, aunque su
fuente hubiera FALLADO (timeout, bloqueo, 422...). Eso cerraba vacantes
reales (p. ej. 2K «Senior VFX Artist» tras «No response from 2k.com/careers»)
y destruía la fecha real de última detección de las ya cerradas.

Reglas ahora:
  1. Una oferta solo se cierra tras un escaneo EXITOSO y COMPLETO de SU fuente.
  2. Fallo, bloqueo, fuente omitida o resultado truncado ≠ cierre: la oferta
     conserva su estado; si lleva demasiado sin verse pasa a «stale»
     (se muestra como sin verificar), nunca a «closed».
  3. Fuente oficial fiable (API estructurada): 1 ausencia → closed.
     Fuente poco fiable (HTML heurístico) o agregador: hacen falta varias
     ausencias seguidas (MISS_TO_CLOSE) y, hasta entonces, «stale».
  4. Adzuna jamás cierra ni invalida una vacante de un ATS oficial: cada
     oferta se reconcilia únicamente con el resultado de su propia fuente.
  5. lastSeen solo se actualiza cuando la oferta se ve de verdad. Las cerradas
     no se tocan; guardan closedAt. Se podan pasados RETAIN_CLOSED_DAYS.

Estados: active → stale → closed; closed → active si reaparece (reapertura).
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

MISS_TO_CLOSE_RELIABLE = 1
MISS_TO_CLOSE_UNRELIABLE = 3
STALE_AFTER_DAYS_ON_FAILURE = 14
RETAIN_CLOSED_DAYS = 30

AGGREGATOR_SOURCE = "adzuna"


def _parse(ts: str | None):
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def _days_between(a: str | None, b: str | None) -> float | None:
    da, db = _parse(a), _parse(b)
    if not da or not db:
        return None
    return (db - da).total_seconds() / 86400


def source_key(job: dict) -> str:
    """Clave de la fuente que debe confirmar la existencia de la oferta."""
    if job.get("ats") in ("adzuna", "adzuna-signal") or job.get("viaAggregator"):
        # Las señales (sig-*) dependen de que Adzuna siga detectando a la empresa.
        return AGGREGATOR_SOURCE
    return f"company:{job.get('company', '')}"


def reconcile(existing: dict[str, dict], seen: dict[str, dict],
              outcomes: dict[str, dict], now: str) -> dict[str, dict]:
    """Devuelve el mapa final id→oferta.

    existing  ofertas conocidas del escaneo anterior.
    seen      ofertas vistas ahora (ya enriquecidas, con firstSeen preservado).
    outcomes  por source_key: {"ok": bool, "reliable": bool, "complete": bool}.
              Una fuente ausente del dict se trata como NO exitosa.
    """
    result: dict[str, dict] = {}

    for jid, job in seen.items():
        job = dict(job)
        job["status"] = "active"
        job["missCount"] = 0
        job["lastSeen"] = now
        job.pop("closedAt", None)
        result[jid] = job

    for jid, old in existing.items():
        if jid in result:
            continue
        job = dict(old)
        if job.get("status") == "closed":
            # No tocar lastSeen; asegurar closedAt (migración de registros antiguos).
            job.setdefault("closedAt", job.get("lastSeen") or now)
            result[jid] = job
            continue

        out = outcomes.get(source_key(job))
        if out and out.get("ok") and out.get("complete", True):
            misses = int(job.get("missCount", 0)) + 1
            job["missCount"] = misses
            limit = MISS_TO_CLOSE_RELIABLE if out.get("reliable", True) else MISS_TO_CLOSE_UNRELIABLE
            if misses >= limit:
                job["status"] = "closed"
                job["closedAt"] = now
            else:
                job["status"] = "stale"
        else:
            # Fuente fallida/truncada/omitida: NO se cierra. Se anota y, si lleva
            # mucho sin verse, queda como stale (sin verificar).
            job["lastError"] = (out or {}).get("error") or "fuente no escaneada con éxito"
            age = _days_between(job.get("lastSeen"), now)
            if age is not None and age > STALE_AFTER_DAYS_ON_FAILURE and job.get("status") == "active":
                job["status"] = "stale"
        result[jid] = job

    return prune_closed(result, now)


def prune_closed(jobs: dict[str, dict], now: str) -> dict[str, dict]:
    kept = {}
    for jid, job in jobs.items():
        if job.get("status") == "closed":
            age = _days_between(job.get("closedAt"), now)
            if age is not None and age > RETAIN_CLOSED_DAYS:
                continue
        kept[jid] = job
    return kept


# ───────────────────── deduplicación oficial vs agregador ─────────────────────

def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def merge_aggregator_into_official(aggregator_jobs: list[dict], official: dict[str, dict],
                                   names_match) -> tuple[list[dict], int]:
    """DATA-02: si una vacante aparece en el ATS oficial y en Adzuna, gana la
    evidencia oficial; la oferta del agregador se descarta y la oficial anota
    que además la vio Adzuna (alsoSeenIn). Clave secundaria conservadora:
    empresa (coincidencia difusa) + título normalizado idéntico.
    Devuelve (agregador_sin_duplicados, nº fusionadas)."""
    by_title: dict[str, list[dict]] = {}
    for job in official.values():
        if job.get("sourceKind") in ("aggregator", "signal") or job.get("viaAggregator"):
            continue
        if job.get("status") == "closed":
            continue
        by_title.setdefault(_norm(job.get("title", "")), []).append(job)

    kept, merged = [], 0
    for ag in aggregator_jobs:
        twins = [o for o in by_title.get(_norm(ag.get("title", "")), [])
                 if names_match(o.get("company", ""), ag.get("company", ""))]
        if twins:
            for t in twins:
                also = set(t.get("alsoSeenIn") or [])
                also.add("adzuna")
                t["alsoSeenIn"] = sorted(also)
            merged += 1
        else:
            kept.append(ag)
    return kept, merged
