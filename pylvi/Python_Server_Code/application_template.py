import zmq
from python_zmq_server import *

tg1 = 0.0
tg2 = 0.0

# === enter the application code here ===

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
