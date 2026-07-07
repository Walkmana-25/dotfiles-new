function setup_fisher
    # Fisher configuration
    set -g fisher_path $HOME/.config/fish/fisher
    set fish_function_path $fish_function_path[1] $fisher_path/functions $fish_function_path[2..]
    set fish_complete_path $fish_complete_path[1] $fisher_path/completions $fish_complete_path[2..]

    # Install Fisher if not installed
    if not functions -q fisher
        echo "Installing Fisher..."
        mkdir -p $HOME/.cache
        curl -sL https://raw.githubusercontent.com/jorgebucaran/fisher/main/functions/fisher.fish | source && fisher install jorgebucaran/fisher
    end

    # Periodic Fisher update (async)
    set -g fisher_last_update_file $HOME/.cache/fisher_last_update
    set -g fisher_lock_file $HOME/.cache/fisher_update.lock
    set -g fisher_lock_timeout 3600
    set -g fisher_update_interval 86400

    if test -f $fisher_last_update_file
        set last_update (cat $fisher_last_update_file)
    else
        set last_update 0
    end

    set current_time (date +%s)
    set time_since_update (math $current_time - $last_update)

    if test $time_since_update -gt $fisher_update_interval
        mkdir -p $HOME/.cache
        
        # Check lock file
        set should_update true
        if test -f $fisher_lock_file
            set lock_time (cat $fisher_lock_file)
            set lock_age (math $current_time - $lock_time)
            if test $lock_age -lt $fisher_lock_timeout
                set should_update false
            end
        end
        
        if test $should_update = true
            date +%s > $fisher_lock_file
            echo "Running Fisher Update..."
            fish -c "fisher update && date +%s > $fisher_last_update_file; rm -f $fisher_lock_file" > /tmp/fisher_update.log 2>&1 &
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
end
