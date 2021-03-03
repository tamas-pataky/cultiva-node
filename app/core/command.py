import re
import traceback
import importlib
import logging

class InvalidCommandError(Exception):
    def __init__(self, command):
        self.command = command
        self.message = "Command '" + command + "' is invalid"
        super().__init__(self.message)

def run_command(app, logger, command, arguments=[]): 
    with app.app_context():
        try:
            command = re.sub(r'(?<!^)(?=[A-Z])', '_', command).lower()

            function = get_function(command)
            result = function(arguments, app, logger)
                   
            return {
                'success': True,
                'result': result
            }
        except InvalidCommandError as invalidCommandError:
            return {
                'success': False,
                'result': str(invalidCommandError)
            }
        except Exception as e: 
            logging.getLogger('CommandRunner').error(traceback.format_exc())
            
            return {
                'success': False,
                'result': str(e)
            }

def get_function(command):
    if 'irrigation' in command:
        module = importlib.import_module('app.irrigation.module')
        importlib.reload(module)
            
        try:            
            irrigation_commands = getattr(module, 'IrrigationCommands')()
            function = getattr(irrigation_commands, command)

            return function
        except Exception:
            raise InvalidCommandError('Invalid command')

    else:
        module = importlib.import_module('app.core.commands')
        importlib.reload(module)

        try:
            return getattr(module, command)
        except Exception:
            raise InvalidCommandError('Invalid command')