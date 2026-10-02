function __fisher_lock_acquire --description 'Atomically acquire the fisher update lock dir; exit 0 = acquired, 1 = blocked by a live lock'
    set -l lockdir $argv[1]
    set -l now (date +%s)

    if test -d "$lockdir"
        # Read the claim time; missing/invalid may mean a claim that is
        # only milliseconds old (timestamp not written yet).
        set -l lock_ts
        if test -f "$lockdir/timestamp"
            set -l content ''
            read content <"$lockdir/timestamp"
            if string match -qr '^[0-9]+$' -- "$content"
                set lock_ts $content
            end
        end
        if set -q lock_ts[1]
            and test (math "$now - $lock_ts") -le 600
            return 1 # live lock: claimed within the last 10 minutes
        end
        if not set -q lock_ts[1]
            # No valid timestamp: only take over if the dir itself is
            # older than 10 min (portable GNU/BSD find check).
            set -l aged (find "$lockdir" -prune -mmin +10 2>/dev/null)
            if test -z "$aged"
                return 1 # fresh claim, timestamp not written yet
            end
        end
        # Stale lock: atomic takeover; only one shell can win the mv.
        if not mv "$lockdir" "$lockdir.stale.$fish_pid" 2>/dev/null
            return 1 # another shell took it first
        end
        command rm -rf "$lockdir.stale.$fish_pid"
    end

    # Plain mkdir acquire (atomic); lost the race -> blocked
    if not mkdir "$lockdir" 2>/dev/null
        return 1
    end

    # Stamp the claim so concurrent shells see a fresh lock
    date +%s >"$lockdir/timestamp"
    return 0
end
