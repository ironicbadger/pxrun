#compdef pxrun
# Zsh completion script for pxrun
# Generated for pxrun CLI tool

_pxrun() {
    local -a completions
    local -a completions_with_descriptions
    local -a response
    (( ! $+commands[pxrun] )) && return 1

    response=("${(@f)$(env COMP_WORDS="${words[*]}" COMP_CWORD=$((CURRENT-1)) _PXRUN_COMPLETE=zsh_complete pxrun)}")

    for type arg in ${response}; do
        if [[ "$type" == "plain" ]]; then
            completions+=($arg)
        elif [[ "$type" == "dir" ]]; then
            _path_files -/
        elif [[ "$type" == "file" ]]; then
            _path_files -f
        fi
    done

    if [ -n "$completions" ]; then
        compadd -U -V unsorted -a completions
    fi
}

# Try to use click's built-in completion if available
if command -v pxrun >/dev/null 2>&1; then
    # Attempt to get zsh completion from click
    COMPLETION_SCRIPT=$(pxrun --show-completion-zsh 2>/dev/null)
    if [ -n "$COMPLETION_SCRIPT" ]; then
        eval "$COMPLETION_SCRIPT"
    else
        compdef _pxrun pxrun
    fi
else
    compdef _pxrun pxrun
fi