---
name: sdlc
description: >
  Run a structured SDLC pipeline for a Plane issue through 6 phases:
  Plan, Implement, Review, Security, QA, and Accept. Each phase uses
  a specialized agent, auto-advances on success, and loops back with
  remediation on failure.
instructions: |
  # SDLC Pipeline Orchestrator

  This skill runs a structured software development lifecycle pipeline driven by a Plane issue.
  It can run the full pipeline or a single phase.

  ## Usage

  - `/sdlc <issue-id>` — Run the full 6-phase pipeline
  - `/sdlc plan <issue-id>` — Run only the Plan phase
  - `/sdlc implement <issue-id>` — Run only the Implement phase
  - `/sdlc review <issue-id>` — Run only the Review phase
  - `/sdlc security <issue-id>` — Run only the Security phase
  - `/sdlc qa <issue-id>` — Run only the QA phase
  - `/sdlc accept <issue-id>` — Run only the Accept phase

  ## Argument Parsing

  Parse the arguments to determine mode:
  - If ONE argument: it is the `<issue-id>`. Run the full pipeline.
  - If TWO arguments: first is the phase name, second is the `<issue-id>`. Run only that phase.
  - Phase names: `plan`, `implement`, `review`, `security`, `qa`, `accept`

  ## Initialization (All Modes)

  1. **Fetch the Plane issue:**
     ```bash
     plane issue get-by-sequence-id --identifier <ISSUE-ID> --expand state,labels,assignees -o json
     ```
     Save the `id` (UUID) from the JSON output for subsequent update and comment commands.
     Extract: title, description, identifier (e.g., RECEIPTS-123), acceptance criteria.
     Use `docs/plane.md` to determine the project identifier for `-p` flags in later commands.
  2. **Discover project context** from the current working directory:
     - Check for a git repo (`git rev-parse --git-dir`)
     - Read `AGENTS.md` if it exists — extract build commands, branch strategy, conventions
     - Read `docs/plane.md` if it exists — extract project, module, and milestone context
     - Read `CLAUDE.md` if it exists — extract additional project guidance
     - Detect tech stack from file patterns: `*.cs` → .NET, `*.swift` → Swift, `package.json` → Node/React, `*.py` → Python, etc.
  3. **Initialize or read the state file** at `.sdlc/<issue-identifier>.md`:
     - If it doesn't exist, create it with the issue header and discovered context
     - If it exists, read it to resume from where we left off
  4. **Ensure `.sdlc/` is gitignored**: check `.gitignore` for `.sdlc/` entry; add it if missing.

  ### State File Template

  When creating a new state file, use this structure:

  ```markdown
  # SDLC Pipeline: <identifier> — <title>

  ## Issue
  - **ID:** <identifier>
  - **URL:** <url>
  - **Title:** <title>
  - **Acceptance Criteria:**
  <criteria from issue description>

  ## Project Context
  - **Tech Stack:** <detected>
  - **Build Command:** <from AGENTS.md or detected>
  - **Test Command:** <from AGENTS.md or detected>
  - **Branch Strategy:** <from AGENTS.md>
  - **Conventions:** <key conventions>
  ```

  ## Single Phase Mode

  When a specific phase is requested (e.g., `/sdlc plan MGG-123`):
  1. Run initialization as above
  2. Read the phase instructions from the corresponding reference file:
     - `plan` → Read `~/.claude/skills/sdlc/references/phase-plan.md`
     - `implement` → Read `~/.claude/skills/sdlc/references/phase-implement.md`
     - `review` → Read `~/.claude/skills/sdlc/references/phase-review.md`
     - `security` → Read `~/.claude/skills/sdlc/references/phase-security.md`
     - `qa` → Read `~/.claude/skills/sdlc/references/phase-qa.md`
     - `accept` → Read `~/.claude/skills/sdlc/references/phase-accept.md`
  3. Execute the phase instructions
  4. Write results to the state file
  5. Report the phase result to the user

  ## Full Pipeline Mode

  When running the full pipeline (`/sdlc MGG-123`):

  ### Execution Order
  1. Plan → 2. Implement → 3. Review → 4. Security → 5. QA → 6. Accept

  ### For Each Phase
  1. Read the phase reference file
  2. Execute the phase instructions
  3. Write results to the state file
  4. Evaluate pass/fail

  ### Auto-Advance
  If a phase passes, immediately proceed to the next phase without user intervention.

  ### Remediation Loop on Failure
  When a phase fails:
  1. Check the remediation attempt count for this phase (tracked in state file under the phase section as `**Remediation Attempts:** N`)
  2. If attempts >= 2: **STOP** and ask the user for guidance via `AskUserQuestion`
  3. If attempts < 2:
     - Route to the appropriate fix agent per the remediation table below
     - Increment the remediation attempt counter
     - After fix, re-run ONLY the failing phase (not prior phases)

  ### Remediation Routing Table

  | Failing Phase | Triage By | Fix By      | Re-run   |
  |---------------|-----------|-------------|----------|
  | Review        | —         | Implementer | Review   |
  | Security      | —         | Implementer | Security |
  | QA            | QA        | QA or Impl  | QA       |
  | Accept        | —         | (stop, ask) | Accept   |

  For **Review** and **Security** failures:
  - Read the failing phase's findings from the state file
  - Re-read `phase-implement.md` and execute targeted fixes for the specific findings
  - Commit the fixes
  - Update the state file with remediation details
  - Re-run the failing phase

  For **QA** failures:
  - QA triages: is the test wrong or the code wrong?
  - If test is wrong → QA fixes the test
  - If code is wrong → route to Implementer with failing test details
  - Re-run QA

  For **Accept** failures:
  - Always stop and surface the unmet criteria to the user

  ### Pipeline Completion

  When all 6 phases pass:
  1. **Post a Plane comment** on the issue with this format (use `plane comment add -p <PROJECT> --work-item-id <UUID> --comment-html "<html>"`):

  ```markdown
  ## SDLC Pipeline Summary

  **Issue:** <identifier> — <title>
  **Result:** PASS

  | Phase | Status | Notes |
  |-------|--------|-------|
  | Plan | Pass | <1-line summary> |
  | Implement | Pass | <N files changed, M commits> |
  | Review | Pass | <findings summary> |
  | Security | Pass | <threat model summary> |
  | QA | Pass | <test summary> |
  | Accept | Pass | <N/N criteria met> |

  **Branch:** `<branch-name>`
  ```

  2. **Update the Plane issue status** to "Done":
     ```bash
     plane issue update -p <PROJECT> --work-item-id <UUID> --state <done-state-id>
     ```
  3. **Delete the state file** (clean up `.sdlc/<identifier>.md`)
  4. Report the final result to the user

  ## Important Notes

  - Each phase should be executed using a `Task` agent with the appropriate `subagent_type` for the work:
    - Plan → `feature-dev:code-architect`
    - Implement → `general-purpose`
    - Review → `feature-dev:code-reviewer`
    - Security → `general-purpose`
    - QA → `general-purpose`
    - Accept → `general-purpose`
  - Always pass the full state file content and phase reference content to the agent
  - The state file is the single source of truth — all phases read from and write to it
  - Never skip phases in the full pipeline
  - If the issue has no description or acceptance criteria, ask the user before proceeding

user_invocable: true
argument: "<phase?> <issue-id> — Run the full SDLC pipeline or a specific phase for a Plane issue"
---
