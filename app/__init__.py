import os
import psutil
import importlib
import serial
import time
import json
import sys
import atexit
import logging

from flask import Flask, current_app, send_file, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO
from flask_apscheduler import APScheduler

app = Flask(__name__, static_folder='../dist/static')

from .config import Config

from .api import api_bp
from .client import client_bp

from app.core.command import run_command
from app.core.log import Logger

CORS(app)

app.register_blueprint(api_bp)

app.extensions['IRRIGATION_CONNECTION'] = getattr(importlib.import_module('app.irrigation.module'), 'IrrigationControllerConnectionProvider')()
app.extensions['LOG_LEVEL'] = 'info'

app.config['SECRET_KEY'] = 'vnkdjnfjknfl1232#'

socket = SocketIO(app, cors_allowed_origins="*")
    
scheduler = APScheduler()
scheduler.init_app(app)
#scheduler.add_job('sentinel', func=lambda: run_command(app, Logger('Sentinel', app), 'runSentinel', []), trigger="interval", seconds=37)
#scheduler.add_job('irrigation', func=lambda: run_command(app, Logger('Irrigation', app), 'runIrrigationProgramme'), trigger="interval", seconds=11)
scheduler.start()

atexit.register(lambda: scheduler.shutdown())

if __name__ == '__main__':
    socket.run(app, debug=True)

@socket.on('command')
def handle_event(command, methods=['GET', 'POST']):
    logger = Logger('Terminal', app, [lambda message: socket.emit('log', message)])
    arguments = command['input'].replace(command['type'], '').strip().split()
    result = run_command(app, logger, command['type'], [ arguments[0] if len(arguments) > 0 else None ])
    socket.emit('log', result['result'])
    socket.emit('result', result['success'])
    
@app.route('/run', methods = ['GET','POST'])
def run():
    arguments = request.args.getlist('arguments')
    
    if request.method == 'POST':
        arguments = [request.get_json(silent=True)]

    logger = Logger('CommandRunner', app)
    result = run_command(app, logger, request.args.get('command'), arguments)
    return jsonify(result)

@app.route('/')
def index_client():
    dist_dir = current_app.config['DIST_DIR']
    entry = os.path.join(dist_dir, 'index.html')
    return send_file(entry)  
    