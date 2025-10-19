import json
import os
from Utilis.provider_parser import extract_prop_from_candidate


def load_sample(name: str):
    path = os.path.join(os.path.dirname(__file__), 'samples', name)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def test_provider_parser_sample_1():
    sample = load_sample('dk_sample.json')
    # samples are arrays of candidates; pick first candidate
    if isinstance(sample, list):
        cand = sample[0]
    else:
        # if top-level dict with players, pick a value
        cand = list(sample.values())[0]
    val = extract_prop_from_candidate(cand, 'receptions')
    assert val == 3.5


def test_provider_parser_sample_2():
    sample = load_sample('dk_sample_2.json')
    cand = sample[0] if isinstance(sample, list) else list(sample.values())[0]
    val = extract_prop_from_candidate(cand, 'receiving')
    assert val == 3.5


def test_provider_parser_sample_3():
    sample = load_sample('dk_sample_3.json')
    cand = sample[0] if isinstance(sample, list) else list(sample.values())[0]
    val = extract_prop_from_candidate(cand, 'recs')
    assert val == 3.5
