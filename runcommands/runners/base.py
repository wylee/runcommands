import abc

from .result import Result


class Runner(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def run(self, *args, **kwargs) -> Result:
        raise NotImplementedError('The run method must be implemented in subclasses')
