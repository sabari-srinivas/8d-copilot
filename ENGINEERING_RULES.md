# 8D Copilot — rules for code in this repo

1. **Golden rule.** The LLM proposes. Deterministic Python decides. A human approves.
   The LLM never writes a p-value, a measurement or a verdict. `agent/tools/stats_test.py`
   is the only module allowed to produce a verdict.
2. **Contract rule.** `docs/contract/README.md` is the agreement between backend and UI.
   If you need to change a field name, a status value or an event type, stop and say so —
   both sides must change together.
3. **Model names come only from env.** `GEMINI_MODEL` and `EMBED_MODEL`. Never hard-code a
   model ID in code, tests, comments or docs.
4. **No number in the 8D that is not in a tool result.** `agent/tools/provenance.py` checks this.
5. **All demo data is synthetic** and is labelled as synthetic in the README and the deck.
   The owner removed the UI wording (CR #5); the plant name carries "(fictional)" instead.
   Do not reintroduce a "demo data" label into any screen.
6. **No secrets, no image bytes in logs.**
7. Small files, one responsibility each. A test for every tool.
