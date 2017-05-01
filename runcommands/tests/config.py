from runcommands.config import Config as BaseConfig, RunConfig


class Config(BaseConfig):

    config_file = 'runcommands.tests:commands.cfg'

    def __init__(self, *defaults, run=None, **overrides):
        if run is None:
            run = RunConfig(config_file=self.config_file)
        super().__init__(*defaults, run=run, **overrides)
