setenv SSH_ENV $HOME/.ssh/environment

function start_agent
    echo "Initializing new SSH agent ..."
    ssh-agent -c | sed 's/^echo/#echo/' >$SSH_ENV
    echo succeeded
    chmod 600 $SSH_ENV
    . $SSH_ENV >/dev/null
    ssh-add
end

function test_identities
    ssh-add -l | grep "The agent has no identities" >/dev/null
    if [ $status -eq 0 ]
        ssh-add
        if [ $status -eq 2 ]
            start_agent
        end
    end
end

if uname -a | grep -q WSL
    set -x SSH_AUTH_SOCK $HOME/.ssh/agent.sock
    ss -a | grep -q $SSH_AUTH_SOCK
    if test $status -ne 0
        busybox rm -f $SSH_AUTH_SOCK
        setsid socat UNIX-LISTEN:$SSH_AUTH_SOCK,fork EXEC:"$HOME/npiperelay/npiperelay.exe -ei -s //./pipe/openssh-ssh-agent",nofork >/dev/null 2>&1 &
    end
else
    if [ -n "$SSH_AGENT_PID" ]
        ps -ef | grep $SSH_AGENT_PID | grep ssh-agent >/dev/null
        if [ $status -eq 0 ]
            test_identities
        end
    else
        if [ -f $SSH_ENV ]
            . $SSH_ENV >/dev/null
        end
        ps -ef | grep $SSH_AGENT_PID | grep -v grep | grep ssh-agent >/dev/null
        if [ $status -eq 0 ]
            test_identities
        else
            start_agent
        end
    end
end
