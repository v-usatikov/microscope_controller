class StopIndicator:
    def has_stop_requested(self):
        raise NotImplementedError


class Machine:
    name: str = None
    number: int = None

class MachineCsvReader:

    def read_csv(self, filename: str) -> Machine:
        """

        :rtype: Machine
        """
        machinbe = Machine()
        machinbe.name = csv.line[1]
        return machinbe


reader = MachineCsvReader();
machines = reader.read_csv('file.csv')
machines.name