from motor_controller.Phytron_MCC2 import MCC2Communicator, MCC2BoxEmulator
from motor_controller.SmarAct_MCS import MCSCommunicator
from motor_controller.SmarAct_MCS2 import MCS2Communicator
from motor_controller.interface import make_empty_input_file, SerialConnector

emulator = MCC2BoxEmulator(n_bus=5, n_axes=3, realtime=True)
connector = SerialConnector(emulator=emulator, beg_symbol=b'\x02', end_symbol=b'\x03')
emul_communicator = MCC2Communicator(connector)

make_empty_input_file(MCC2Communicator, [], 'MCC2_input_empty.csv')
make_empty_input_file(MCSCommunicator, [], 'MCS_input_empty.csv')
make_empty_input_file(MCS2Communicator, [], 'MCS2_input_empty.csv')