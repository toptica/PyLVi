import zmq
import json
import numpy as np
import struct
import re
import operator
from numbers import Number
import functools  # for "rsetattr" and "rgetattr"

tg1 = 0.0
tg2 = 0.0


def rsetattr(obj, attr, val):
    """
    Drop-in replacements for setattr, which can also handle dotted attr strings.
    from: http://stackoverflow.com/questions/31174295/getattr-and-setattr-on-nested-objects
    Args:
        obj: Object
        attr: Attribute (string)
        val: New attribute value

    Returns: result of setattr
    """
    pre, _, post = attr.rpartition('.')
    return setattr(rgetattr(obj, pre) if pre else obj, post, val)


def rgetattr(obj, attr):
    f = operator.attrgetter(attr)
    return f(obj)


# common functions
def heartbeat():
    return "ping"


def message_preprocessing(msg):
    """ :param msg:
    # {commmand_dict};[{descriptor1},{descriptor2}, ...];[data_string1, data_string2, ...]
    # command_dict: dictionary
    # for function calls: {'obj':'object', 'fct':'function'}
    # for attributes: {'obj':'object', 'attr':'attribute', 'access':'r' or 'w'}
    # descriptor: dictionary
    # 'argtype': bool, numeric, string, dict, ndarray
    # 'dtype': bool, string, int16, int32, float32, float64, complex128
    # 'shape': [size, dim], size: number of elements, dim: dimension of 2d ndarray
    # 'argname': str: argument name (empty if positional argument)
    # data_string: encoded data string
    # bool: "True", "False", is encoded as 0 and 1 in int16 binary format
    # numeric: binary
    # sting: string
    # dict: json
    # ndarray: binary
    return: isattr, command, args

    Example for msg: '{"obj":"test","fct":"array"};[{"argtype":"ndarray","dtype":"int16","shape":[3]}];[\xe4\x01\xe4\x01\xe4\x01]'
    """

    # 1. get command or attribute
    offset = re.search(b'};', msg)
    command_dict = json.loads(bytes.decode(msg[:offset.start() + 1]))
    args = []
    argnames = []
    if 'fct' in command_dict:
        # a function is called
        isattr = False
        command = '.'.join(filter(None, (command_dict['obj'], command_dict['fct']))) + '('
        # => "obj.fct("
        # If 'obj' is empty => "fct("
    elif 'attr' in command_dict:
        # an attribute is called
        isattr = True
        attr_obj = command_dict['obj']
        attr_name = command_dict['attr']
        if command_dict['access'] == 'r':
            # get attribute
            command = "".join(['rgetattr(', command_dict['obj'], ',', '\'', command_dict['attr'], '\')'])
            # => "rgetattr(obj, 'attr')"
        elif command_dict['access'] == 'w':
            # set attribute
            command = "".join(['rsetattr(', command_dict['obj'], ',', '\'', command_dict['attr'], '\','])
            # => "rsetattr(obj, 'attr',"
        else:
            raise ValueError('Invalid \'access\' value.')
    else:
        raise SyntaxError
    if not isattr or (isattr and command_dict['access'] == "w"):
        # function call or write attribute
        offset2 = re.search(b'];', msg)
        descriptor_list = json.loads(bytes.decode(msg[offset.end():offset2.start()+1]))
        data_pointer = offset2.end()+1
        # the descriptor_list is a list of dicts; each element represents one argument
        for descriptor in descriptor_list:
            element_size = dtype_to_elementsize(descriptor['dtype'])
            mul = functools.reduce(operator.mul, descriptor['shape'])
            data_string_size = mul * element_size
            data = msg[data_pointer:data_pointer + data_string_size]  # data is bytearray
            if descriptor['argtype'] == 'bool':
                args.append(data == bytearray(b'\x01'))  # b'\x01' is True
                data_pointer += data_string_size + 1
            elif descriptor['argtype'] == 'numeric':
                type_ = {
                    "int16": "h",       # 'h': interpret data as short integer
                    "int32": "i",       # 'i': interpret data as integer
                    "float32": "f",     # 'f': interpret data as float (single-precision)
                    "float64": "d",     # 'd': interpret data as double
                    "complex128": "2d", # 'c': interpret data as complex (two double-precision numbers)
                }[descriptor['dtype']]
                if descriptor['dtype'] == 'complex128':
                    complex_tuple = struct.unpack(type_, data)
                    args.append(complex(complex_tuple[0], complex_tuple[1]))
                else:
                    args.append(struct.unpack(type_, data)[0])
                data_pointer += data_string_size + 1
            elif descriptor['argtype'] == 'string':
                args.append(str(data, 'utf-8'))
                data_pointer += data_string_size + 1
            elif descriptor['argtype'] == 'dict':
                args.append(json.loads(data.decode("utf-8")))
                data_pointer += data_string_size + 1
            elif descriptor['argtype'] == 'ndarray':
                # one and multi-dimensional numpy arrays
                # todo: little endian is used here; how can be specified that big endian interpretation is used?
                args.append(np.fromstring(data, descriptor['dtype']))  # np.frombuffer can be used as well -> no additional buffer is used
                args[len(args)-1].shape = tuple(descriptor['shape'])    # change shape of array; only important for array with more than 1 dim
                data_pointer += data_string_size + 1
            argnames.append(descriptor['argname'])
    return isattr, command, args, argnames


