# Draft invitation to DS colleagues

For personal circulation. This is draft wording; no email has been sent.
Attach the projection PDF, `docs/ds-workbench-slides.pdf`. The links below let
colleagues use the app and inspect the source without installing anything.

**Subject: DS Workbench — try it, challenge it, help develop it**

Hi all,

I'd like to share DS Workbench with you and see whether we can develop it into
a useful shared resource for DS research, teaching and implementation.

The app lets you build and inspect derivations word by word, following lexical
and computational rules, pointer movements, requirements, backtracking and the
resulting meaning. It builds on the Python `dynamicsyntax` package and its
DyLan foundation. The workbench adds native Classical and Constructive
semantics, English and Greek grammar extensions, sentence/paragraph/dialogue
interfaces, and a research library connecting the literature to implementation.
The inherited TTR backend remains available with its own grammars and coverage.

Core parsing works without an LLM or API key. Optional model assistance proposes
vocabulary and supported construction hypotheses; Jev can help choose between
word senses. DS executes the programs and checks the derivation. Completion
doesn't establish that the interpretation is linguistically right, and coverage
is still fragmentary. Development used Astra with Codex and Fable 5.1 with
Claude Code; the optional models in the app are accessed through OpenRouter.

Here are the main links:

- **Try the app:** https://ds-workbench.vercel.app/
- **Slides:** https://github.com/StergiosCha/DS_workbench/blob/main/docs/ds-workbench-slides.pdf
- **Source and setup:** https://github.com/StergiosCha/DS_workbench
- **Ways to contribute:** https://github.com/StergiosCha/DS_workbench/blob/main/CONTRIBUTING.md
- **Proposed first development cycle:** https://github.com/StergiosCha/DS_workbench/blob/main/docs/community/next-cycle.md

An easy first check is `John, who Mary knows, walks.` in native English, with
both model switches off. Compare Classical and Constructive, and step through
**Rules**. The **DS Library** tab has 53 selected works, with review scope made
explicit; it is a starting collection that needs further reading and correction.

What I'd particularly welcome is people taking on small, well-defined pieces:
reviewing a source analysis and its interpretation; contributing examples and
counterexamples with context; implementing a construction; curating part of the
library; or helping with tests, teaching material and maintenance. Programming
isn't required to make a useful contribution. Alternative DS analyses can be
recorded and compared rather than settled implicitly by one implementation.

My suggestion is to start with one construction family: agree the source and
expected meanings, implement a bounded fragment, and test its limits in each
backend we claim to support. The repository includes an executable grammar
extension tutorial, a construction proposal template and a maintainer guide.

Would you be interested in trying it and saying which part you would like to
review or help develop? A reply with a phenomenon, language or technical area
is enough to start; detailed examples can go into a GitHub issue.

Best,

