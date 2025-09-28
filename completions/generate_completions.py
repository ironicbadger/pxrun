#!/usr/bin/env python3
"""Generate shell completions for pxrun."""

import os
import sys
import click

# Add parent directory to path to import pxrun
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.cli.__main__ import cli


def generate_bash_completion():
    """Generate bash completion script."""
    return '''# Bash completion for pxrun
# Installation:
#   - Copy to /etc/bash_completion.d/pxrun or
#   - Source in your ~/.bashrc: source /path/to/pxrun.bash

_pxrun_completion() {
    local IFS=$'\\n'
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
'''


def generate_zsh_completion():
    """Generate zsh completion script."""
    return '''#compdef pxrun
# Zsh completion for pxrun
# Installation:
#   - Copy to directory in $fpath (e.g., /usr/local/share/zsh/site-functions/_pxrun)
#   - Or add to ~/.zshrc: fpath=(/path/to/completions $fpath)

_pxrun() {
    local -a completions
    local -a response
    (( ! $+commands[pxrun] )) && return 1

    response=("${(@f)$(env COMP_WORDS="${words[*]}" COMP_CWORD=$((CURRENT-1)) _PXRUN_COMPLETE=zsh_complete pxrun)}")

    for type arg in ${response}; do
        case $type in
            plain)
                completions+=($arg)
                ;;
            dir)
                _path_files -/
                ;;
            file)
                _path_files -f
                ;;
        esac
    done

    if [ -n "$completions" ]; then
        compadd -U -V unsorted -a completions
    fi
}

compdef _pxrun pxrun
'''


def generate_fish_completion():
    """Generate fish completion script."""
    return '''# Fish completion for pxrun
# Installation:
#   - Copy to ~/.config/fish/completions/pxrun.fish

function _pxrun_completion
    set -l response (env COMP_WORDS=(commandline -cp) COMP_CWORD=(commandline -t) _PXRUN_COMPLETE=fish_complete pxrun)

    for completion in $response
        set -l metadata (string split "," $completion)

        if test $metadata[1] = "dir"
            __fish_complete_directories $metadata[2]
        else if test $metadata[1] = "file"
            __fish_complete_path $metadata[2]
        else
            echo $metadata[2]
        end
    end
end

complete -c pxrun -f -a "(_pxrun_completion)"
'''


def main():
    """Generate all completion scripts."""
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Generate bash completion
    bash_file = os.path.join(script_dir, 'pxrun.bash')
    with open(bash_file, 'w') as f:
        f.write(generate_bash_completion())
    print(f"Generated: {bash_file}")

    # Generate zsh completion
    zsh_file = os.path.join(script_dir, '_pxrun')
    with open(zsh_file, 'w') as f:
        f.write(generate_zsh_completion())
    print(f"Generated: {zsh_file}")

    # Generate fish completion
    fish_file = os.path.join(script_dir, 'pxrun.fish')
    with open(fish_file, 'w') as f:
        f.write(generate_fish_completion())
    print(f"Generated: {fish_file}")

    print("\nInstallation instructions:")
    print("\nBash:")
    print("  sudo cp pxrun.bash /etc/bash_completion.d/")
    print("  or add to ~/.bashrc: source /path/to/pxrun.bash")
    print("\nZsh:")
    print("  sudo cp _pxrun /usr/local/share/zsh/site-functions/")
    print("  or add to ~/.zshrc: fpath=(/path/to/completions $fpath)")
    print("\nFish:")
    print("  cp pxrun.fish ~/.config/fish/completions/")


if __name__ == '__main__':
    main()