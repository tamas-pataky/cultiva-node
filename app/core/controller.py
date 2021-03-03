import json
import uuid
import traceback

from app.core.wrappers import retry
from app.core.command import InvalidCommandError

@retry
def reset_connection(serial_connection, logger):
    with serial_connection.lock:
        logger.log('Resetting serial connection ...')
        response = serial_connection.reset()

@retry
def open_ports(serial_connection, ports, logger):
    ports_string = ', '.join(list(set(map(str, ports))));

    logger.log('Opening ports ' + ports_string + ' ...')
    
    response = None
    result = None
    
    command_id = str(uuid.uuid4())
    command = parse_command(command_id, 'open(' + ports_string + ')')
    
    try:
        with serial_connection.lock:
            response = serial_connection.send(command_id, command)
    
        result = json.loads(response)   

        if result['success'] == True and result['message'] == 'opened(' + ports_string + ')':
            return
        else:            
            raise Exception('Result from controller does not indicate success')
    except:
        error = 'Error opening ports ' + str(ports_string) + ' ... Request: ' + str(command) + ' Response: ' + str(response) + ' Result: ' + str(result)
        logger.error(traceback.format_exc())
        logger.error(error)        
        raise Exception(error)
 
@retry
def close_ports(serial_connection, ports, logger):
    ports_string = ', '.join(list(set(map(str, ports))));

    logger.log('Closing ports ' + ports_string + ' ...')
    
    response = None
    result = None

    command_id = str(uuid.uuid4())
    command = parse_command(command_id, 'close(' + ports_string + ')')

    try:
        with serial_connection.lock:
            response = serial_connection.send(command_id, command)            
       
        result = json.loads(response)

        if result['success'] == True and result['message'] == 'closed(' + ports_string + ')':
            return
        else:
            raise Exception('Result from controller does not indicate success')
    except:
        error = 'Error closing ports ' + str(ports_string) + ' ... Request: ' + str(command) + ' Response: ' + str(response) + ' Result: ' + str(result)
        logger.error(traceback.format_exc())
        logger.error(error)
        raise Exception(error)

@retry
def read_sensors(serial_connection, read_instructions, logger):  
    if len(read_instructions) == 0:
        return []

    logger.log('Reading sensors ...')
    
    response = None
    result = None
    
    command_id = str(uuid.uuid4())
    command = make_command(command_id, 'read', read_instructions)

    try:
        with serial_connection.lock:
            response = serial_connection.send(command_id, command)

        result = json.loads(response)
        
        if result['success'] == True and result['message'].startswith('read('):
            return list(map(int, result['message'].replace('read(', '')[:-1].split(',')))
        else:
            raise Exception('Result from controller does not indicate success')
    except:
        error = 'Error reading sensors ... Request: ' + str(command) + ' Response: ' + str(response) + ' Result: ' + str(result)
        logger.error(traceback.format_exc())
        logger.error(error)
        raise Exception(error)

@retry
def run_command(serial_connection, command_text, logger):  
    response = None
    result = None
    
    command_id = str(uuid.uuid4())
    command = parse_command(command_id, command_text)

    try:
        with serial_connection.lock:
            response = serial_connection.send(command_id, command)

        result = json.loads(response)
        
        if result['success'] == True:
            return result
        else:
            raise Exception('Result from controller does not indicate success')
    except:
        error = 'Error running command ... Request: ' + str(command) + ' Response: ' + str(response) + ' Result: ' + str(result)
        logger.error(traceback.format_exc())
        logger.error(error)
        raise Exception(error)
        
def parse_command(command_id, command):
    if command is None:
        raise InvalidCommandError(command)

    if '(' not in command:
        raise InvalidCommandError(command)

    type = command[0:command.index('(')]
    
    arguments = list(map(lambda i : i.strip(), command.replace(type, "")[1:-1].split(',')))
    
    return make_command(command_id, type, arguments)

def make_command(command_id, type, arguments):
    data = {}
    data['id'] = command_id
    data['command'] = type
    data['arguments'] = arguments

    return json.dumps(data)