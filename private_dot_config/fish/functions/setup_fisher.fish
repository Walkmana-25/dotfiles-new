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

    # Source all conf.d files
    if test -d $fisher_path/conf.d
        for file in $fisher_path/conf.d/*.fish
            if test -f $file
                source $file
            end
        end
    end
end
