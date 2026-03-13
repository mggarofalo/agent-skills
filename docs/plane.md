# Plane project management

This repo is tracked in the **agent-skills** Plane project (identifier `SKILLS`).

## Conventions

- **One module per skill.** Every skill under `skills/` has a corresponding Plane module. Issues related to a skill should be added to that module so work is grouped and progress is visible at the module level.
- **Creating a new skill.** When a new skill is added to the repo, create a matching module in the SKILLS project: `plane module create -p SKILLS --name "<skill-name>" --description "<one-liner>" --status backlog`.
- **Removing a skill.** Archive or delete the corresponding module when a skill is removed.

## CLI quick reference

The `plane` CLI is available system-wide. Common commands:

```bash
# List modules
plane module list -p SKILLS -o table --all

# Create an issue and assign it to a module
plane issue create -p SKILLS --name "Fix false positive in audit" --module <module-id>

# Move an existing issue into a module
plane module add-issue -p SKILLS --module <module-id> --issue <issue-id>
```

See `plane --help` or `plane docs` for full documentation.
