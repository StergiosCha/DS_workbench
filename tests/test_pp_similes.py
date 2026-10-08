"""Destination arguments and nominal comparison LINKs in both native backends."""
from copy import deepcopy
import shutil

import pytest

from dynamicsyntax import icp
from dylan import lexical_provider
from dylan.action.meta.element import reset_all_meta_bindings
from dylan.assisted_parsing import compile_entries
from dylan.corpus import compile_coq
from dylan.workbench_api import parse_request


@pytest.fixture(autouse=True)
def bindings():
    reset_all_meta_bindings()
    yield
    reset_all_meta_bindings()


def run(text, language, backend, **kw):
    return parse_request({'sentence': text, 'grammar': f'2026-{language}-{backend}', **kw}, _trace=False)


@pytest.mark.parametrize('backend', ['classical', 'mltt'])
@pytest.mark.parametrize('language,text,meaning', [
    ('smg', 'Ο Γιώργος μπήκε στην πίστα σαν άγριο παγώνι,', 'enter_goal(giorgos,'),
    ('smg', 'Η Μαρία μπήκε στο σπίτι σαν ένα μεγάλο άγριο λιοντάρι.', 'enter_goal(maria,'),
    ('smg', 'Ο Γιάννης πήγε σε ένα πάρκο σαν σκύλο.', 'go_goal(giannis,'),
    ('smg', 'Μπήκα στην πίστα σαν παγώνι.', 'enter_goal(speaker,'),
    ('smg', 'Ο Γιώργος περπατάει στο πάρκο σαν άγριο παγώνι.', 'at_location('),
    ('smg', 'Ο Γιώργος περπατάει σε ένα πάρκο.', 'at_location('),
    ('smg', 'Ο Γιώργος περπατάει σαν άγριο παγώνι στην πίστα.', 'at_location('),
    ('smg', 'Ο Γιώργος εξετάζει τον ασθενή σαν γιατρό.', 'examine('),
    ('english', 'George walks onto the stage like a wild peacock.', 'onto_goal('),
    ('english', 'Mary walks into the park like a black dog.', 'into_goal('),
    ('english', 'John walks toward the park like a dog.', 'toward_goal('),
    ('english', 'John goes to the park like a wild peacock.', 'go_to(john,'),
    ('english', 'A man walks like a dog in a park.', 'manner_like('),
    ('english', 'John walks like a black wild peacock.', 'manner_like('),
    ('english', 'John examines a patient like a doctor.', 'examine('),
])
def test_varied_constructions_without_llm(monkeypatch, backend, language, text, meaning):
    def forbidden(*a, **kw):
        pytest.fail('The offline construction regression must not call a model')
    monkeypatch.setattr(lexical_provider, 'propose', forbidden)
    r = run(text, language, backend)
    assert r['complete'], r['failure']
    assert meaning in r['words'][-1]['normalized']
    assert r['derivation']['actions']
    assert not any(n['requirements'] for n in r['words'][-1]['nodes'])
    if 'σαν' in text or 'like' in text:
        assert 'manner_like(' in r['words'][-1]['normalized']
        assert any('L' in n['id'] for n in r['words'][-1]['nodes'])
    if backend == 'mltt' and shutil.which('coqc'):
        assert compile_coq(r['coq'], {}) == 'passed'


@pytest.mark.parametrize('backend', ['classical', 'mltt'])
@pytest.mark.parametrize('language,text', [
    ('smg', 'Ο Γιώργος μπήκε στην.'),
    ('smg', 'Ο Γιώργος μπήκε στον πίστα.'),
    ('smg', 'Ο Γιώργος μπήκε την πίστα.'),
    ('smg', 'Ο Γιώργος περπατάει σαν.'),
    ('smg', 'Ο Γιώργος περπατάει σαν άγρια παγώνι.'),
    ('smg', 'Ο Γιώργος περπατάει σαν άγριο γάτα.'),
    ('smg', 'Ο Γιώργος περπατάει σαν ένας παγώνι.'),
    ('smg', 'Ο Γιώργος περπατάει στο.'),
    ('smg', 'Ο Γιώργος περπατάει σε ο πάρκο.'),
    ('english', 'John walks into.'),
    ('english', 'John goes the park.'),
    ('english', 'John goes in the park.'),
    ('english', 'John walks like.'),
    ('english', 'John walks like a wild.'),
    ('english', 'John walks like dog.'),
    ('english', 'John walks like a a dog.'),
])
def test_unfilled_frames_and_agreement_fail(backend, language, text):
    r = run(text, language, backend)
    assert not r['complete'], r['words'][-1]['normalized']
    assert r['diagnostics']['judgment']['status'] == 'not_assessed'


@pytest.mark.parametrize('backend', ['classical', 'mltt'])
def test_comparison_is_a_description_not_an_animal_witness(backend):
    r = run('John walks like a wild peacock.', 'english', backend)
    assert r['complete']
    meaning = r['words'][-1]['normalized']
    assert meaning.startswith('manner_like(') and meaning.endswith(', walk(john))')
    if backend == 'mltt':
        assert 'Σ x:peacock. wild(x)' in meaning
        assert 'Parameter manner_like : Type -> Prop -> Prop.' in r['coq']
        assert not r['words'][-1]['context_assumptions']
    else:
        assert 'peacock(' in meaning and 'wild(' in meaning
        assert 'ε' not in meaning and 'ι' not in meaning
    assert 'peacock(john)' not in meaning


