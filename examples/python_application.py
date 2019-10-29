import zmq
import numpy as np
from python_zmq_server import *

tg1 = 0.0
tg2 = 0.0

# === enter the application code here ===

class Inner:
    def __init__(self):
        self.var_double_inner = 54.23


class Test:
    def __init__(self):
        self.var_int = 42
        self.var_double = 12.34
        self.var_complex = 7.2 + 1j*17.23
        self.var_string = "Hello World!"
        self.var_bool = True
        self.var_nparray = np.array([1.2, 2, 3, 4, 5])
        self.var_nparray_2d = np.array([[1.2, 2.8, 3.28, 44, 55], [18.2, 2.58, 3.3, 4.9, 5.1]])
        self.var_nparray_complex = np.array([1.2+5.7j, 2.95+9.3j, 3.9+9.87j, 4.1+98.88j, 5.01+2.1j])
        self.var_nparray_complex_2d = np.array([[1.2 + 5.7j, 2.95 + 9.3j, 3.9 + 9.87j, 4.1 + 98.88j, 5.01 + 2.1j],
                                                [8.3 + 1.2j, 7.2 + 9.66j, 1.1 + 11.2j, 4.5 + 9.2j, 5.99 + 8.2j]])
        self.var_dict = \
        {'Name': 'Zap', 
         'Number': 25.3, 
         'Boolean': True,
         'Array': self.var_nparray.tolist()
         }
        self.inner = Inner()

    def test(self, pos1=1, pos2=2):
        return pos1-pos2

    def dict_return(self):
        ar = np.array([1,2,3])
        return {'Name': 'Zap', 'Number': 42.3, 'Boolean': True, 'Array': ar.tolist()}
        # return {"Name": "Zap", "Number": 42.3, "Boolean": True}

    def dict_send(self, dictionary):
        print(dictionary)
        print(dictionary['Array'])
        print(type(dictionary['Array']))
        return dictionary["Number"]

    def multi_array_test(self, a1, a2, a3):
        return 2*a1, 2*a2, 2*a3

    @staticmethod
    def my_sum(a, b):
        return a + b

    def fct_array(self, array):
        print(array)
        print(type(array))
        return array

    def fct_numeric(self, num):
        # return np.array([num, num, num])
        print(num)
        print(type(num))
        return num

    def fct_boolean(self, bl):
        print(bl)
        return bl

    def fct_string(self, string):
        return string+'_return'
    
    def fct_dict(self, di):
        return di

# create test object
test = Test()


def array_test_function(test_array):
    print('test function executed!')

# === end of application code ===

# open socket for TCP communication
context = zmq.Context()
socket = context.socket(zmq.REP)
zmq_adr = "tcp://127.0.0.1:5555"
socket.bind(zmq_adr)
print('Program startup completed')

while True:
    # tg1 = time.time()
    # t_start = time.time()
    # Wait for request from client
    # t1 = time.time()
    message = socket.recv()  # this part of the code seems to consume most of the time for large datasets
    if message == b"__quit__":
        socket.unbind(zmq_adr)
        print("Close ZMQ connection")
        socket.send(b"Close ZMQ connection")
        break
    # t2 = time.time()
    # print('time msg receive: %.4f' % (t2 - t1))
    # print("Received request: %s" % message)
    # t1 = time.time()
    isattr, command, args, argnames = message_preprocessing(message)
    # t2 = time.time()
    # print('time msg_preprocessing: %.4f' % (t2 - t1))

    try:
        if isattr and args == []:  # get attribute
            calling_msg = command
        else:  # call function or set attribute
            arglist = []
            size = len(args)
            for i in range(size):
                if argnames[i] == '':
                    arglist.append('args[%d]' % i)
                else:
                    arglist.append(str(argnames[i]) + '=args[%d]' % i)
            calling_msg = command + ','.join(arglist) + ')'

        # t1 = time.time()
        print("Calling message: %s" % calling_msg)
        if args != []:
            print("Arguments: " + str(args))
            print("Argument names: " + str(argnames))

        r = eval(calling_msg)
        # t2 = time.time()
        # print('time eval message: %.4f' % (t2 - t1))
        # print("Return value: ", r)
        # print("Type: ", type(r))
        # t1 = time.time()
        data_to_transmit = create_transmit_data(r)
        # t2 = time.time()
        # print('time create transmit data: %.4f' % (t2 - t1))

        # t1 = time.time()
        # json_data = json.dumps(r, cls=NumpyEncoder)
        # t2 = time.time()
        # print('time json.dumps: %.4f' % (t2 - t1))
        # socket.send(bytearray(json_data, 'utf-8'))
        # ecops_sigpro.process_data(message)

        # t1 = time.time()
        # data_to_transmit = bytearray(transmit_data)
        # print("Transmit data: %s" % data_to_transmit)
        socket.send(data_to_transmit)
        # t2 = time.time()
        # print('time socket send: %.4f' % (t2 - t1))
        # t_end = time.time()
        # print('complete execution time: %.4f' % (t_end - t_start))
        # print('')
        # socket.send(b"Hello")
    except NameError:
        print("except NameError")
        socket.send(b"Unknown command")
        raise
    except SyntaxError:
        print("except SyntaxError")
        socket.send(b"Invalid syntax")
        raise
    except:
        print("except")
        socket.send(b"Unknown error")
        raise
