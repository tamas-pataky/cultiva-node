import sys
import time
import serial
import logging
import traceback
import json

from datetime import datetime
from datetime import timedelta
from serial.tools import list_ports

from threading import RLock, Thread

class SerialConnection:
    def __init__(self, vendor_id, product_id, logger):
        self.lock = RLock()
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.connection = None
        self.logger = logger
        self.open()        
        
    def open(self):
        device_list = list_ports.comports()
        
        port = '';
                
        for device in device_list:
            if (device.vid != None or device.pid != None):
                if (device.vid == self.vendor_id and device.pid == self.product_id):
                    port = device.device
    
        if port == '':
            raise Exception("Device by vendor id '" + str(self.vendor_id) + "' and product id '" + str(self.product_id) + "' not found")
            
        self.connection = serial.Serial(port, 9600, timeout=10)     
        
        self.warmup();

    def warmup(self):
        ready = False
        
        while ready is not True:
            result = self.receive(2000)
            
            if result == '{"type":"ready"}':
                ready = True
            else:
                self.logger.warning('Ready message from controller not received. Response: ' + result)

    def close(self):
        self.connection.close()

    def reset(self):
        self.close()
        self.open()
                
    def send(self, command_id, command):
        payload = bytes("<" + command + ">", encoding='utf-8')

        for i in range(3): 
            try:   
                self.flush()
                
                self.connection.write(payload)        
                response = self.receive(250)
                
                if not self.is_valid_json(response):
                    raise Exception('Expected acknowledgement, received invalid response: ' + response)
                    
                if self.is_valid_result(response, command_id):
                    return response
        
                if not self.is_valid_acknowledgement(response, command_id):
                    raise Exception('Expected acknowledgement, received invalid response: ' + response)

                response = self.receive(5000)
                
                if not self.is_valid_result(response, command_id):
                    raise Exception('Expected result, received invalid response: ' + response)
                    
                return response
            except:
                self.logger.warning(traceback.format_exc())
                self.logger.warning('Retrying in ' + str(250 * i) + ' milliseconds')
                time.sleep(0.25 * i)
                pass      
             
        self.logger.error('Communication to controller failed. Resetting controller ...')
        self.reset()

        raise Exception('Failed to receive response from controller. Connection has been reset ...')
                
    def receive(self, timeout):
        receive_in_progress = False

        start_marker = '<'
        end_marker = '>'

        line = []

        start = datetime.now()

        while True:
            if (datetime.now() - start).total_seconds() * 1000 > timeout:
                raise Exception('Invalid response received from controller: "' + ''.join(str(char) for char in line) + '", start: ' + str(start) + ', end: ' + str(datetime.now()))

            c = self.connection.read().decode()

            if receive_in_progress == True:
                if str(c) == end_marker:
                    receive_in_progress = False
                    return ''.join(str(char) for char in line)
                else:
                    line.append(c)
            elif str(c) == start_marker:
                receive_in_progress = True
                
    def flush(self):
        try:
            for c in self.connection.read():
                pass
        except:
            pass
                
    def is_valid_acknowledgement(self, response, command_id):                
        if 'commandReceived' in response and command_id in response:
            return True
        elif 'Received' in response and command_id in response:
            return True
        else:
            return False
            
    def is_valid_result(self, response, command_id):            
        return 'result' in response and command_id in response
        
    def is_valid_json(self, response):
        try:
            json_object = json.loads(response)
            return True
        except:            
            return False