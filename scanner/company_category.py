import re

KNOWN_AAA_ALIASES = [
    "electronic arts", "ea sports", "ea games", "ea",
    "activision", "blizzard", "activision blizzard", "king",
    "ubisoft", "take-two", "take two interactive", "rockstar",
    "2k", "bethesda", "zenimax", "id software",
    "microsoft", "xbox game studios", "xbox", "bungie",
    "343 industries", "turn 10", "the coalition", "ninja theory",
    "obsidian", "inxile", "compulsion games", "playground games",
    "mojang", "sony interactive entertainment", "playstation studios",
    "naughty dog", "insomniac", "guerrilla", "sucker punch",
    "santa monica studio", "media molecule", "polyphony digital",
    "bend studio", "firesprite", "nixxes", "housemarque",
    "nintendo", "square enix", "eidos montreal", "crystal dynamics",
    "io interactive", "capcom", "konami", "bandai namco", "sega",
    "atlus", "fromsoftware", "from software", "cd projekt",
    "warner bros games", "warner bros. games", "netherrealm",
    "rocksteady", "monolith", "riot games", "tencent", "netease",
    "epic games", "valve", "codemasters", "criterion",
    "respawn", "dice", "ripple effect", "motive studio", "motive studios",
    "bioware", "maxis", "rare", "double fine", "certain affinity",
    "amazon games", "niantic", "supercell", "scopely", "zynga",
    "playtika", "rovio", "gameloft", "wb games", "paradox interactive",
    "embracer", "keywords studios", "digital extremes", "remedy entertainment",
    "larian studios", "team17", "devolver digital",
]

_COMPILED = [re.compile(rf"\b{re.escape(alias)}\b", re.IGNORECASE) for alias in KNOWN_AAA_ALIASES]


def is_known_aaa_studio(company_name: str) -> bool:
    name = (company_name or "").lower()
    if not name:
        return False
    return any(pattern.search(name) for pattern in _COMPILED)


def classify_company_category(company_name: str, manual_override: str | None = None) -> str:
    if manual_override in ("aaa", "indie"):
        return manual_override
    return "aaa" if is_known_aaa_studio(company_name) else "indie"
