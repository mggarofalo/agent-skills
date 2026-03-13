# Plane project management

This repo is tracked in the **agent-skills** Plane project (identifier `SKILLS`).

## Conventions

- **One module per skill.** Every skill under `skills/` has a corresponding Plane module. Issues related to a skill should be added to that module so work is grouped and progress is visible at the module level.
- **Creating a new skill.** When a new skill is added to the repo, create a matching module in the SKILLS project: `plane module create -p SKILLS --name "<skill-name>" --description "<one-liner>" --status backlog`.
- **Removing a skill.** Archive or delete the corresponding module when a skill is removed.

## CLI quick reference

The `plane` CLI is available system-wide. All commands below have been validated against `plane <cmd> --help`.

### Issues

```bash
# Fetch an issue by sequence ID (e.g., SKILLS-4)
plane issue get-by-sequence-id --identifier <ISSUE-ID> --expand state,labels,assignees -o json

# Update an issue (state, priority, etc.) — requires the issue UUID
plane issue update -p <PROJECT> --work-item-id <UUID> --state <state-id>

# Create a new issue
plane issue create -p <PROJECT> --name "<title>" --description-html "<html>" --priority medium
```

### Comments

```bash
# Add a comment to an issue — requires the issue UUID
plane comment add -p <PROJECT> --work-item-id <UUID> --comment-html "<html>"
```

### States and labels

```bash
# List states (to find state IDs for updates)
plane state list -p <PROJECT> -o json

# List labels (to find label IDs for issue creation)
plane label list -p <PROJECT> -o json
```

### Modules

```bash
# List modules
plane module list -p SKILLS -o table --all

# Create an issue and assign it to a module
plane issue create -p SKILLS --name "Fix false positive in audit" --module <module-id>

# Move an existing issue into a module
plane module add-issue -p SKILLS --module <module-id> --issue <issue-id>
```

### State/label resolution pattern

When a skill needs to update issue state or create an issue with labels:
1. Fetch the list (`plane state list` or `plane label list`) with `-o json`
2. Parse the JSON to find the UUID for the desired state name or label name
3. Use that UUID in the update/create command

See `plane --help` or `plane docs` for full documentation.
