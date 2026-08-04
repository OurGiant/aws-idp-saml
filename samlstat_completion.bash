# Bash completion for samlstat
# Source this file or add to ~/.bash_completion.d/
#   source ~/repo/devops/aws-idp-saml/samlstat_completion.bash

_samlstat_profiles() {
    local samlsts="$HOME/.aws/samlsts"
    if [ -f "$samlsts" ]; then
        grep -oP '(?<=^\[)[^]]+' "$samlsts" | grep -v -i -E '^(Fed-|global$)'
    fi
}

_samlstat() {
    local cur prev words cword
    _init_completion || return

    local subcommands="status auth creds pin"
    local status_flags="-f -v -u -x -p -c --filter --valid --unknown --expired --profile --creds --json --no-color"
    local auth_flags="-f -p -x --filter --profiles --expired --fastpass --stored-password --no-stored-password --debug --browser --encrypted --quiet"
    local creds_flags="-f -p --filter --profiles"
    local pin_flags="-d -l --delete --list"

    # Determine if a subcommand has been given
    local subcmd=""
    for ((i=1; i < cword; i++)); do
        case "${words[i]}" in
            status|s) subcmd="status"; break ;;
            auth|a) subcmd="auth"; break ;;
            creds|c) subcmd="creds"; break ;;
            pin) subcmd="pin"; break ;;
        esac
    done

    case "$subcmd" in
        auth)
            case "$prev" in
                -f|--filter|-b|--browser)
                    # -f takes a string, -b takes browser name
                    if [ "$prev" = "-b" ] || [ "$prev" = "--browser" ]; then
                        COMPREPLY=($(compgen -W "chrome firefox" -- "$cur"))
                    fi
                    return ;;
                -p|--profiles)
                    COMPREPLY=($(compgen -W "$(_samlstat_profiles)" -- "$cur"))
                    return ;;
            esac
            if [[ "$cur" == -* ]]; then
                COMPREPLY=($(compgen -W "$auth_flags" -- "$cur"))
            else
                COMPREPLY=($(compgen -W "$(_samlstat_profiles)" -- "$cur"))
            fi
            ;;
        creds)
            case "$prev" in
                -f|--filter) return ;;
                -p|--profiles)
                    COMPREPLY=($(compgen -W "$(_samlstat_profiles)" -- "$cur"))
                    return ;;
            esac
            if [[ "$cur" == -* ]]; then
                COMPREPLY=($(compgen -W "$creds_flags" -- "$cur"))
            else
                COMPREPLY=($(compgen -W "$(_samlstat_profiles)" -- "$cur"))
            fi
            ;;
        pin)
            if [[ "$cur" == -* ]]; then
                COMPREPLY=($(compgen -W "$pin_flags" -- "$cur"))
            else
                COMPREPLY=($(compgen -W "$(_samlstat_profiles)" -- "$cur"))
            fi
            ;;
        status)
            if [[ "$cur" == -* ]]; then
                COMPREPLY=($(compgen -W "$status_flags" -- "$cur"))
            fi
            ;;
        *)
            # No subcommand yet — complete subcommands and top-level flags
            if [[ "$cur" == -* ]]; then
                COMPREPLY=($(compgen -W "$status_flags" -- "$cur"))
            else
                COMPREPLY=($(compgen -W "$subcommands" -- "$cur"))
            fi
            ;;
    esac
}

complete -F _samlstat samlstat
