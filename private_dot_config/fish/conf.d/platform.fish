if uname -a | grep -q Darwin
    alias trash-put='trash'
else
    if status is-interactive
        and not set -q TMUX
        and not set -q SSH_CLIENT
        exec tmux
    end
end
