# fisher auto update (safe mode)
# - interactive shell only
# - at most once per day
# - recursion / duplicate execution guard
# - skip when fisher is unavailable
# - background execution to keep startup fast

if not status is-interactive
    exit
end

# global re-entry guard (same process)
if set -q __fisher_auto_update_running
    exit
end
set -g __fisher_auto_update_running 1

# cleanup guard on shell exit
function __fisher_auto_update_guard_cleanup --on-event fish_exit
    set -e __fisher_auto_update_running
end

# require fisher
if not type -q fisher
    exit
end

# throttle: once per 24h
set -l cache_dir "$HOME/.cache"
set -l stamp "$cache_dir/fisher.last_update"

set -l now (date +%s)
set -l last 0

if test -f "$stamp"
    # GNU stat (Linux): stat -c %Y
    # BSD stat (macOS): stat -f %m
    set last (stat -c %Y "$stamp" 2>/dev/null)
    if test $status -ne 0
        set last (stat -f %m "$stamp" 2>/dev/null)
    end
    if test -z "$last"
        set last 0
    end
end

set -l interval 86400
if test (math "$now - $last") -lt $interval
    exit
end

mkdir -p "$cache_dir"

# lock dir to avoid concurrent updates across multiple shells
set -l lockdir "$cache_dir/fisher.update.lock"
if not mkdir "$lockdir" 2>/dev/null
    # someone else is updating
    exit
end

# run in background; write stamp only on success; always release lock
begin
    command fisher update
    and date +%s > "$stamp"
    rmdir "$lockdir" 2>/dev/null
end >/dev/null 2>&1 &
