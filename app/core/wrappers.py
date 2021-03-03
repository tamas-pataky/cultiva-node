import time
import logging
import traceback

from functools import wraps

def retry(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        retExc = None
        for i in range(3):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                retExc = e
                logging.error(traceback.format_exc())
                logging.info('Retrying in ' + str(0.5 * i) + ' seconds')
                time.sleep(0.5 * i)
        raise retExc
    return wrapper