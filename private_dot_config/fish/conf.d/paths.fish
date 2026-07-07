# Common

fish_add_path $HOME/.cargo/bin
fish_add_path $HOME/.local/bin
fish_add_path $HOME/go/bin
fish_add_path /usr/local/bin

set -gx PNPM_HOME "~/.local/share/pnpm"
if not string match -q -- $PNPM_HOME $PATH
    set -gx PATH "$PNPM_HOME" $PATH
end


# Mac Specific
if test (uname -s) = 'Darwin'
    fish_add_path /opt/homebrew/bin
    fish_add_path /opt/homebrew/sbin
    fish_add_path /usr/local/bin
    fish_add_path /usr/local/sbin
    fish_add_path /opt/homebrew/opt/postgresql@15/bin

    fish_add_path $HOME/.lmstudio/bin
    fish_add_path $HOME/.antigravity/antigravity/bin
    fish_add_path $HOME/.deno/bin
end

# Linux Specific
if test (uname -s) = 'Linux'
end
