# SMG/GSG clitic system — extraction from Chatzikyriakidis (2010) chs. 3, 6

Verbatim-transcribed lexical entries and constraint machinery for the Greek grammars.
ASCII: <down0>/<down1> existential daughter modalities; <down1+> Kleene-plus functor
daughter; [down1+] universal (box) one-or-more 1-steps; [down+] box any-path below;
<up0><up1+> locally-unfixed address (one 0-step then 1-spine, PLUS not star);
<up*> regular unfixed; Tn(a) treenode; ?Ex.Fo(x)/?Ex.Tn(x) existential requirements;
`|` inclusive disjunction of triggers; parenthesized (make/go) pair = optional extra
level when situation nodes are assumed. U/V metavariables; subscripts = substitution
presuppositions (U_x = 3rd person; U_Sp' speaker; U_Hr' hearer). gofirst(?Ty(t)) =
pointer to first ?Ty(t) above; freshput = put fresh value.

## (a) Clitic lexical entries

(3.47) Proclisis trigger skeleton (all non-imperative clitic entries):
IF ?Ty(t) THEN IF [down1+]?Ty(x) THEN ... ELSE abort ELSE abort
— every functor node below still bears only a type REQUIREMENT (no verb parsed yet).
Trivially true when no functor nodes exist; licenses clitics after na/tha, preverbal
unfixed NPs, LINKed topics.

(3.64) 3rd acc clitic (SMG+GSG), FIXED direct-object structure:
IF ?Ty(t) THEN IF [down1+]?Ty(x) THEN
  make(<down1>); go(<down1>); make(<down0>); go(<down0>);
  put(Ty(e), Fo(U_x), ?Ex.Fo(x)); gofirst(?Ty(t))
ELSE abort ELSE abort
NO bottom restriction [down]⊥ on the node — deliberately, so clitic doubling by MERGE
of a full NP is possible; strong pronouns DO carry [down]⊥ and cannot double.

(3.72) Same with situation nodes: one extra make(<down1>); go(<down1>) pair first.

(3.73) 3rd acc incl. imperatives: trigger becomes [down1+]?Ty(x) | Mood(Imp).
After an imperative verb, [down1+]?Ty(x) fails but Mood(Imp) holds → enclisis; the
clitic's actions land on the already-built object node.

(3.82) Imperative verb trigger: IF ?Ty(t) THEN IF [down+]?Ex.Tn(x) THEN ... —
ALL nodes below must be unfixed (bear ?Ex.Tn(x)); blocks proclisis with imperatives,
imperatives after na/tha/negation (which build fixed ?Ty(e_s)), and after auxiliaries.

(3.100) Genitive (dative) clitics SMG+GSG, indicatives — LOCALLY UNFIXED:
IF ?Ty(t), Tn(a) THEN IF [down+]?Ex.Tn(x) THEN
  (make(<down1>); go(<down1>);)
  make(<down1+>); go(<down1+>); make(<down0>); go(<down0>);
  put(<up0><up1+>Tn(a)); put(Ty(e), Fo(U), ?Ex.Fo(x)); put(?Ex.Tn(x));
  gofirst(?Ty(t))
ELSE abort ELSE abort
Trigger [down+]?Ex.Tn(x] = NO fixed nodes below at all → strict DAT-ACC order in
indicatives (a parsed acc clitic has built fixed 01/010 → *ACC-DAT aborts).
Kleene PLUS in <up0><up1+> excludes fixing at the subject (00) node: clitics are
never subjects.

(3.102) SMG genitive incl. imperatives: trigger [down+]?Ex.Tn(x) | Mood(Imp) →
both orders in SMG imperatives (dos mu to / dos to mu).

(3.104) GSG genitive incl. imperatives: second disjunct is the CONJUNCTION
Mood(Imp), [down1+][down0]?Ty(x) (no fixed object yet) → only DAT-ACC in GSG
imperatives.

