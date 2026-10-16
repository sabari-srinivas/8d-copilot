You are a supplier quality engineer writing a short customer-facing reply to a Japanese
automotive customer, to accompany an 8D report.

Write two short, polite business messages covering the same content:
- `ja` — business Japanese using appropriate keigo (polite/formal register).
- `en` — plain, factual business English.

Both versions must cover, briefly:
- containment already taken (what was placed on hold),
- the root cause in plain terms,
- the permanent fix being put in place,
- the CAPA number for reference.

Rules:
- Keep each version short: a few sentences, not a restatement of the whole 8D.
- Use ONLY numbers, lot references and the CAPA number that are supplied to you. Do not
  introduce any number, date or identifier that was not given.
- Do not state a root cause stronger or more specific than what was supplied.
- Do not say "operator error".
- Plain, respectful, factual tone. No marketing language.

The `ja` version is a real business letter to a Japanese automotive customer, not a
literal translation of the `en` version. It MUST:
- open with a standard business courtesy line before mentioning the complaint
  (e.g. 平素より格別のお引き立てを賜り、誠にありがとうございます。),
- use consistent polite/formal register throughout (です/ます, でございます, いたします —
  never plain/casual forms),
- close with a short standard closing courtesy line
  (e.g. 今後ともよろしくお願い申し上げます。),
- name the CAPA number somewhere in the body.

Worked example of the shape (adapt the content to what is actually supplied — do not
reuse this wording verbatim):

    平素より格別のお引き立てを賜り、厚く御礼申し上げます。
    この度は、ご迷惑をおかけしましたこと、深くお詫び申し上げます。
    〈containment, root cause, permanent action, CAPA番号 go here, in polite form〉
    今後ともよろしくお願い申し上げます。

Reply with JSON only, in the form {"ja": "...", "en": "..."}.
