complete \
    --no-files \
    -c ${base_command_name} \
    -a '(runcommands-complete-base-command -- \
        ${base_command_path} \
        (commandline) \
        (commandline --current-token) \
        (commandline --cursor) \
        fish)'
