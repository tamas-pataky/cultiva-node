import sys
import logging

class Logger:    
    def __init__(self, module, app, loggers = []):         
        self.message_format = '%(asctime)s [%(name)s][%(levelname)s] %(message)s'
        self.date_format = '%Y-%m-%d %H:%M:%S'        
        
        self.module = module
        self.app = app
        self.loggers = loggers

        logging.basicConfig(level=logging.WARNING, format=self.message_format, datefmt=self.date_format)
                    
        self.default_logger = logging.getLogger(module)
        
        self.set_log_level(app.extensions['LOG_LEVEL'])
        logging.getLogger('apscheduler.scheduler').setLevel(logging.ERROR)
                
    def set_log_level(self, level):
        if level == 'error':
            logging.getLogger('werkzeug').setLevel(logging.ERROR)
            self.default_logger.setLevel(logging.ERROR)
        elif level == 'warning':            
            logging.getLogger('werkzeug').setLevel(logging.WARNING)
            self.default_logger.setLevel(logging.WARNING)
        elif level == 'info':
            logging.getLogger('werkzeug').setLevel(logging.INFO)
            self.default_logger.setLevel(logging.INFO)
        elif level == 'debug':
            logging.getLogger('werkzeug').setLevel(logging.DEBUG)
            self.default_logger.setLevel(logging.DEBUG)

    def log_h1(self, title, pad_top=False, pad_bottom=False):              
        self.log((' ' + title + ' ').center(100,"*"), pad_top, pad_bottom)
    
    def log_h2(self, title, pad_top=False, pad_bottom=False):        
        self.log('> ' + title.upper(), pad_top, pad_bottom)

    def log_h3(self, title, pad_top=False, pad_bottom=False):
        self.log(title.upper(), pad_top)
        self.log_divider('—', False, pad_bottom)
        
    def log_h3_object(self, title, data={}, pad_top=False, pad_bottom=False):
        self.log_h3(title, pad_top, False)
        self.log_object(data, False, pad_bottom)

    def log_h3_list(self, title, items, key, value, pad_top=False, pad_bottom=False):
        self.log_h3(title, pad_top, False)
    
        for item in items:
            self.log_variable(item[key], item[value])

        if pad_bottom:
            self.log(' ')
        
    def log_object(self, data, pad_top=False, pad_bottom=False):
        if data is None:
            return

        if pad_top:
            self.log(' ')
        
        for attr, value in data.items():
            self.log_variable(attr.title(), value)

        if pad_bottom:
            self.log(' ')
                
    def log_variable(self, name, value, pad_top=False, pad_bottom=False):
        self.log((name + ':').ljust(50, ' ') + str(value).rjust(50, ' '), pad_top, pad_bottom)
    
    def log_divider(self, divider, pad_top=False, pad_bottom=False):
        self.log(divider.ljust(100, divider), pad_top, pad_bottom)
    
    def log_progress(self, percentage):
        self.log('▪'.rjust(int(percentage), '▪'))

    def log_new_line(self):
        self.log(' ')

    def error(self, message, pad_top=False, pad_bottom=False): 
        self.set_log_level(self.app.extensions['LOG_LEVEL'])

        if pad_top:
            self.default_logger.error(' ')
            
            for i in range(len(self.loggers)):                
                self.loggers[i](' ')

        self.default_logger.error(message)
        
        for i in range(len(self.loggers)):            
            self.loggers[i](message)

        if pad_bottom:
            self.default_logger.error(' ')
            
            for i in range(len(self.loggers)):
                self.loggers[i](' ')
                
    def warning(self, message, pad_top=False, pad_bottom=False): 
        self.set_log_level(self.app.extensions['LOG_LEVEL'])

        if pad_top:
            self.default_logger.warning(' ')
            
            for i in range(len(self.loggers)):                
                self.loggers[i](' ')

        self.default_logger.warning(message)
        
        for i in range(len(self.loggers)):            
            self.loggers[i](message)

        if pad_bottom:
            self.default_logger.warning(' ')
            
            for i in range(len(self.loggers)):
                self.loggers[i](' ')
    
    def log(self, message, pad_top=False, pad_bottom=False): 
        self.set_log_level(self.app.extensions['LOG_LEVEL'])

        if pad_top:
            self.default_logger.info(' ')
            
            for i in range(len(self.loggers)):                
                self.loggers[i](' ')

        self.default_logger.info(message)
        
        for i in range(len(self.loggers)):            
            self.loggers[i](message)

        if pad_bottom:
            self.default_logger.info(' ')
            
            for i in range(len(self.loggers)):
                self.loggers[i](' ')
