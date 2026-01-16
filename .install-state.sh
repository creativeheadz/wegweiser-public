#!/bin/bash

# Filepath: .install-state.sh
# Installation State Tracking Library
# Provides functions for tracking installation progress, enabling resume and rollback

STATE_FILE=".install-state.json"
BACKUP_DIR=".install-backup"

# Initialize state tracking
init_state() {
    if [ ! -f "$STATE_FILE" ]; then
        cat > "$STATE_FILE" << EOF
{
  "version": "1.0",
  "started_at": "$(date -Iseconds)",
  "deployment_mode": "",
  "steps": {},
  "current_step": "",
  "status": "not_started"
}
EOF
    fi
}

# Set deployment mode
set_deployment_mode() {
    local mode="$1"
    jq --arg mode "$mode" '.deployment_mode = $mode' "$STATE_FILE" > "$STATE_FILE.tmp" && mv "$STATE_FILE.tmp" "$STATE_FILE"
}

# Mark step as started
step_start() {
    local step_name="$1"
    local step_description="$2"

    jq --arg step "$step_name" \
       --arg desc "$step_description" \
       --arg time "$(date -Iseconds)" \
       '.current_step = $step |
        .steps[$step] = {
          "description": $desc,
          "status": "in_progress",
          "started_at": $time,
          "completed_at": null,
          "error": null
        }' "$STATE_FILE" > "$STATE_FILE.tmp" && mv "$STATE_FILE.tmp" "$STATE_FILE"
}

# Mark step as completed
step_complete() {
    local step_name="$1"

    jq --arg step "$step_name" \
       --arg time "$(date -Iseconds)" \
       '.steps[$step].status = "completed" |
        .steps[$step].completed_at = $time' "$STATE_FILE" > "$STATE_FILE.tmp" && mv "$STATE_FILE.tmp" "$STATE_FILE"
}

# Mark step as failed
step_fail() {
    local step_name="$1"
    local error_msg="$2"

    jq --arg step "$step_name" \
       --arg error "$error_msg" \
       '.steps[$step].status = "failed" |
        .steps[$step].error = $error |
        .status = "failed"' "$STATE_FILE" > "$STATE_FILE.tmp" && mv "$STATE_FILE.tmp" "$STATE_FILE"
}

# Mark step as skipped
step_skip() {
    local step_name="$1"
    local reason="$2"

    jq --arg step "$step_name" \
       --arg reason "$reason" \
       '.steps[$step].status = "skipped" |
        .steps[$step].error = $reason' "$STATE_FILE" > "$STATE_FILE.tmp" && mv "$STATE_FILE.tmp" "$STATE_FILE"
}

# Get step status
get_step_status() {
    local step_name="$1"
    jq -r --arg step "$step_name" '.steps[$step].status // "not_started"' "$STATE_FILE"
}

# Check if step is completed
is_step_completed() {
    local step_name="$1"
    local status=$(get_step_status "$step_name")
    [ "$status" == "completed" ]
}

# Mark installation as complete
install_complete() {
    jq --arg time "$(date -Iseconds)" \
       '.status = "completed" |
        .completed_at = $time' "$STATE_FILE" > "$STATE_FILE.tmp" && mv "$STATE_FILE.tmp" "$STATE_FILE"
}

# Mark installation as failed
install_failed() {
    local error_msg="$1"

    jq --arg error "$error_msg" \
       --arg time "$(date -Iseconds)" \
       '.status = "failed" |
        .failed_at = $time |
        .error = $error' "$STATE_FILE" > "$STATE_FILE.tmp" && mv "$STATE_FILE.tmp" "$STATE_FILE"
}

# Get installation status
get_install_status() {
    jq -r '.status' "$STATE_FILE"
}

# Get progress percentage
get_progress() {
    local total_steps=$(jq '.steps | length' "$STATE_FILE")
    local completed_steps=$(jq '[.steps[] | select(.status == "completed")] | length' "$STATE_FILE")

    if [ "$total_steps" -eq 0 ]; then
        echo "0"
    else
        echo $((completed_steps * 100 / total_steps))
    fi
}

