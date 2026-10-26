"""Public source metadata, independent of the private user's profile."""
def enrich_sources(sources):
    for source in sources:
        name = source['name'].lower()
        if any(word in name for word in ('fundae', 'diplos', 'cntg', 'sidefx', 'coloso', 'animum')):
            categories = ['courses']
        elif any(word in name for word in ('hitmarker', 'indies', 'gamesjobs', 'artstation', 'stratos')):
            categories = ['vfx']
        elif any(word in name for word in ('veolia', 'adecco', 'cofrico', 'randstad', 'electricista', 'mantenimiento', 'instalador', 'electromec')):
            categories = ['electricity']
        elif 'xunta' in name:
            categories = ['programming', 'electricity']
        else:
            categories = ['programming']
        ats = next((label for label in ('Workable', 'Recruitee', 'SuccessFactors', 'SmartRecruiters', 'Viterbit') if label.lower() in name), None)
        source.update(categories=categories, platform=ats or ('Formación' if categories == ['courses'] else 'Portal / web pública'),
                      sourceKind='ats' if ats else 'training' if categories == ['courses'] else 'public-portal')
    return sources
