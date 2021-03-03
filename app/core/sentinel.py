import os
import sys
import psutil
import requests
import traceback
import socket
import uuid

from datetime import datetime
from tinydb import TinyDB, Query
from flask import current_app

from app.core.wrappers import retry

class CpuProbe:
    def name(self):
        return 'CPU'
        
    def run(self):
        return round(psutil.cpu_percent(), 2)
        
class MemoryProbe:
    def name(self):
        return 'Memory'
        
    def run(self):
        return round(psutil.virtual_memory().available * 100 / psutil.virtual_memory().total, 1)
        
class LocalIpAddressProbe:
    def name(self):
        return 'Local IP address'
        
    def run(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        try:
            s.connect(('10.255.255.255', 1))
            ip = s.getsockname()[0]
        except Exception:
            ip = '127.0.0.1'
        finally:
            s.close()
        return ip

class InternetProbe:
    def __init__(self, logger):
        self.logger = logger
        self.repository = SentinelRepository()
        self.alert_factory = AlertFactory()
        
    def name(self):
        return 'Internet access'
        
    def run(self):
        is_internet_up = self.is_internet_up()
                
        if not is_internet_up:
            self.handle_internet_down()
        else:
            self.handle_internet_up()
        
        if is_internet_up:
            return 'OK'
        else:
            raise Exception('No internet access')
            
    def handle_internet_up(self):
        was_up_last_time = self.was_up_last_time()
        
        if not was_up_last_time:
            self.repository.update_state({'internet': { 'status': 'up', 'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S') }})
            self.repository.insert_alert(self.alert_factory.internet_up())
            self.logger.log('Internet came back up ... An alert has been raised')
            
    def handle_internet_down(self):
        was_up_last_time = self.was_up_last_time()
                                               
        if was_up_last_time:
            self.repository.update_state({'internet': { 'status': 'down', 'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S') }})
            self.repository.insert_alert(self.alert_factory.internet_down())    

            self.logger.error('Internet went down ... An alert has been raised')
        else:
            was_downForProlongedPeriod_last_time = self.was_downForProlongedPeriod_last_time()
            down_since = self.went_down_at()
            minutes_elapsed = (datetime.now() - down_since).total_seconds() / 60.0
            
            if minutes_elapsed > 1 and not was_downForProlongedPeriod_last_time:
                self.repository.update_state({'internet': { 'status': 'downForProlongedPeriod', 'time': down_since.strftime('%Y-%m-%d %H:%M:%S') }})
                self.repository.insert_alert(self.alert_factory.internet_down_for_prolonged_period(down_since))
    
    def was_up_last_time(self):         
        previous_status = self.get_previous_status()
        return previous_status != 'down' and previous_status != 'downForProlongedPeriod'
        
    def was_downForProlongedPeriod_last_time(self):
        return self.get_previous_status() == 'downForProlongedPeriod'
        
    def get_previous_status(self):
        previous_state = self.repository.get_state()
        
        if not previous_state:
            return 'unknown'
        
        if not 'internet' in previous_state:
            return 'unknown'
        
        if not 'status' in previous_state['internet']:
            return 'unknown'
            
        return previous_state['internet']['status']
        
    def went_down_at(self):
        previous_state = self.repository.get_state()['internet']        
        return datetime.strptime(previous_state['time'], '%Y-%m-%d %H:%M:%S')
    
    def is_internet_up(self, url='http://www.google.com/', timeout=5):
        try:
            _ = requests.head(url, timeout=timeout)
            return True
        except requests.ConnectionError:
            return False


class SentinelRepository:
    def __init__(self):        
        self.sentinel_db = TinyDB('app/core/sentinel.json')
        self.state_table = self.sentinel_db.table('state')
        self.alerts_table = self.sentinel_db.table('alerts')
        
    def insert_alert(self, alert):
        a = Query()        
        if self.alerts_table.get(a.key == alert['key']) is None:        
            self.alerts_table.insert(alert)
        
    def get_alerts(self):
        return self.alerts_table.all()
        
    def delete_alert(self, alert):
        a = Query()  
        return self.alerts_table.remove(a.id == alert['id'])
        
    def update_alert(self, alert):
        a = Query()
        return self.alerts_table.update(alert, a.id == alert['id'])
        
    def has_alerts(self):
        return len(self.alerts_table) > 0
        
    def get_state(self):
        return self.state_table.get(doc_id=len(self.state_table))

    def update_state(self, state):
        if len(self.state_table) == 0:
            self.state_table.insert({ 'internet': { 'status': 'unknown', 'time': '' } })
        
        current_state = self.get_state()
            
        if ('internet' in state):
            current_state['internet']['status'] = state['internet']['status']
            current_state['internet']['time'] = state['internet']['time']
            
        self.state_table.truncate()
        self.state_table.insert(current_state)
            