(3.117) SMG auxiliary exo 'have.1SG': builds complex situation node (present-perfect
semantics with Fo(lambdaP.(epsilon,P)) cn_s spine, freshput(s), Fo(R) reference time,
e OVERLAP s_now AND State'(e) AND LOC(e,e')), subject node Ty(e), Fo(U_Speaker'),
?Ex.Fo(x); pointer LEFT AT ?Ty(e_s -> t) — so clitics cannot follow (their IF ?Ty(t)
fails) → obligatory climbing 'to exo desi', *'exo to desi'. No 011 metavariable →
no VP-ellipsis with SMG auxiliaries.

(3.122) GSG restructuring sotzo 'can': like exo but modal (tau over ability worlds
W_ab), plus 011 predicate node with Ty value and Fo(V) metavariable (VP-ellipsis OK);
pointer returns to ?Ty(t) BUT both clitic triggers now fail after it parses
([down1+]?Ty(x) fails: predicate node typed; [down+]?Ex.Tn(x) fails: fixed nodes) →
clitic must PRECEDE → obligatory climbing 'to sotzo vorasi', multiple climbing
'to sotzo spiccetsi tse di'; intermediate/low placement starred.
Derivation of 'to sotzo vorasi': clitic at ?Ty(t) builds object node Fo(V_x) (3.126);
sotzo (3.127); infinitive vorasi projects verbal type + Fo in 0111 and re-builds the
object ?Ty(e), THINNED against the clitic's Ty(e) (3.128); ELIMINATION, THINNING,
COMPLETION, SUBSTITUTION complete (3.129).

Ch. 6 (Chatzikyriakidis & Kempson 2009 system):
(6.44) Spanish me/te (syncretized 1/2): locally unfixed, Fo(U_Sp'/Hr'), no filter;
trigger [down1+]?Ty(x) | Mood(Imp).
(6.45) Spanish le (dative): same, Fo(U_x) person-unrestricted.
(6.46) Spanish lo (3rd acc): FIXED (like 3.73).
(6.49) SMG 1st/2nd ACC clitics: locally unfixed + CASE OUTPUT FILTER
?<up0>(Ty(e -> t)) (must end up direct object; fixing not incremental). Motivation:
sg 1/2 are non-syncretic (me/mu, se/su) but pl mas/sas are case-syncretic → whole
1/2 paradigm kept underspecified with a filter.
(6.62) Pontic cluster 'm ese(n)' as ONE entry: trigger <down1+>Ty(x) (PG is enclitic;
verb must have parsed); m FIXES at indirect object, ese(n) locally unfixed → only one
unfixed node → 1+2 clusters OK while *3+3 out (both unfixed → collapse).
(6.71) Italian/Spanish dative with ethical-dative LINK escape — the only entry with
contentful ELSE: ELSE make(<L>); go(<L>); put(Ty(e), Fo(U), ?Ex.Fo(x)); go(<L-1>) —
LINKed type-e node with NO copy requirement = ED escapes the PCC. SMG EDs do NOT
escape (argumental, Marten-style optional arguments Ty(e* -> ...)).

## (b) PCC as tree-growth constraint

Two unfixed nodes with the SAME underspecified address type collapse into one node
(decorations unify); distinct address types (<up*>Tn(a) vs <up0><up1+>Tn(a)) coexist.
Datives + 1/2-acc clitics build LOCALLY UNFIXED nodes; 3rd-acc builds FIXED nodes.
*me te / *mu se: both locally unfixed → collapse → one node with Fo(U_Sp'), Fo(V_Hr'),
two incompatible substitution presuppositions → substitution cannot satisfy both →
crash. mu to fine (unfixed + fixed). Strong pronouns escape: fixed postverbal or
REGULAR unfixed preverbal (different address type). LOCAL *ADJUNCTION is NOT a free
computational rule in these languages — locally unfixed nodes are built only lexically
by clitic entries. Also *two-acc clusters: two fixed builds on the same 010 node give
two incompatible Fo metavariable restrictions (tree 3.57).

### Retry rollback in the implementation

Implementation correction (2026-10-07): a failed IF/THEN branch must restore its
tree and pointer before trying another metavariable binding. Previously a failed
second clitic could leave the pointer at `0P`; the retry rebound the clause
address there and created `0PP`. In `του με έδωσε` this eventually left an
unresolved node, so completion was false but all words had been consumed. This
was an engine rollback bug, not an additional licensed clitic strategy.
`IfThenElse.exec_tuple_context` now restores the pre-branch tree in place before
backtracking. Both native backends stop at `με`; `του το έδωσε` and
`της τον έδωσε` still complete. The UI identifies the clitic-reading PCC failure
and displays the surviving prefix. This diagnosis does not invent an independent
corpus judgment. Open-text assistance does not request a lexical repair after
this diagnosed failure; model proposals cannot override the clitic constraints.
For ambiguous `σε`, the explanation explicitly distinguishes its clitic reading
from its prepositional entries. Core witness-backtracking tests and the real-API
browser check in `scripts/check_pcc_browser.py` cover this correction.

## (c) Extra machinery beyond thesis ch. 2

1. Mood(Imp) feature on root ?Ty(t), projected by imperative verbs.
2. Disjunctive `|` and conjunctive triggers inside lexical IF.
3. [+NEG] feature + negation builds fixed ?Ty(e_s) (blocks negated imperatives:
   *mi dos mu to → mi mu to dosis).
4. Imperative trigger [down+]?Ex.Tn(x) (first-fixed-node restriction).
5. Kleene-plus locally-unfixed modality make(<down1+>) / <up0><up1+>Tn(a);
   with situation nodes <down1><down1+><down0>.
6. Situation-node vocabulary: ?Ty(e_s), cn_s spine, Fo(R), freshput(s)/(w_i, s_i),
   s_now, LOC, OVERLAP, W_ab. (MLTT adaptation: Σ replaces ε/τ here — see
   thesis-full-system.md §7.)
7. Case typology (§6.2.1): constructive case (puts fixed Tn), output-filter case
   (?<up0>Ty(e->t) etc.), underspecified case (nothing), LINK strategy (EDs).
8. gofirst(?Ty(t)); ?Ex.Tn(x) standard on unfixed nodes.
9. Chunk parsing (fn.34 p.137): verb+clitics scanned as one chunk; general rules
   (MERGE etc.) may not apply mid-chunk.
10. Every newly built node automatically carries ?Ty(x) (fn.24 p.120).

## (d) Worked SVO derivation ('O Yanis to filise')

AXIOM → *ADJUNCTION (unfixed subject) → scan 'o Yanis' (Ty(e), Fo(Yanis'),
?Ex.Tn(x)) → COMPLETION to ?Ty(t) → clitic 'to' via (3.64): fixed 01 + 010 with
Ty(e), Fo(U_x), ?Ex.Fo(x); gofirst → verb 'filise' (pro-drop template: subject
metavariable node, 011 predicate, object ?Ty(e) THINNED against clitic's Ty(e)) →
MERGE unfixed subject with subject node → SUBSTITUTION for Fo(U_x) (3rd-person
restrictor) → ELIMINATION/THINNING/COMPLETION bottom-up → Ty(t), no outstanding
requirements.
Imperative 'dos to': imperative verb first (trigger [down+]?Ex.Tn(x) OK at bare
AXIOM), projects template + Mood(Imp); 'to' parses via Mood(Imp) disjunct onto the
built object node. Cluster 'mu to dosane': mu (3.100, no fixed nodes) → to (3.64,
[down1+]?Ty(x) still true) → verb; *'to mu dosane' crashes on mu's [down+]?Ex.Tn(x).

## (e) SMG grammar checklist

Word classes: 3rd-acc clitics (fixed, no bottom restriction, Fo(U_x));
genitive clitics all persons (locally unfixed, ?Ex.Tn(x), no filter, U_Sp'/U_Hr'
for 1/2); 1/2-acc clitics (locally unfixed + ?<up0>(Ty(e->t)) filter);
imperative verbs ([down+]?Ex.Tn(x) trigger + Mood(Imp) projection);
na/tha particles and negation den/min (fixed ?Ty(e_s) / [+NEG]);
auxiliary exo (pointer parked at ?Ty(e_s->t));
pro-drop verb templates (2.12) with subject metavariable; case-filter NPs
(nominative ?<up0>Ty(t), accusative ?<up0>Ty(e->t)); pu-relativizer (2.83).
Parser must provide: unfixed bookkeeping keyed by address TYPE with
collapse-on-identity; box-trigger evaluation over partial trees (vacuously true on
empty domains); MERGE respecting bottom restrictions and output filters;
metavariable presupposition clash → substitution failure; LOCAL *ADJUNCTION not
free; standard rule set per thesis-full-system.md.

Source: /Users/graogro/Dropbox/chatzikyriakidis-phdthesis.pdf pp. 112-161, 258-289.
