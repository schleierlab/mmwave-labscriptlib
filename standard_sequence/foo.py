@ABC
class Sequence:
    @abstractmethod
    def run(self):
        ...

@ABC
class MOTSequence(Sequence):
    pass

@ABC
class OpticalPumpingSequence(MOTSequence):
    pass

class MOTCheck(MOTSequence):
    pass
