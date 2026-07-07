set -x LANG ja_JP.utf8
set -x ELECTRON_OZONE_PLATFORM_HINT auto

if status is-interactive
    # すでにtmux内、またはSSH接続時はスキップ
    if not set -q TMUX; and not set -q SSH_TTY

        # OSに応じてtmuxのパスを特定
        set -l tmux_path ""
        switch (uname)
            case Darwin # Macの場合
                if test -f /opt/homebrew/bin/tmux
                    set tmux_path /opt/homebrew/bin/tmux # Apple Silicon
                else if test -f /usr/local/bin/tmux
                    set tmux_path /usr/local/bin/tmux     # Intel Mac
                else
                    set tmux_path (which tmux)            # その他
                end
            case Linux # Linuxの場合
                set tmux_path (which tmux)
        end

        # tmuxのパスが有効で、実行可能であれば起動
        if test -n "$tmux_path"; and test -x "$tmux_path"
            exec $tmux_path
        end
    end
end

# setup fisher plugin manager
setup_fisher

# set fzf keybinding
fzf_configure_bindings --directory=\cd --git_log= --git_status= --processes= --variables=

set -gx FZF_ALT_C_OPTS "--preview 'eza --tree --icons --color=always --level=3 {} 2>/dev/null | head -200' --preview-window=down:60%:wrap"
set -g fzf_fd_opts --max-depth 10 -H


set -g fish_greeting ""

set -g __fish_greeting_file "$HOME/.config/fish/greeting.txt"


function fish_greeting
    if test -f "$__fish_greeting_file"
        set_color cyan
        echo "Welcome to "(hostname)"'s fish shell!"
        set_color normal
        while read -l line
            echo "  $line"
        end < "$__fish_greeting_file"
    end
end

fish_vi_key_bindings default
bind -M insert -m default \cc force-repaint
bind -M insert \cf forward-char

starship init fish | source

test -f "$HOME/.cargo/env.fish" && source "$HOME/.cargo/env.fish"

bind -M insert ctrl-e cdf
bind -M default ctrl-e cdf
