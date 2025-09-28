# Fish completion for pxrun
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