def proposal(surface, lemma, template, domains, case='none', gender='none', person='none'):
    finite = template in {'prepositional-se', 'prepositional-into', 'prepositional-to'}
    return dict(surface=surface, lemma=lemma, template=template, domains=domains,
                case=case, gender=gender, person=person,
                number='sg' if case != 'none' or person != 'none' or template == 'noun' else 'none',
                verb_form='finite' if finite else 'none',
                evidence='Diagnostic lexical hypothesis; DS must build the destination and comparison.')


@pytest.mark.parametrize('backend', ['classical', 'mltt'])
@pytest.mark.parametrize('language,text,vocabulary,compiled', [
    ('smg', 'Ο Γιώργος όρμησε στην αυλή σαν ήρεμο λιοντάρι.', [
        proposal('όρμησε','ορμάω','prepositional-se',['human','object'],person='3'),
        proposal('αυλή','αυλή','noun',['object'],'acc','f'),
        proposal('ήρεμο','ήρεμος','adjective',['object'],'acc','neut'),
    ], 'verb-prepositional-se'),
    ('english', 'Mary sauntered into the atrium like a graceful gazelle.', [
        proposal('sauntered','saunter','prepositional-into',['human','object']),
        proposal('atrium','atrium','noun',['object']),
        proposal('graceful','graceful','adjective',['object']),
        proposal('gazelle','gazelle','noun',['animal']),
    ], 'prepositional-into'),
    ('english', 'Mary ambles to the stage like a peacock.', [
        proposal('ambles','amble','prepositional-to',['human','object']),
    ], 'prepositional-to'),
])
def test_new_model_vocabulary_uses_the_same_rules(monkeypatch, backend, language, text, vocabulary, compiled):
    # Isolate model compilation from accidental dictionary coverage of these
    # forms. Real-provider checks additionally exercise the normal seed path.
    monkeypatch.setattr('dylan.assisted_parsing.expand', lambda *a, **kw: {'entries':[], 'notices':[]})
    calls = []
    def provider(context, spec, **kw):
        calls.append(context)
        return {'entries':[e for e in vocabulary if e['surface'] in context['requested']]}, {'provider':'fixture','model':'fixture'}
    monkeypatch.setattr(lexical_provider, 'propose', provider)
    r = run(text, language, backend, lexical_mode='assisted')
    assert r['complete'], (r['failure'], r['lexical']['notices'])
    assert calls and all(c['backend'] == backend for c in calls)
    assert any(e['template'] == compiled for e in r['lexical']['entries'])
    assert 'manner_like(' in r['words'][-1]['normalized']
    if backend == 'mltt' and shutil.which('coqc'):
        assert compile_coq(r['coq'], {}) == 'passed'


def test_simile_function_word_is_protected_and_bad_frame_is_atomic():
    p = icp('2026-smg-mltt')
    before = deepcopy(p.semantic_profile)
    try:
        for entry in [proposal('σαν','σαν','noun',['object'],'acc','neut'),
                      proposal('όρμησε','ορμάω','prepositional-se',['object'],person='3')]:
            with pytest.raises(ValueError):
                compile_entries(p, {'entries':[entry]}, [entry['surface']], 'el')
        assert p.semantic_profile == before
    finally:
        p.close()


def test_adjective_domain_feedback_preserves_accusative_agreement():
    p = icp('2026-smg-mltt')
    try:
        adjective = proposal('ήρεμο', 'ήρεμος', 'adjective', ['human'], 'acc', 'neut')
        with pytest.raises(ValueError, match='Keep case=acc and gender=neut; change only the domains array'):
            compile_entries(p, {'entries':[adjective]}, ['ήρεμο'], 'el')
        adjective['domains'] = ['object']
        actions, _ = compile_entries(p, {'entries':[adjective]}, ['ήρεμο'], 'el')
        assert actions[0][1].parameters[1:] == ('acc', 'neut')
    finally:
        p.close()


@pytest.mark.parametrize('backend', ['classical', 'mltt'])
@pytest.mark.parametrize('language,paragraph', [
    ('smg', 'Ο Γιώργος μπήκε στην πίστα σαν άγριο παγώνι. Η Μαρία πήγε στο πάρκο. Ο Γιάννης περπατάει σαν λιοντάρι.'),
    ('english', 'George walks onto the stage like a wild peacock. Mary goes to the park. John walks like a dog.'),
])
def test_paragraphs_preserve_every_sentence(backend, language, paragraph):
    r = parse_request({'paragraph':paragraph, 'grammar':f'2026-{language}-{backend}'})
    assert r['coverage'] == {'complete':3,'total':3,'failed':0,'all_complete':True}
    assert 'manner_like(' in r['sentences'][0]['result']['words'][-1]['normalized']
