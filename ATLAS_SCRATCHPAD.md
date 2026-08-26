# ATLAS_SCRATCHPAD

Task1: AI-Agent-based-Deep-Research work — completed
  Subtask 1.1: Startup fixes (Streamlit app failures) — completed
  Subtask 1.2: KNOWN_ISSUES.md cleanup — completed
  Subtask 1.3: Render verification — completed
  Subtask 1.4: Commits — completed (e59b0c2, d3ff747, 9d164c8)

Task2: Synthetica work (synthetica-cognitive-sandbox) — completed
  Subtask 2.1: Understand repo/WIP — completed
  Subtask 2.2: WIP commit (2ff8f31) — completed
  Subtask 2.3: Audit — completed
  Subtask 2.4: Fixes commit (396d2cd) — completed
  Subtask 2.5: Verification — completed

Task3: Synthetica — validate agent reasoning end-to-end — completed
  Subtask 3.1: Trace reasoning pipeline (prompts, inputs, outputs, feedback) — completed
  Subtask 3.2: Live simulation run with real reasoning traces — completed (2 runs: 48 turns each, llama3.2 via Ollama)
  Subtask 3.3: Verify axiom evolution + replay/dashboard reasoning data — completed (4 compression records @gen10; APIs 200)
  Subtask 3.4: Bug hunt & fixes — completed (7 bugs fixed: eval score zeroing, fabricated fallback reasoning, axiom wipe, crash on nested intent, hidden dict reasoning, coherence always-false, discarded evaluator output)
  Subtask 3.5: Commits + final report — completed (5cda242)
  Notes: .env created for local Ollama (llama3.2); run_task3_verify.py kept as regression harness

Task4: Synthetica — independent re-verification of Task3's 7 reasoning-bug fixes (5cda242) — completed
  Subtask 4.1: Per-bug before/after diff review — completed (all 7 diffs reviewed)
  Subtask 4.2: Write targeted repro per bug (fails pre-fix, passes now) — completed (verify_task4_repro.py, 8 checks incl. axiom-wipe edge case)
  Subtask 4.3: Run repros, fix any incomplete/wrong fix — completed (pre-fix 0/8 pass, post-fix 8/8; live 12-gen regression run OK; 1 follow-up fix: env-layer nested-intent coercion aligned with agent layer)
  Subtask 4.4: Final report + scratchpad closeout — completed (commit f88845d)

