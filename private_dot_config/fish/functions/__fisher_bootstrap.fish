function __fisher_bootstrap
    # Pure bootstrap of fisher itself (no throttling here).
    # Callers are responsible for gating how often this runs.
    if functions -q fisher
        return 0
    end

    echo "Installing Fisher..."
    mkdir -p $HOME/.cache

    # fisher is a fish function, not an external command; source it directly
    curl -fsSL --max-time 30 https://raw.githubusercontent.com/jorgebucaran/fisher/main/functions/fisher.fish | source
    if functions -q fisher
        fisher install jorgebucaran/fisher
        return 0
    end

    # curl/source failed (e.g. offline): fail quietly
    return 1
end
