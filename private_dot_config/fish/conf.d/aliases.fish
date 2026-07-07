# Common

alias rm='echo "This is not the command you are looking for. You can use trash-put instead. If you really want to use rm, you can use \rm."; false'
alias ls='lsd'
alias ssh='ssh -A'
alias zz='cdf'
alias claude='claude --mcp-config ~/.claude/mcp.json'

# Mac Specific
if test (uname -s) = 'Darwin'
    alias trash-put='trash'
end

# Linux Specific
if test (uname -s) = 'Linux'
    alias crontab='crontab -i'
end
