# Thariq Shihipar's Guidance on Skill Creation

Thariq Shihipar leads the Claude Code team at Anthropic. This document compiles his published guidance on authoring effective skills. Sources: his article "Lessons from Building Claude Code: How We Use Skills" (March 2026), Anthropic's official skill-creator SKILL.md, and the official best practices documentation.

---

## Nine Skill Archetypes

Thariq identifies nine categories that most skills fall into. Use these to frame what you're building:

1. **Library & API Reference** -- Guidance on using internal/external libraries, CLIs, SDKs with edge cases documented
2. **Product Verification** -- Testing and verification procedures paired with external tools
3. **Data Fetching & Analysis** -- Connections to data/monitoring stacks with query patterns
4. **Business Process & Team Automation** -- Workflow automation into single commands
5. **Code Scaffolding & Templates** -- Framework boilerplate generation
6. **Code Quality & Review** -- Quality enforcement and code review
7. **CI/CD & Deployment** -- Code fetching, pushing, deployment procedures
8. **Runbooks** -- Multi-tool investigation from symptoms to structured reports
9. **Infrastructure Operations** -- Routine maintenance and operational procedures

---

## Core Principles

### Avoid stating obvious knowledge
Focus on information that pushes Claude beyond its default patterns. If Claude already knows how to do it without the skill, that line isn't earning its tokens.

### Build a gotchas section
"The highest-signal content in any skill is the Gotchas section." Compile these from actual failure points -- things that went wrong in practice, not hypothetical risks. Every time the skill produces a bad result, add a gotcha.

### Use progressive disclosure
Structure skills as folders with markdown files, scripts, templates, and references that Claude accesses contextually. Keep SKILL.md under 500 lines. Split into `references/` files when approaching that limit.

### Allow flexibility
Provide information Claude needs without over-constraining through overly specific instructions. Match specificity to fragility:
- **High freedom** (text guidance): Multiple approaches valid, decisions depend on context
- **Medium freedom** (pseudocode): Preferred pattern exists, some variation acceptable
- **Low freedom** (specific scripts): Operations fragile, consistency critical

Think of Claude as a robot exploring a path. Narrow bridge with cliffs = low freedom. Open field = high freedom.

---

## On Writing Style

> "Try to explain to the model **why** things are important in lieu of heavy-handed musty MUSTs. Use theory of mind and try to make the skill general and not super-narrow to specific examples."

> "If you find yourself writing ALWAYS or NEVER in all caps, or using super rigid structures, that's a yellow flag -- if possible, reframe and explain the reasoning so that the model understands why the thing you're asking for is important. That's a more humane, powerful, and effective approach."

Key takeaway: Explain *why*, don't just dictate *what*. Claude responds better to understanding the reasoning than to capitalized imperatives.

---

## On Writing Descriptions

Descriptions are the primary trigger mechanism. Claude uses them to decide when to load a skill from potentially 100+ available options.

> "Currently Claude has a tendency to 'undertrigger' skills -- to not use them when they'd be useful. To combat this, please make the skill descriptions a little bit 'pushy'."

**Bad description:**
> "How to build a simple fast dashboard to display internal data."

**Good description:**
> "How to build a simple fast dashboard to display internal data. Make sure to use this skill whenever the user mentions dashboards, data visualization, internal metrics, or wants to display any kind of company data, even if they don't explicitly ask for a 'dashboard.'"

Rules:
- Write in third person ("Processes Excel files..." not "I can help you...")
- Include both what the skill does AND specific triggers/contexts
- List synonyms and related phrases the user might say
- Be slightly "pushy" -- err on the side of triggering

---

## On Improving Skills

> "Generalize from the feedback... if the skill works only for those examples, it's useless. Rather than put in fiddly overfitty changes, or oppressively constrictive MUSTs, if there's some stubborn issue, you might try branching out and using different metaphors, or recommending different patterns of working."

> "Keep the prompt lean. Remove things that aren't pulling their weight. Read the transcripts, not just the final outputs."

> "Look for repeated work across test cases. If all 3 test cases resulted in the subagent writing a `create_docx.py` or a `build_chart.py`, that's a strong signal the skill should bundle that script."

---

## The Iteration Loop

1. Complete a task without a skill -- identify the reusable pattern
2. Write a draft skill
3. Create 3+ test prompts (mix of should-trigger and should-not-trigger)
4. Run the test prompts and evaluate results
5. Read the *transcripts*, not just final outputs
6. Generalize from feedback -- don't overfit
7. Remove what isn't pulling its weight
8. If a script keeps being generated, bundle it in the skill
9. Repeat until satisfied, then expand the test set

---

## Anti-Patterns

- Windows-style paths (always use forward slashes)
- Offering too many options (provide a default with an escape hatch)
- Assuming tools are installed (be explicit about dependencies)
- Deeply nested references (keep one level deep from SKILL.md)
- Voodoo constants (always justify configuration values)
- Punting errors to Claude (handle them explicitly in scripts)
- Time-sensitive information (it will go stale)
- ALWAYS/NEVER in all caps without explaining why

---

## Checklist for Effective Skills

From the official best practices documentation:

- [ ] Description is specific and includes key terms
- [ ] Description includes both what the skill does AND when to use it
- [ ] SKILL.md body under 500 lines
- [ ] Additional details in separate reference files (if needed)
- [ ] No time-sensitive information
- [ ] Consistent terminology throughout
- [ ] Examples are concrete, not abstract
- [ ] File references one level deep
- [ ] Progressive disclosure used appropriately
- [ ] Workflows have clear steps
- [ ] Scripts solve problems rather than punt to Claude
- [ ] At least 3 test prompts created
- [ ] Gotchas section compiled from real failures
