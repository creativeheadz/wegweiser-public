# Claude Code Automation Setup

This project uses Claude Code slash commands and automation scripts for common workflows.

## Available Commands

### `/md_cleanup_into_documentation`

Automatically organize and validate markdown files in the project root.

**Quick Start**:
```
/md_cleanup_into_documentation
```

**What It Does**:
- ✅ Validates markdown files
- ✅ Moves important docs to `/documentation/`
- ✅ Deletes obsolete status/checklist files
- ✅ Preserves project config (CLAUDE.md)
- ✅ Creates automatic backups

**Smart Classification**:
- **Move**: README, SETUP, GUIDE, ARCHITECTURE, PORTABILITY, DESIGN, FIX_LOG
- **Delete**: Status reports, checklists, implementation summaries
- **Preserve**: CLAUDE.md

**Safety Features**:
- Backup created before any deletion
- Full logging to `wlog/md_cleanup.log`
- Non-destructive (can be undone via backups)

## How to Use Commands in Claude Code

### Method 1: Direct Slash Command (Easiest)
Just type in the chat:
```
/md_cleanup_into_documentation
```

Claude Code will automatically find and execute it.

### Method 2: Reference in CLAUDE.md
The command is documented in `CLAUDE.md` under "Automated Workflows & Commands".
When you reference the command in conversation, Claude Code will use it.

### Method 3: View All Commands
```
/help
```

Then look for your command in the list.

## Files Structure

```
.claude/
├── commands/
│   └── md_cleanup_into_documentation.md    # Command definition
├── AUTOMATION_README.md                     # This file
└── (other config files)

scripts/
└── md_cleanup.sh                           # Implementation script

CLAUDE.md                                    # Updated with command docs
```

## How to Extend This

To create another slash command:

1. Create `.claude/commands/my_command.md`:
```markdown
# /my_command

Description of what it does.

## Usage

/my_command
```

2. Create the implementation script in `scripts/`

3. Document in `CLAUDE.md` under "Automated Workflows & Commands"

4. Use with `/my_command`

## More Information

- **Command Details**: See `.claude/commands/md_cleanup_into_documentation.md`
- **Implementation**: See `scripts/md_cleanup.sh`
- **Developer Notes**: See `CLAUDE.md` section "Automated Workflows & Commands"
- **Logs**: Check `wlog/md_cleanup.log` after running cleanup

---

**Last Updated**: 2025-10-24
