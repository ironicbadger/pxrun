# Bash completion for pxrun
# Installation:
#   - Copy to /etc/bash_completion.d/pxrun or
#   - Source in your ~/.bashrc: source /path/to/pxrun.bash

_pxrun_completion() {
    local IFS=$'\n'
    local response

    response=$(env COMP_WORDS="${COMP_WORDS[*]}" COMP_CWORD=$COMP_CWORD _PXRUN_COMPLETE=bash_complete pxrun)

    for completion in $response; do
        IFS=',' read type value <<< "$completion"

        case $type in
            dir)
                COMPREPLY+=("$value/")
                compopt -o dirnames
                ;;
            file)
                COMPREPLY+=("$value")
                compopt -o filenames
                ;;
            plain)
                COMPREPLY+=("$value")
                ;;
        esac
    done

    return 0
}

complete -o default -o bashdefault -F _pxrun_completion pxrun
