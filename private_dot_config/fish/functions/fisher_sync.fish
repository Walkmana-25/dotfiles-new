function fisher_sync
    # Manual immediate fisher sync. Bypasses the interval check but
    # shares the lock protocol with fisher_auto_update and still
    # claims the interval so the next startup does not re-update.
    set -l cache_dir $HOME/.cache
    set -l stamp $cache_dir/fisher_sync.stamp
    set -l lockdir $cache_dir/fisher_sync.lock

    # Force bootstrap retry on the next shell start
    command rm -f $cache_dir/fisher_bootstrap.stamp

    # Lock first: a live update blocks us; never remove its lock and
    # do not claim the interval out from under it.
    mkdir -p $cache_dir
    if not __fisher_lock_acquire "$lockdir"
        echo "fisher_sync: another update is already running" >&2
        return 1
    end

    # Claim the interval before running (same semantics as auto-update)
    date +%s > "$stamp"

    if not functions -q fisher
        echo "Installing Fisher..."
        __fisher_bootstrap
        if not functions -q fisher
            command rm -f "$lockdir/timestamp"
            rmdir "$lockdir" 2>/dev/null
            echo "fisher_sync: fisher is unavailable" >&2
            return 1
        end
    end

    echo "Syncing fisher plugins..."
    fisher update

    # Release the lock unconditionally
    command rm -f "$lockdir/timestamp"
    rmdir "$lockdir" 2>/dev/null
end