def dtype_to_elementsize(dtype):
    return {
        "bool": 1,
        "string": 1,
        "int16": 2,
        "int32": 4,
        "float32": 4,
        "float64": 8, 
        "complex128": 16 
    }.get(dtype, 0)


def create_transmit_data(data_in):
    if not isinstance(data_in, tuple):
        # only one return of called function
        data_in = (data_in,)
    descriptor_list = []
    data_list = []
    argname = ''
    for k, dataset in enumerate(data_in):  # iterate over all return values
        print('Return value ' + str(k))
        print(dataset)
        print('Dataset type ' + str(type(dataset)))
        if isinstance(dataset, np.ndarray):
            print('dataset ndarray')
            # encode numpy arrays as binary data
            data_list.append(dataset.tostring())
            # create descriptor
            descriptor_list.append(dict(argtype='ndarray', dtype=str(dataset.dtype), shape=dataset.shape, argname=argname))
        elif isinstance(dataset, Number) and not isinstance(dataset, bool):
            # "Number" from package "numbers". Checks if datatype is numeric. Bool is also interpreted as Number!
            print('dataset Number')
            if isinstance(dataset, float):
                dtype_ = 'float64'
                data_list.append(struct.pack('d', dataset))  # 'd': Converted to double binary data (i.e. 8 bytes)
            if isinstance(dataset, complex):
                dtype_ = 'complex128'
                data_list.append(struct.pack('2d', dataset.real, dataset.imag))  # '2d': Converted to two double binary data values (i.e. 8 bytes)
            if isinstance(dataset, int):
                dtype_ = 'int32'
                data_list.append(struct.pack('i', dataset))  # 'i': Converted to int binary data (i.e. 4 bytes)
            descriptor_list.append(dict(argtype='numeric', dtype=dtype_, shape=(1,), argname=argname))
        elif isinstance(dataset, bool):
            print('dataset bool')
            if dataset:
                data_list.append(bytes(b'\x01'))
            else:
                data_list.append(bytes(b'\x00'))
            descriptor_list.append(dict(argtype='bool', dtype='bool', shape=(1,), argname=argname))
        elif isinstance(dataset, str):
            data_list.append(str.encode(dataset))
            descriptor_list.append(dict(argtype='string', dtype='string', shape=(len(dataset),), argname=argname))
        elif isinstance(dataset, dict):
            json_str = json.dumps(dataset)
            data_list.append(str.encode(json_str))
            # json.dumps returns JSON string for the dictionary. This string is then encoded to binary.
            descriptor_list.append(dict(argtype='dict', dtype='string', shape=(len(json_str),), argname=argname))
        else:
            data_out = json.dumps(data_in)
    return b"".join([json.dumps(descriptor_list).encode(), b';[', b','.join(data_list), b']'])


if __name__ == '__main__':
    """
    if imported as a module include the following code into the main module
    """
    # open socket for TCP communication
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    zmq_adr = "tcp://127.0.0.1:5555"
    socket.bind(zmq_adr)
    print('Program startup completed')

    while True:
        #tg1 = time.time()
        #t_start = time.time()
        #  Wait for request from client
        #t1 = time.time()
        message = socket.recv()  # this part of the code seems to consume most of the time for large datasets
        if message == b"__quit__":
            socket.unbind(zmq_adr)
            print("Close ZMQ connection")
            socket.send(b"Close ZMQ connection")
            break
        #t2 = time.time()
        # print('time msg receive: %.4f' % (t2 - t1))
        # print("Received request: %s" % message)
        #t1 = time.time()
        isattr, command, args, argnames = message_preprocessing(message)
        #t2 = time.time()
        #print('time msg_preprocessing: %.4f' % (t2 - t1))

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

            #t1 = time.time()
            print("Calling message: %s" % calling_msg)
            if args != []:
                print("Arguments: " + str(args))
                print("Argument names: " + str(argnames))

            r = eval(calling_msg)
            #t2 = time.time()
            #print('time eval message: %.4f' % (t2 - t1))
            # print("Return value: ", r)
            # print("Type: ", type(r))
            #t1 = time.time()
            data_to_transmit = create_transmit_data(r)
            #t2 = time.time()
            #print('time create transmit data: %.4f' % (t2 - t1))

            # t1 = time.time()
            # json_data = json.dumps(r, cls=NumpyEncoder)
            # t2 = time.time()
            # print('time json.dumps: %.4f' % (t2 - t1))
            # socket.send(bytearray(json_data, 'utf-8'))
            # ecops_sigpro.process_data(message)

            #t1 = time.time()
            # data_to_transmit = bytearray(transmit_data)
            # print("Transmit data: %s" % data_to_transmit)
            socket.send(data_to_transmit)
            #t2 = time.time()
            #print('time socket send: %.4f' % (t2 - t1))
            #t_end = time.time()
            #print('complete execution time: %.4f' % (t_end - t_start))
            #print('')
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
