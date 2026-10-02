function setup_fisher
    # Fisher configuration
    set -g fisher_path $HOME/.config/fish/fisher
    set fish_function_path $fish_function_path[1] $fisher_path/functions $fish_function_path[2..]
    set fish_complete_path $fish_complete_path[1] $fisher_path/completions $fish_complete_path[2..]

    # Install Fisher if not installed (throttled: at most once per interval)
    if not functions -q fisher
        set -l bootstrap_stamp $HOME/.cache/fisher_bootstrap.stamp
        set -l now (date +%s)
        # Retry hourly until fisher is installed; once installed this branch never runs again.
        set -l attempt_interval 3600
        set -l last_attempt 0

        if test -f "$bootstrap_stamp"
            set -l content ''
            read content <"$bootstrap_stamp"
            # Treat missing/invalid content as expired
            if string match -qr '^[0-9]+$' -- "$content"
                set last_attempt $content
            end
        end

        if test (math "$now - $last_attempt") -ge $attempt_interval
            mkdir -p $HOME/.cache
            # Stamp the attempt before bootstrapping so a failing/offline
            # bootstrap does not retry on every shell.
            date +%s > "$bootstrap_stamp"
            __fisher_bootstrap
        end
    end

    # Source all conf.d files
    if test -d $fisher_path/conf.d
        for file in $fisher_path/conf.d/*.fish
            if test -f $file
                source $file
            end
        end
    end

    # Periodic plugin sync (interactive shells only)
    if status is-interactive
        fisher_auto_update
    end
end
