# GLOBAL_AGENTS.MD — Cross-Project Source of Truth

> **Scope:** Applies to ALL projects. Loaded before any project-level AGENTS.MD.
> **Rule:** If a learning lives here, do not repeat it in the project file.
> **Maintenance:** Andy promotes bullets from project AGENTS.MD §7 when they are not project-specific.
> Last updated: 2026-05-14

---

## HOW TO USE

1. Paste this file's contents at the top of your prompt, before the project AGENTS.MD.
2. Project AGENTS.MD overrides anything here only when it says so explicitly.
3. When a session ends, check: should any project-level learning move here instead?

---

## G1. ANDY'S PREFERENCES
> How Andy works. Apply these without being asked.

```
Communication : Direct. No filler. No over-explaining settled decisions.
Questions     : Max one per response. State the assumption, then proceed.
Format        : Prose over bullets unless content is genuinely list-shaped.
Code          : Always complete. Never truncate. No placeholders like "// rest of code here".
Tone          : Peer-level. No sycophancy. Push back when something is wrong.
```

---

## G2. GLOBAL CONTEXT RULES
> Applied automatically across all projects.

```
- Never delete or rename files without explicit instruction.
- Never add dependencies without asking first.
- Never refactor code outside the current task scope.
- Only touch files directly related to the current task.
- Spot a bug outside scope? Note it, do not fix it silently.
- Secrets always in env vars, never in code.
```

---

## G3. GLOBAL APPLIED LEARNING
> Promoted from project AGENTS.MD §7 when the learning is universal.
> One line. Under 15 words. No explanations.

### Claude / AI Behavior
- AGENTS.MD is empty by default; always audit it before trusting its contents.
- Read both GLOBAL_AGENTS.MD and project AGENTS.MD at session start, every session.

### Platform & Tool Limits
- Django DatabaseCache cannot back django-ratelimit; Redis or Memcached required.
- Django DEBUG=True must be read from env var, never hardcoded, even in dev.
- Middleware-based auth guards are fragile; @login_required on views is authoritative.

### Workflow & Process
- Zero tests means no safe refactoring; write tests before restructuring any module.
- Paste GLOBAL_AGENTS.MD before project AGENTS.MD or project rules won't be seen.
- PEM key files must exist before Django starts; document this in quickstart instructions.

---

## G4. PROMOTION CHECKLIST
> Before closing any project session, ask: does this learning belong here?

Promote a bullet from project §7 → here when it:
- [ ] Applies to more than one project type.
- [ ] Relates to Claude behavior, not a specific codebase.
- [ ] Is a platform/tool limit, not a project decision.
- [ ] Would save time if Andy starts a brand-new project tomorrow.

---

*Load this file first. Every session. Every project.*
