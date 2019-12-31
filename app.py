#!/usr/bin/env python
# coding: utf-8
from flask import Flask, render_template, request, Response
from logging.config import dictConfig
from flask_bootstrap import Bootstrap
import logging
import threading
import time
import requests
import urllib
import socket
import conf

dictConfig({
    'version': 1,
    'formatters': {
        'default': {'format': '%(asctime)s - %(message)s </br>'}
    },
    # 设置处理器
    'handlers': {
        'fileHandler': {
            'class': 'logging.FileHandler',
            'filename': 'sensor.log',
            'formatter': 'default',
            'level': 'WARNING'
                }},
    # 设置root日志对象配置
    'root': {
        'level': 'WARNING',
        'handlers': ['fileHandler']
    },
    # 设置其他日志对象配置
    'loggers': {
        'test':
            {'level': 'WARNING',
             'handlers': ['fileHandler'],
             'propagate': 0}
    }
})

sensor_data = {'current': 100.0, 'turn_on': 19.0, 'turn_off': 21.0, 'humidity': 100.0}

HEADERS = {'Content-Type': 'application/x-www-form-urlencoded'}
URL = 'http://mk.shushimall.com:8018/cominterface/index.aspx'


def get_device_status():
    content = ''
    try:
        form_data = {'cid': conf.GET_DEVICE_STATUS_CID, 'key': conf.GET_DEVICE_STATUS_KEY}
        data = urllib.urlencode(form_data)
        res = requests.post(url=URL, headers=HEADERS, data=data)
        content = res.content
        print content
        is_working = res.json().get('JData')[0].get('devtype')[0].get('isworking')
        print is_working
        if '1' == is_working:
            return 'ON'
        elif '0' == is_working:
            return 'OFF'
    except:
        logging.error('get status error, content [%s]' % content)
    return 'ERROR'


def set_device_status(current_status, target_status, current_temperature):
    logging.warning('update device status [%s] to [%s], current temperature [%s]' %
                    (current_status, target_status, current_temperature))
    content = ''
    try:
        form_data = {'mid': conf.UPDATE_DEVICE_STATUS_MID, 'key': conf.UPDATE_DEVICE_STATUS_KEY, 'dev_type': '8',
                     'commandvalue': target_status, 'commandcode': 'set_onoff'}
        data = urllib.urlencode(form_data)
        res = requests.post(url=URL, headers=HEADERS, data=data)
        content = res.content
        print content
    except:
        logging.error('set status error, content [%s]' % content)
    return target_status


def get_current_data(data):
    data_list = data.split('\r\n')
    temp_data = data_list[len(data_list) - 2]
    if temp_data:
        print(temp_data)
        print('\n\n')
        values = temp_data.split('"')
        print('current temperature is [%s]' % values[23])
        print('humidity is [%s]' % values[11])
        sensor_data['humidity'] = float(values[11])
        sensor_data['current'] = values[23]
        return float(values[23])
    return 100


class FlaskApp(Flask):
    def __init__(self, *args, **kwargs):
        super(FlaskApp, self).__init__(*args, **kwargs)
        self._activate_background_job()

    @staticmethod
    def _activate_background_job():
        def sensor_monitor():
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(('0.0.0.0', 10086))
            s.listen(5)
            sock, addr = s.accept()
            count = 0
            while True:
                data = sock.recv(10240)
                if count == 0:
                    count = 150
                    current_temperature = get_current_data(data)
                    current_status = get_device_status()
                    sensor_data['current'] = current_temperature
                    logging.warn('cur_temp is [%s] cur_status is [%s]' % (current_temperature, current_status))
                    print('cur_temp is [%s], turn on at [%s], turn off at [%s], cur_status is [%s]' %
                          (current_temperature, sensor_data.get('turn_on'), sensor_data.get('turn_off'), current_status))
                    if current_temperature <= sensor_data.get('turn_on') and current_status == 'OFF':
                        set_device_status(current_status, '1', current_temperature)
                    if current_temperature >= sensor_data.get('turn_off') and current_status == 'ON':
                        set_device_status(current_status, '0', current_temperature)
                time.sleep(60)
                count = count - 1
        t1 = threading.Thread(target=sensor_monitor)
        # t1.start()


app = FlaskApp(__name__)
bootstrap = Bootstrap(app)


@app.route('/', methods=['GET', 'POST'])
def index():
    turn_on = request.form.get('turn_on')
    turn_off = request.form.get('turn_off')
    if turn_on is not None and turn_off is not None:
        sensor_data['turn_on'] = float(turn_on)
        sensor_data['turn_off'] = float(turn_off)
        logging.warning('update sensor data: turn on [%s] turn off [%s]' % (turn_on, turn_off))
    return render_template('index.html', temperature=sensor_data.get('current'), humidity=sensor_data.get('humidity'),
                           turnOn=sensor_data.get('turn_on'), turnOff=sensor_data.get('turn_off'))


@app.route('/log')
def query_log():
    log_file = open('sensor.log', mode='r')
    content = log_file.read()
    log_file.close()
    return Response(content, mimetype='text/html')\



@app.route('/test')
def test():
    return render_template('test.html')


if __name__ == '__main__':
    app.config['BOOTSTRAP_SERVE_LOCAL'] = True
    app.run(host='0.0.0.0')
