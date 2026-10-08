"""Native polar questions, local reflexives and contextual polarity answers."""
import json


def extend(root, backend):
    b = backend
    e, t = ('object', 'Prop') if b == 'mltt' else ('e', 't')
    vp = f'arrow({e},{t})'
    actions = rf'''

// Polar questions preserve their propositional content with an explicit act label.
polar-do(UNUSED)
IF Tn(0)
   ?Ty({b}:{t})
   ¬<\/0>Ex.x
   ¬<\/1>Ex.x
   ¬?[+COMP]
THEN put([+POLAR-QUESTION])
   make(\/1)
   go(\/1)
   put(?Ty({b}:{vp}))
   put([+DO])
   put(?[+BARE-VERB])
   go(/\1)
   make(\/0)
   go(\/0)
   put(?Ty({b}:{e}))
ELSE abort

question-boundary(UNUSED)
IF Tn(0)
   Ty({b}:{t})
   [+POLAR-QUESTION]
   ¬[+QUESTION-PUNCTUATED]
   complete
THEN put([+QUESTION-PUNCTUATED])
ELSE abort

local-reflexive(ROLE)
IF ?Ty({b}:{e})
   ¬Ex.Fo(x)
   ¬<\/0>Ex.x
   ¬<\/1>Ex.x
THEN semantic-reflexive(ROLE)
ELSE abort

polarity-answer(POLARITY)
IF Tn(0)
   ?Ty({b}:{t})
   ¬<\/0>Ex.x
   ¬<\/1>Ex.x
THEN semantic-answer(POLARITY)
ELSE abort
'''
    rows = ['do polar-do none', 'does polar-do none', 'did polar-do none', '? question-boundary none',
            'yes polarity-answer yes', 'no polarity-answer no']
    rows += [f'{word} local-reflexive {word}' for word in ('myself', 'yourself', 'himself', 'herself', 'itself', 'themselves')]
    # A reviewed verb for offline dialogue presets; dictionary/model templates
    # can supply other transitive predicates without changing the binding rule.
    for word in ('burn', 'burns', 'burned', 'burnt'):
        rows.append(f'{word} transitive burn human object')
    rows += ['burn transitive-base burn human object', 'burn noun burn_injury']
    with (root / 'lexical-actions.txt').open('a') as f:
        f.write(actions)
    with (root / 'lexicon.txt').open('a') as f:
        f.write('\n// Polar questions and shared-turn subject binding.\n' + '\n'.join(rows) + '\n')
    profile = json.loads((root / 'semantics.json').read_text())
    profile['predicates']['burn'] = ['human', 'object']
    profile['subtyping']['burn_injury'] = ['object']
    if b == 'classical':
        profile['predicates']['burn_injury'] = ['object']
    profile['interpretation_notes'].append('Polar do/does/did questions retain a labelled query content; no tense or full agreement semantics is supplied. Local reflexives bind to the clause subject, with speaker/addressee identities evaluated at each word. Yes affirms the previous complete query content; No negates it. These are content interpretations, not grounding or truth judgments.')
    (root / 'semantics.json').write_text(json.dumps(profile, ensure_ascii=False, indent=2) + '\n')
