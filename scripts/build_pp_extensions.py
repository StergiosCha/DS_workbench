"""Generate destination arguments, PP LINKs and nominal simile LINKs.

Called by build_everyday_extensions after the everyday sections are rebuilt.
Similes consume a CN description, not an existentially introduced animal.
"""
import json


def extend(root, b, language):
    from build_everyday_extensions import block
    entity, prop, cn = ('object', 'Prop', 'CN') if b == 'mltt' else ('e', 't', 'cn')
    vp = f'arrow({entity},{prop})'
    actions = (root / 'lexical-actions.txt').read_text()
    profile = json.loads((root / 'semantics.json').read_text())
    blocks, rows = [], []
    profile['predicates']['manner_like'] = ['CN', 'Prop']
    profile['interpretation_notes'].append('Nominal similes compare a manner with a CN description. manner_like supplies no resemblance axioms, animal existence, or identification of the subject with the comparison noun. Selected goal frames and LINK location/path modifiers remain distinct; temporal and spatial inference is not supplied.')
    pp = rf'''postverbal-pp(PRED)
IF Ty({b}:{prop})
   complete
THEN go(\/1)
   semantic-pp(PRED)
ELSE abort'''
    comparison = pp.replace('postverbal-pp(PRED)', 'nominal-simile(UNUSED)').replace('semantic-pp(PRED)', 'semantic-comparison(manner_like)')
    blocks.append(pp)
    if language == 'en':
        # A/an in this construction introduces a comparison description. It
        # does not introduce an actual witness outside the simile operator.
        blocks.append(comparison.replace('\nELSE abort', '\n   put(?[+COMPARISON-ARTICLE])\nELSE abort'))
        rows.append('like nominal-simile none')
        blocks.append(rf'''simile-article(UNUSED)
IF ?Ty({b}:{cn})
   [+COMPARISON]
   ?[+COMPARISON-ARTICLE]
   ¬<\/0>Ex.x
   ¬<\/1>Ex.x
THEN delete(?[+COMPARISON-ARTICLE])
ELSE abort''')
        if b == 'classical':
            cn_body = block(actions, 'predicative-article').split('   make(\\/0)', 1)[1].rsplit('\nELSE abort', 1)[0]
            blocks[-1] = blocks[-1].replace('\nELSE abort', '\n   make(\\/0)' + cn_body + '\nELSE abort')
        rows += ['a simile-article none', 'an simile-article none']
        for prep, symbol in [('into', 'into_goal'), ('onto', 'onto_goal'), ('toward', 'toward_goal'), ('towards', 'toward_goal')]:
            profile['predicates'][symbol] = ['object', 'Prop']
            rows.append(f'{prep} postverbal-pp {symbol}')
        # Selected to/into frames are also available to lexical proposals;
        # PP adjuncts cannot satisfy their outstanding preposition requirement.
        for prep in ('to', 'into'):
            for suffix in ('', '-base'):
                blocks.append(block(actions, 'prepositional-on' + suffix).replace('prepositional-on', 'prepositional-' + prep).replace('ON-COMPLEMENT', prep.upper() + '-GOAL'))
            blocks.append(block(actions, 'on-complement').replace('on-complement', prep + '-goal-complement').replace('ON-COMPLEMENT', prep.upper() + '-GOAL'))
            rows.append(f'{prep} {prep}-goal-complement none')
        for form in ('go', 'goes', 'went'):
            rows.append(f'{form} prepositional-to go_to human object')
        profile['predicates']['go_to'] = ['human', 'object']
        profile['constants']['george'] = 'human'
        profile.setdefault('referents', {})['george'] = {'gender':'masc','number':'sg'}
        rows.append('george proper george human')
        for word, parent in [('peacock', 'animal'), ('stage', 'object')]:
            profile['subtyping'][word] = [parent]
            if b == 'classical':
                profile['predicates'][word] = ['object']
            rows.append(f'{word} noun {word}')
        profile['predicates']['wild'] = ['object']
        rows.append('wild adjective wild')
    else:
        # Inside a LINK complement, leave the CN pointer for ordinary upward
        # completion. The Greek clause-object entry's early return to the
        # clause would strand the new LINK application below it.
        common = block(actions, 'common-noun')
        tail = common.split('   semantic-thin\n', 1)[1].rsplit('\nELSE abort', 1)[0]
        # LexicalAction stores sequential IF segments, so close the first
        # segment before testing where the completed nominal should return.
        revised = common.split('   semantic-thin\n', 1)[0] + '   semantic-thin\nELSE abort\nIF </\\+>[+PP]\nTHEN do_nothing\nELSE ' + tail.strip()
        actions = actions.replace(common, revised)
        # Greek LINK complements need their own case-checked DP programs:
        # the original verb-object output filter expects a VP parent.
        for kind, original in [('definite', 'definite-acc'), ('indefinite', 'indefinite-acc')]:
            dp = block(actions, original).replace(original + '(', 'pp-' + kind + '(')
            dp = dp.replace(f'   put(?</\\0>Ty({b}:{vp}))\n', '')
            dp = dp.replace(f'IF ?Ty({b}:{entity})', f'IF ?Ty({b}:{entity})\n   [+PP-COMPLEMENT]')
            blocks.append(dp)
        for word, gender in [('τον','m'), ('την','f'), ('τη','f'), ('το','neut')]:
            rows.append(f'{word} pp-definite {gender}')
        for word, gender in [('έναν','m'), ('μια','f'), ('μία','f'), ('ένα','neut')]:
            rows.append(f'{word} pp-indefinite {gender}')
        # Bare σε and its contracted articles use the same complement subtree.
        greek_pp = pp.replace('   complete', '   complete\n   ¬<\\/1>[+SELECTS-SE]').replace('\nELSE abort', '\n   put([+PP-COMPLEMENT])\nELSE abort')
        blocks[0] = greek_pp
        rows.append('σε postverbal-pp at_location')
        profile['predicates']['at_location'] = ['object', 'Prop']
        definite = next(x for x in blocks if x.startswith('pp-definite('))
        body = definite.split('THEN ',1)[1].rsplit('\nELSE abort',1)[0]
        blocks.append(greek_pp.replace('postverbal-pp(PRED)', 'postverbal-pp-article(PRED,GENDER)').replace('\nELSE abort', '\n   ' + body + '\nELSE abort'))
        for form, gender in [('στο','neut'), ('στον','m'), ('στη','f'), ('στην','f')]:
            rows.append(f'{form} postverbal-pp-article at_location {gender}')
        # Selected destination: retain the same subject/clitic/case machinery
        # as a finite transitive, but require σε before the accusative DP.
        goal = rf'''verb-prepositional-se(PRED,SUBJ,PERSON)
IF ?Ty({b}:{prop})
   ¬[+VERB]
   ¬[+NA]
   ¬[+FUT]
THEN put([+VERB])
   put(Mood(Ind))
   build-transitive(PRED,SUBJ,PERSON,sg)
   go(\/1)
   go(\/0)
   put(?[+SE-GOAL])
   gofirst(?Ty({b}:{prop}))
ELSE abort'''
        blocks.append(goal)
        bare_goal = block(actions, 'verb-intransitive').replace('verb-intransitive(', 'verb-optional-se(')
        bare_goal = bare_goal.replace('   gofirst(?Ty', '   put([+SELECTS-SE])\n   gofirst(?Ty')
        blocks.append(bare_goal)
        goal_prep = rf'''se-goal(UNUSED)
IF ?Ty({b}:{entity})
   ?[+SE-GOAL]
   ¬Ex.Fo(x)
THEN delete(?[+SE-GOAL])
   put([+SE-GOAL])
ELSE abort'''
        blocks.append(goal_prep)
        rows.append('σε se-goal none')
        def_body = block(actions, 'definite-acc').split('THEN ',1)[1].rsplit('\nELSE abort',1)[0]
        blocks.append(goal_prep.replace('se-goal(UNUSED)', 'se-goal-article(GENDER)').replace('\nELSE abort', '\n   ' + def_body + '\nELSE abort'))
        for form, gender in [('στο','neut'), ('στον','m'), ('στη','f'), ('στην','f')]:
            # Prioritize the explicitly selected destination over a location
            # adjunct when both lexical frames can be explored.
            rows.insert(0, f'{form} se-goal-article {gender}')
        # Bare Greek simile nominals carry accusative agreement. Separate
        # gender branches keep adjective/noun agreement checked by DS.
        blocks.append(comparison.replace('nominal-simile(UNUSED)', 'nominal-simile(GENDER)').replace('\nELSE abort', '\n   put(Case(acc))\n   put(Gender(GENDER))\nELSE abort'))
        rows += [f'σαν nominal-simile {g}' for g in ('m','f','neut')]
        blocks.append(rf'''simile-article(GENDER)
IF ?Ty({b}:{cn})
   [+COMPARISON]
   Gender(GENDER)
   ¬[+ARTICLE]
   ¬<\/0>Ex.x
   ¬<\/1>Ex.x
THEN put([+ARTICLE])
ELSE abort''')
        for word, gender in [('έναν','m'), ('μια','f'), ('μία','f'), ('ένα','neut')]:
            rows.append(f'{word} simile-article {gender}')
        # Common nouns already check case and gender; refinement must project
        # nested Sigma witnesses when an adjective is stacked on another.
        if b == 'mltt':
            actions = actions.replace('sigma(x,A,PRED(x))', 'refine(A,PRED)')
        computational = root / 'computational-actions.txt'
        with computational.open('a') as f:
            f.write(r'''

anticipation-link
!completion
IF Ty(x)
   ¬[+REL]
   ¬Ex.?x
   </\L>Ex.x
THEN semantic-link
ELSE abort
''')
        # Small explicit inflection inventory for offline examples. Open-text
        # hypotheses can instantiate these same general templates for new words.
        for forms, symbol in [('μπαίνω μπαίνεις μπαίνει', 'enter'), ('μπήκα μπήκες μπήκε', 'enter'), ('πηγαίνω πηγαίνεις πηγαίνει', 'go'), ('πήγα πήγες πήγε', 'go')]:
            profile['predicates'][symbol + '_goal'] = ['object','object']
            profile['predicates'][symbol] = ['object']
            for person, (form, referent) in enumerate(zip(forms.split(), ('speaker','hearer','pro')), 1):
                rows += [f'{form} verb-prepositional-se {symbol}_goal {referent} {person}', f'{form} verb-optional-se {symbol} {referent} {person}']
        for nom, acc, symbol, gender in [('πίστα','πίστα','pista','f'), ('παγώνι','παγώνι','peacock','neut'), ('λιοντάρι','λιοντάρι','lion','neut')]:
            profile['subtyping'][symbol] = ['object']
            if b == 'classical':
                profile['predicates'][symbol] = ['object']
            rows += [f'{nom} common-noun {symbol} nom {gender}', f'{acc} common-noun {symbol} acc {gender}']
        for nom, acc, gender, symbol in [('άγριος','άγριο','m','wild'), ('άγρια','άγρια','f','wild'), ('άγριο','άγριο','neut','wild'), ('μεγάλος','μεγάλο','m','big'), ('μεγάλη','μεγάλη','f','big'), ('μεγάλο','μεγάλο','neut','big')]:
            profile['predicates'][symbol] = ['object']
            rows += [f'{nom} common-adjective {symbol} nom {gender}', f'{acc} common-adjective {symbol} acc {gender}']
    (root / 'lexical-actions.txt').write_text(actions + '\n\n' + '\n\n'.join(blocks) + '\n')
    with (root / 'lexicon.txt').open('a') as f:
        f.write('\n// Destination arguments and nominal simile LINKs.\n' + '\n'.join(dict.fromkeys(rows)) + '\n')
    (root / 'semantics.json').write_text(json.dumps(profile, ensure_ascii=False, indent=2) + '\n')