Task22: Synthetica — audit-round bug fixes (amnesty rep inversion, case-sensitive coherence) — completed
  Subtask 22.1: Regression tests (tests/test_audit_fixes.py, offline, no LLM) — completed
  Subtask 22.2: Pre-fix verification — completed (2/6 fail pre-fix: amnesty inversion + case sensitivity; 4 pass)
  Subtask 22.3: Fixes — completed (AMNESTY: pos rep x1.3, neg rep x0.7 toward zero; intents_match() .upper()-normalized, None-safe; commit 319d967 on fix/audit-round)
  Subtask 22.4: Post-fix verification — completed (6/6 tests pass; verify_task4_repro.py 8/8 PASS)
  Subtask 22.5: PR — completed (PR #1 https://github.com/saksham-jain177/synthetica-cognitive-sandbox/pull/1, OPEN, unmerged; no PR CI — docker-image.yml only runs on tags)

Task24: Synthetica — research-platform test suite (determinism-first) — completed
  Subtask 24.1: Branch feat/test-suite off synced main (c4d5a81) — completed
  Subtask 24.2: Determinism tests (tests/test_determinism.py, 6) — seeded runs identical traces; run_seeded_simulation() harness in conftest.py
  Subtask 24.3: Mechanics tests (tests/test_mechanics.py, 22 incl. 1 strict xfail) — energy/rep deltas, betrayals, barrier rules, advance_generation carryover, event cadence
  Subtask 24.4: Persistence tests (tests/test_persistence.py, 10) — AxiomTracker JSONL round-trip/schema; replay /list + /load via Flask test client
  Subtask 24.5: Evaluator tests (tests/test_evaluator.py, 12) — EVAL_CADENCE gating, llm_evaluated/justification persistence, heuristic fallback, key-case normalization
  Subtask 24.6: Run suite — 50 passed, 1 xfailed, ~5.3s (all offline stub-LLM)
  Subtask 24.7: Push + PR #2 https://github.com/saksham-jain177/synthetica-cognitive-sandbox/pull/2 — OPEN, unmerged
  Bugs found (not fixed): synthetica_environment.py:222 duplicate collapse scars; :199-201 steal mints energy; evaluator_node.py:133-142 llm_evaluated stays True on LLM failure; replay.py:78 /axioms path-root mismatch with AxiomTracker

Task24 Addendum: Synthetica — audit round 2: fix the 4 bugs found by the test suite — completed
  Branch fix/audit-round-2 based on feat/test-suite (PR #2); one PR targeting main, unmerged
  Subtask A24.1: Regression tests tests/test_audit_fixes_2.py (5) — completed
  Subtask A24.2: Pre-fix proof (source changes stashed) — 4 FAILED / 1 passed:
    - collapse-scar dedup: 2 collapse scars after sabotage + maintenance re-collapse
    - steal conservation: total energy 510 -> 525 (15 minted)
    - evaluator fallback: llm_evaluated was True on LLM failure
    - /axioms guard: AxiomTracker had no base_dir(); old guard let sim_id '..' pass
  Subtask A24.3: Fixes — completed
    - synthetica_environment.py: new _record_collapse_scar() helper; all 3 collapse sites (sabotage/quake/maintenance) route through it (canonical scar, substring dedup)
    - synthetica_environment.py STEAL_RESOURCE: stolen = min(25, victim_energy); no minting
    - evaluator_node.py: use_llm set False on LLM exception AND malformed-JSON fallback
    - axiom_tracker.py: new static base_dir(); replay.py /axioms guard now validates against tracker's real root via realpath
    - Updated suite expectations that documented the bugs as behavior: test_mechanics.py steal delta 25->5; test_evaluator.py llm_evaluated True->False (2 sites); removed strict xfail on sabotage collapse scar (now passes)
  Subtask A24.4: Post-fix — full suite 56 passed, 0 failed (~4s)

Task22-Polish: Synthetica — portfolio-ready polish sprint (S-approved) — in progress
  Branch: feat/polish-sprint (off main c4d5a81)
  Subtask T1: Audit pass (read-only) — completed
    - Mapped backend/app structure: 29 Python files, 2 simulation systems (OASIS disabled, Synthetica active)
    - Only active HTTP endpoints: replay viewer + health check + observatory dashboard
    - Root scripts: run_synthetica.py (single run), run_batch_simulations.py (grid sweep), run_task3_verify.py + verify_task4_repro.py (debug harnesses)
    - 5 stale .log files at root (gitignored, deleted)
    - Dead code: 3 disabled API blueprints (graph/simulation/report), utils/retry.py (unused), scripts/action_logger.py (unused), duplicate LLM clients
    - Test coverage on main: only tests/test_audit_fixes.py (6 tests); feat/test-suite branch has 56 more (unmerged)
    - .env.example was in Chinese, referenced MiroFish/cloud services, not matching actual config.py
  Subtask T2: README rewrite — completed
    - Restructured: what it is -> architecture diagram (mermaid) -> 4 core features as design decisions with WHY -> quick start -> honest limitations
    - Added: sequential LLM triage rationale (6GB VRAM), axiom compression rationale (context collapse), dual-scoring rationale (cost optimization), adversarial scrubbing rationale
    - Kept MiroFish fork attribution, AGPL-3.0 license
    - Added project structure tree, test instructions, limitations section
  Subtask T3: Test suite — completed
    - 89 tests across 6 files, all offline (stub LLM clients, no network)
    - test_environment.py (24): scarcity pressure, all 7 action types, trust system, event injection, generation advance, fog-of-war prompts
    - test_evaluator.py (15): deterministic scoring (CCS-B), contextual modifiers, coherence, schema normalization, EVAL_CADENCE, Pydantic validation
    - test_axiom_tracker.py (5): JSONL write/read round-trip, empty record guard
    - test_config.py (11): config defaults, scoring maps, CCS bounds, trust thresholds
    - test_utils.py (13): intents_match (case-insensitive, None-safe), split_text_into_chunks
    - test_runner.py (3): agent setup, full 2-gen simulation produces correct JSONL schema
    - All pass in ~5s
  Subtask T4: Hygiene — completed
    - Deleted 5 stale .log files from root (gitignored, on-disk only)
    - Rewrote .env.example: English, matches actual Config class, all Synthetica env vars documented with comments
    - No dead root scripts to delete: run_task3_verify.py and verify_task4_repro.py are regression harnesses
  Subtask T5: Demo story — completed
    - run_batch_simulations.py produces JSONL under uploads/simulations/{sim_id}/synthetica_actions.jsonl + axioms.jsonl
    - Output is viewer-friendly: Neural Observatory (/observatory) reads JSONL via replay API
    - Documented in README: how to generate, view, and interpret results
  Subtask T6: Commit + PR — pending
    - All changes on feat/polish-sprint branch
    - 89 tests green, no ruff configured (no ruff.toml in repo)
