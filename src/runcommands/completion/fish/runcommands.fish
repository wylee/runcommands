complete \
    --no-files \
    -c run -c runcommand -c runcommands -c commands.py \
    -a '(runcommands-complete -- \
             (commandline) \
             (commandline --current-token) \
             (commandline --cursor) \
             fish)'
