import json
from Utilis.dk_scraper import extract_prop_from_candidate


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def gather_candidates(obj):
    """Mimic the walk behavior to collect candidate dicts from nested JSON."""
    out = []

    def walk(o):
        if isinstance(o, dict):
            out.append(o)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for it in o:
                walk(it)

    walk(obj)
    return out


def test_sample_parsing_basic():
    data = load_json('tests/samples/dk_sample.json')
    cands = gather_candidates(data)
    matched = False
    for c in cands:
        if c.get('playerName') and 'travis kelce' in c.get('playerName').lower():
            val = extract_prop_from_candidate(c, 'receiving')
            assert val == 3.5
            matched = True
    assert matched


def test_sample_parsing_2():
    data = load_json('tests/samples/dk_sample_2.json')
    cands = gather_candidates(data)
    matched = False
    for c in cands:
        if c.get('playerName') and 'travis kelce' in c.get('playerName').lower():
            val = extract_prop_from_candidate(c, 'receiving')
            assert val == 3.5
            matched = True
    assert matched


def test_sample_parsing_3():
    data = load_json('tests/samples/dk_sample_3.json')
    cands = gather_candidates(data)
    matched = False
    for c in cands:
        name = c.get('name') or (c.get('player') or {}).get('name')
        if name and 'travis kelce' in name.lower():
            val = extract_prop_from_candidate(c, 'receiving')
            assert val == 3.5
            matched = True
    assert matched
