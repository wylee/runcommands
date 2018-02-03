complete \
    --no-files \
    -c run -c runcommand -c runcommands \
    -a '(runcommands-complete -- \
             (commandline) \
             (commandline --current-token) \
             (commandline --cursor) \
             fish)'
