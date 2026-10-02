function fisher_auto_update
    # Periodic fisher plugin sync: at most once per interval.
    # The interactive guard lives in setup_fisher (not here) so this
    # function can be called from non-interactive tests via `fish -c`.
    if not functions -q fisher
        # Bootstrap handles that case
        return 0
    end

    # Sync interval in seconds (default: once per day)
    set -l interval 86400
    if set -q FISHER_UPDATE_INTERVAL
        and string match -qr '^[0-9]+$' -- "$FISHER_UPDATE_INTERVAL"
        set interval $FISHER_UPDATE_INTERVAL
    end

    set -l cache_dir $HOME/.cache
    set -l stamp $cache_dir/fisher_sync.stamp
    set -l now (date +%s)
    set -l last 0

    # Read the stamp content (never mtime/stat: BSD stat is fragile)
    if test -f "$stamp"
        set -l content ''
        read content <"$stamp"
        if string match -qr '^[0-9]+$' -- "$content"
            set last $content
        end
    end

    # Future-dated stamp (corruption / clock skew) counts as expired
    if test "$last" -gt "$now"
        set last 0
    end

    if test (math "$now - $last") -lt $interval
        return 0
    end

    mkdir -p $cache_dir

    # Remove old-generation artifacts (legacy stamp/lock names)
    command rm -rf $cache_dir/fisher_last_update
    command rm -rf $cache_dir/fisher_update.lock
    command rm -rf $cache_dir/fisher.last_update
    command rm -rf $cache_dir/fisher.update.lock

    # Lock dir to avoid concurrent updates across multiple shells.
    # __fisher_lock_acquire blocks (exit 1) while another update is
    # live and atomically takes over stale locks; lost race -> skip.
    set -l lockdir $cache_dir/fisher_sync.lock
    if not __fisher_lock_acquire "$lockdir"
        return 0
    end

    # Claim before running: write the stamp now so the interval is
    # enforced even if the update fails or the shell is killed.
    # (The lock claim timestamp is written by __fisher_lock_acquire.)
    date +%s > "$stamp"

    # Run in background to keep shell startup fast
    begin
        fisher update
        command rm -f "$lockdir/timestamp"
        rmdir "$lockdir" 2>/dev/null
    end >/dev/null 2>&1 &
end