class AlertFactory:
    def internet_up(self):
        return {
            'id': str(uuid.uuid4()),
	        'key': 'InternetUp(' + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ')',
	        'time': datetime.now().isoformat(),
	        'type': 'InternetUp',
            'severity': 0,
	        'properties': '{"time":"' + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '"}'
        }
        
    def internet_down(self):
        return {
            'id': str(uuid.uuid4()),
	        'key': 'InternetDown(' + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ')',
	        'time': datetime.now().isoformat(),
	        'type': 'InternetDown',
            'severity': 2,
	        'properties': '{"time":"' + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '"}'
        }
        
    def internet_down_for_prolonged_period(self, since):
        return {
            'id': str(uuid.uuid4()),
	        'key': 'InternetDownForProlongedPeriod(' + since.strftime('%Y-%m-%d %H:%M:%S') + ')',
	        'time': datetime.now().isoformat(),
	        'type': 'InternetDownForProlongedPeriod',
            'severity': 3,
	        'properties': '{"time":"' + since.strftime('%Y-%m-%d %H:%M:%S') + '"}'
        }
        
    def sensor_status_changed(self, sensor, status, reading, severity):
        return {
            'id': str(uuid.uuid4()),
	        'key': 'SensorStatusChanged(sensorId: ' + str(sensor['id']) + ', status: "' + status + '")',
	        'time': datetime.now().isoformat(),
	        'type': 'SensorStatusChanged',
            'severity': severity,
	        'properties': '{"sensorName":"' + sensor['name'] + '","status":"' + status + '","measuredValue":' + str(reading) + '}'
        }
        
    def irrigation_run_failed(self, stacktrace):
        return {
            'id': str(uuid.uuid4()),
	        'key': 'IrrigationRunFailed(' + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '")',
	        'time': datetime.now().isoformat(),
	        'type': 'IrrigationRunFailed',
            'severity': 2,
	        'properties': '{"stacktrace":"' + stacktrace + '" }'
        }
        
class AlertDispatcher:
    @retry
    def dispatch_to_phone(self, alert):
        print('TODO')
        
    @retry
    def dispatch_to_hub(self, alert):
        payload = alert.copy()
        payload.pop('id', None)
        
        notification_address = current_app.config['HUB_ADDRESS'] + '/api/notifications?nodeId=' + str(current_app.config['NODE_ID'])    
        response = requests.post(notification_address, json=payload, verify=False)
        response.raise_for_status()
     
class Sentinel:
    def __init__(self, logger):
        self.logger = logger
        self.repository = SentinelRepository()
        self.alert_factory = AlertFactory()
        self.alert_dispatcher = AlertDispatcher()
        
    def run_programme(self):
        self.logger.log_h1('Starting Sentinel Programme', True, True)
        
        self.run_probes()
        self.sync_with_hub()
        self.dispatch_alerts()
        
        self.logger.log_h1('Finished Sentinel Programme', True, True)
                
        return 'Sentinel run finished successfully'
        
    def run_probes(self):
        try:
            results = {}
            
            self.logger.log_h2('Starting probes', True, True)
                
            probes = [
                InternetProbe(self.logger),
                CpuProbe(),
                MemoryProbe(),
                LocalIpAddressProbe()
            ]
            
            for probe in probes:
                try:
                    results[probe.name()] = probe.run()
                except:
                    self.logger.warning("Probe '" + probe.name() + "' failed")
                    results[probe.name()] = 'Failed'
                    
            self.logger.log_h3_object('Probes', results, True, True)
                    
            self.logger.log_h2('Finished probes')
        except:
            self.logger.error(traceback.format_exc())
            
    def sync_with_hub(self):
        try:
            is_internet_up = InternetProbe(self.logger).is_internet_up()
            
            if is_internet_up:
                self.logger.log_h2('Syncing started', True, False)
                
                sync_address = current_app.config['HUB_ADDRESS'] + '/api/node/sync'
                
                payload = {
                    'nodeId': current_app.config['NODE_ID'],
                    'localIpAddress': LocalIpAddressProbe().run()
                }
                
                response = requests.post(sync_address, json=payload, verify=False)
                response.raise_for_status()
                
                self.logger.log_h2('Syncing finished', False, True)
            else:
                self.logger.log_h2('Syncing deferred', True, True)
        except:
            self.logger.error(traceback.format_exc())
            
    def dispatch_alerts(self): 
        try:
            results = {}
        
            self.logger.log_h2('Starting dispatching alerts', True, False)
                    
            is_internet_up = InternetProbe(self.logger).is_internet_up()
            
            if self.repository.has_alerts(): 
                for alert in self.repository.get_alerts():                                
                    if is_internet_up:
                        self.alert_dispatcher.dispatch_to_hub(alert)
                        self.repository.delete_alert(alert) 
                        results[alert['key']] = 'Dispatched to Hub'
                    else:
                        results[alert['key']] = 'Deferred'
                        
                    if alert['severity'] == 3 and not 'dispatched_to_phone' in alert:
                        self.alert_dispatcher.dispatch_to_phone(alert)                
                        alert['dispatched_to_phone'] = True
                        self.repository.update_alert(alert)
                        results[alert['key']] = 'Dispatched to GSM'
                             
                self.logger.log_h3_object('Alerts', results, True, True) 
                
            self.logger.log_h2('Finished dispatching alerts', False, True)
        except:
            self.logger.error(traceback.format_exc())
            
