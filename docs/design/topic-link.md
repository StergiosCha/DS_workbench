# Initial nominative topics through LINK

The SMG classical and constructive grammars implement the proper-name fragment of thesis TOPIC STRUCTURE INTRODUCTION and TOPIC STRUCTURE REQUIREMENT, (2.93)-(2.94), physical PDF p.81. The contrast with subject adjunction is given in (2.100)-(2.101), pp.85-86.

Topic introduction creates a separate nominal tree connected by inverse LINK to the existing propositional axiom. Its root has storage address `0B`; `make(/\L)` creates it and `go(/\L)` moves the pointer there. Forward `go(\/L)` returns to the clause at `0`. `B` is an internal address convention for the predecessor, not a new linguistic modality. The workbench renders the semantic LINK from `0B` to `0`. Ordinary daughter closures exclude this edge.

An initial nominative proper name can complete this topic node. It keeps its nominative case and agreement labels; the case filter for a syntactic subject applies only to the ordinary unfixed-node branch. On returning to the clause, the lexical action adds `?SharedFo(name)`, the named implementation of the source's D-path requirement. A concrete matching formula must occur at a fixed address in the clause or a tree connected by forward LINK. The topic itself, unrelated context, unresolved placeholders and unfixed addresses cannot discharge this requirement.

Substitution retains the parsed name's person, gender and number, together with its declared sort. The topic is nonlocal to the clause, so it can supply a clitic or pro-drop subject referent without relaxing the existing local-reference restriction. This does not merge the topic with a clause node: nominative topic and accusative resumptive remain separate nodes.

The comma entry is a written boundary after a completed initial topic, as in (2.95). It cannot start a sentence or repeat at the same boundary. A comma is not required for the unpunctuated SVO alternative in (2.101), and it does not stand for a general model of prosody.

## Examples and evidence

`o γiorγos, ton ksero.` and `ο γιώργος, τον ξέρω.` use already approved words. They adapt (2.95) by replacing the source verb `γnorizo` with `ksero`. The meaning is `know(speaker, giorgos)` in both modes. The source's name and clause remain connected by a copy requirement.

`o γiorγos xtipise to γiani.` uses (2.50)'s vocabulary with the two strategies explicitly described in (2.100)-(2.101). Requesting multiple complete analyses in the workbench exposes subject MERGE and topic LINK, both with `hit(giorgos, giannis)`. A third derivation also uses adjunction for the object. These are structural derivations, not three independently established discourse readings. Each selected analysis has its own words, rules and operation playback.

The negative controls include incompatible feminine/plural clitics, a clause whose referents do not include the topic, incomplete clauses and misplaced boundary tokens. These checks establish the fragment's constraints; adapted test strings are not automatically added as source grammaticality judgments. Constructive positive meanings compile in Coq.

## Limits

The fragment supports one initial nominative proper-name topic. Common-noun topics, nested topics, a general CLLD/HTLD distribution, discourse suitability and prosodic conditions remain outside it. The forward-LINK copy test is available for later extensions, but these SMG grammars do not yet provide relative clauses or arbitrary embedded topic constructions. The full source sentences (2.95) and (2.97) still require additional reviewed vocabulary; their missing words are not treated as evidence of ungrammaticality.
