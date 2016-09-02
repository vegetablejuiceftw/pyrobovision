import cv2
from flask import Flask, render_template, Response, request
from time import time, sleep

from camera import CameraMaster

cameras = CameraMaster()
print('grabber count', cameras.slave_count)

app = Flask(__name__)

SLEEP_TIME = 0.08


@app.route('/combined/<path:type_str>')
def video_combined(type_str):
    TYPES = ['VIDEO', 'DEBUG', 'COMBO']
    def generator():
        while True:
            last_frame = cameras.get_group_photo(mode=TYPES.index(type_str.upper()))
            ret, jpeg = cv2.imencode('.jpg', last_frame, (cv2.IMWRITE_JPEG_QUALITY, 80))
            yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpeg.tostring() + b'\r\n\r\n'
            sleep(SLEEP_TIME)

    return Response(generator(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/video/<path:camera_id>')
def video(camera_id):
    camera_id = int(camera_id)
    def generator():
        while True:
            last_frame = cameras.get_slave_photo(camera_id)
            ret, jpeg = cv2.imencode('.jpg', last_frame, (cv2.IMWRITE_JPEG_QUALITY, 80))
            yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpeg.tostring() + b'\r\n\r\n'
            sleep(SLEEP_TIME)

    return Response(generator(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/debug/<path:camera_id>')
def debug(camera_id):
    camera_id = int(camera_id)
    def generator():
        while True:
            last_frame = cameras.get_slave_photo(camera_id, mode=CameraMaster.DEBUG_MODE)
            ret, jpeg = cv2.imencode('.jpg', last_frame, (cv2.IMWRITE_JPEG_QUALITY, 80))
            yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpeg.tostring() + b'\r\n\r\n'
            sleep(SLEEP_TIME)

    return Response(generator(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/both/<path:camera_id>')
def both(camera_id):
    camera_id = int(camera_id)
    def generator():
        while True:
            last_frame = cameras.get_slave_photo(camera_id, mode=CameraMaster.COMBO_MODE)
            ret, jpeg = cv2.imencode('.jpg', last_frame, (cv2.IMWRITE_JPEG_QUALITY, 80))
            yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpeg.tostring() + b'\r\n\r\n'
            sleep(SLEEP_TIME)

    return Response(generator(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/')
def index():
    return render_template('main.html', camera_list=cameras.get_slaves_list())


@app.route('/group')
def group():
    return render_template('group.html', camera_list=cameras.get_slaves_list())


# static files for js and css
@app.route('/nouislider.css')
def nouisliderCSS():
    return render_template('nouislider.css')


@app.route('/nouislider.js')
def nouisliderJS():
    return render_template('nouislider.js')


@app.route('/config/camera/<path:camera_id>', methods=['get', 'post'])
def config(camera_id):
    camera_id = int(camera_id)
    channel = request.form.get('channel')
    LOWER = int(request.form.get('LOWER'))
    UPPER = int(request.form.get('UPPER'))
    print('config', channel, LOWER, UPPER)

    cameras.set_slave_properties(camera_id, channel, LOWER, UPPER)
    return 'Mkay, yes, a response, I guess I can do that.'


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, use_reloader=False, threaded=True)
