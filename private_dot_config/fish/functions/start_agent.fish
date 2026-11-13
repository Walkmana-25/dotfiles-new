function start_agent
    echo "Initializing new SSH agent ..."
    ssh-agent -c | sed -e 's/^echo/#echo/' -e 's/^setenv \([A-Z_]*\) \(.*\);/set -gx \1 \2/' >$SSH_ENV
    echo succeeded
    chmod 600 $SSH_ENV
    . $SSH_ENV >/dev/null
    ssh-add
end
