function load_env_files
    set -l env_dir $HOME/.config/.env
    if not test -d $env_dir
        return 0
    end
    for file in $env_dir/*.env
        if test -f "$file"
            while read -l line
                string match -q '#*' $line; and continue
                string match -qr '^\s*$' $line; and continue
                set -l cleaned (string replace -r '^export\s+' '' -- $line)
                if string match -qr '^(\w+)=(.*)' -- $cleaned
                    set -l var_name (string match -rg '^(\w+)=' -- $cleaned)
                    set -l var_value (string replace -r '^\w+=' '' -- $cleaned)
                    if set -gx $var_name $var_value 2>/dev/null
                        # success
                    else
                        echo "WARNING: Failed to set $var_name from $file" >&2
                    end
                else if not string match -qr '^\s*$' -- $cleaned
                    echo "WARNING: Skipping invalid line in $file: $line" >&2
                end
            end < "$file" 2>/dev/null
        end
    end
end