# List all steps with their status
list_steps() {
    jq -r '.steps | to_entries[] | "\(.key): \(.value.status)"' "$STATE_FILE"
}

# Get incomplete steps
get_incomplete_steps() {
    jq -r '.steps | to_entries[] | select(.value.status != "completed") | .key' "$STATE_FILE"
}

# Create backup point
create_backup() {
    local backup_name="$1"
    local backup_path="$BACKUP_DIR/$backup_name"

    mkdir -p "$backup_path"

    # Backup .env if it exists
    if [ -f ".env" ]; then
        cp .env "$backup_path/.env"
    fi

    # Record backup metadata
    cat > "$backup_path/metadata.json" << EOF
{
  "created_at": "$(date -Iseconds)",
  "backup_name": "$backup_name",
  "installation_state": $(cat "$STATE_FILE")
}
EOF

    echo "$backup_path"
}

# Restore from backup
restore_backup() {
    local backup_name="$1"
    local backup_path="$BACKUP_DIR/$backup_name"

    if [ ! -d "$backup_path" ]; then
        return 1
    fi

    # Restore .env
    if [ -f "$backup_path/.env" ]; then
        cp "$backup_path/.env" .env
    fi

    # Restore state
    if [ -f "$backup_path/metadata.json" ]; then
        jq '.installation_state' "$backup_path/metadata.json" > "$STATE_FILE"
    fi

    return 0
}

# List available backups
list_backups() {
    if [ -d "$BACKUP_DIR" ]; then
        find "$BACKUP_DIR" -mindepth 1 -maxdepth 1 -type d -exec basename {} \;
    fi
}

# Clean up old backups
cleanup_backups() {
    if [ -d "$BACKUP_DIR" ]; then
        # Keep only the 5 most recent backups
        ls -t "$BACKUP_DIR" | tail -n +6 | xargs -I {} rm -rf "$BACKUP_DIR/{}"
    fi
}

# Display progress bar
show_progress() {
    local progress=$(get_progress)
    local filled=$((progress / 2))
    local empty=$((50 - filled))

    printf "\rProgress: ["
    printf "%${filled}s" | tr ' ' '='
    printf "%${empty}s" | tr ' ' '-'
    printf "] %d%%" "$progress"
}

# Display detailed status
show_status() {
    local status=$(get_install_status)
    local progress=$(get_progress)

    echo "Installation Status: $status"
    echo "Progress: $progress%"
    echo ""
    echo "Steps:"

    jq -r '.steps | to_entries[] |
           "\(.key): \(.value.status) - \(.value.description)"' "$STATE_FILE" | \
    while IFS= read -r line; do
        if echo "$line" | grep -q "completed"; then
            echo -e "  ${GREEN}✓${NC} $line"
        elif echo "$line" | grep -q "in_progress"; then
            echo -e "  ${BLUE}→${NC} $line"
        elif echo "$line" | grep -q "failed"; then
            echo -e "  ${RED}✗${NC} $line"
        elif echo "$line" | grep -q "skipped"; then
            echo -e "  ${YELLOW}⊘${NC} $line"
        else
            echo -e "  ${DIM}○${NC} $line"
        fi
    done
}

# Check if installation can be resumed
can_resume() {
    if [ ! -f "$STATE_FILE" ]; then
        return 1
    fi

    local status=$(get_install_status)
    if [ "$status" == "failed" ] || [ "$status" == "in_progress" ]; then
        return 0
    fi

    return 1
}

# Reset installation state
reset_state() {
    if [ -f "$STATE_FILE" ]; then
        mv "$STATE_FILE" "$STATE_FILE.old.$(date +%Y%m%d_%H%M%S)"
    fi
    init_state
}

# Export functions for use in other scripts
export -f init_state
export -f set_deployment_mode
export -f step_start
export -f step_complete
export -f step_fail
export -f step_skip
export -f get_step_status
export -f is_step_completed
export -f install_complete
export -f install_failed
export -f get_install_status
export -f get_progress
export -f list_steps
export -f get_incomplete_steps
export -f create_backup
export -f restore_backup
export -f list_backups
export -f cleanup_backups
export -f show_progress
export -f show_status
export -f can_resume
export -f reset_state
