import os
import time
import uuid
import functools
from threading import Thread
from glob import glob
from flask import Flask, url_for, jsonify, send_file, make_response, \
    copy_current_request_context, Response, request

try:
    # This will only work on a Raspberry Pi
    import picamera
except:
    picamera = None

cameras = {}  # available cameras
background_tasks = {}
app = Flask(__name__)
app.config['AUTO_DELETE_BG_TASKS'] = False


# custom exceptions
class InvalidCamera(ValueError):
    pass

class InvalidPhoto(ValueError):
    pass

# custom error handlers
@app.errorhandler(InvalidCamera)
def invalid_camera(e):
    return jsonify({'error': 'camera not found'}), 404

@app.errorhandler(InvalidPhoto)
def invalid_photo(e):
    return jsonify({'error': 'photo not found'}), 404

@app.errorhandler(400)
def bad_request(e=None):
    return jsonify({'error': 'bad request'}), 400

@app.errorhandler(404)
def not_found(e=None):
    return jsonify({'error': 'resource not found'}), 404

@app.errorhandler(405)
def method_not_supported(e):
    return jsonify({'error': 'method not supported'}), 405

@app.errorhandler(500)
def internal_server_error(e=None):
    return jsonify({'error': 'internal server error'}), 500

if picamera:
    @app.errorhandler(picamera.PiCameraRuntimeError)
    def camera_is_in_use(e):
        return jsonify({'error': 'service unavailable'}), 503


def get_camera_from_id(camid):
    """Return the camera object for the given camera ID."""
    camera = cameras.get(camid)
    if camera is None:
        raise InvalidCamera()
    return camera


class BaseCamera(object):
    """Base camera handler class."""
    def __init__(self):
        self.camid = None  # to be defined by subclasses

    def get_url(self):
        return url_for('get_camera', camid=self.camid, _external=True)

    def export_data(self):
        return {'self_url': self.get_url(),
                'photos_url': self.get_photos_url(),
                'timelapses_url': self.get_timelapses_url(),
                'emulated': self.is_emulated()}

    def get_photos_url(self):
        return url_for('capture_photo', camid=self.camid, _external=True)

    def get_timelapses_url(self):
        return url_for('capture_timelapse', camid=self.camid, _external=True)

    def get_photos(self):
        return [os.path.basename(f) for f in glob(self.camid + '/*.jpg')]

    def get_photo_path(self, filename):
        path = self.camid + '/' + filename
        if not os.path.exists(path):
            raise InvalidPhoto()
        return path

    def get_new_photo_filename(self, suffix=''):
        return uuid.uuid4().hex + suffix + '.jpg'


class PiCamera(BaseCamera):
    """Raspberry Pi camera module handler class."""
    def __init__(self):
        super(PiCamera, self).__init__()
        self.camid = 'pi'

    def is_emulated(self):
        return False

    def capture(self):
        """Capture a picture."""
        filename = self.get_new_photo_filename()
        with picamera.PiCamera() as camera:
            camera.resolution = (1024, 768)
            camera.hflip = True
            camera.vflip = True
            camera.start_preview()
            time.sleep(2)  # wait for camera to warm up
            camera.capture(self.camid + '/' + filename)
        return filename

    def capture_timelapse(self, count, interval):
        """Capture a time lapse."""
        filename = self.get_new_photo_filename('_{0:03d}_{1:03d}')
        with picamera.PiCamera() as camera:
            camera.resolution = (1024, 768)
            camera.hflip = True
            camera.vflip = True
            camera.start_preview()
            time.sleep(2)  # wait for camera to warm up
            for i in range(count):
                camera.capture(self.camid + '/' + filename.format(i, count))
                time.sleep(interval)
        return filename.format(0, count)


class FakeCamera(BaseCamera):
    """Emulated camera handler class."""
    def __init__(self):
        super(FakeCamera, self).__init__()
        self.camid = 'fake'
        self.fake_shot = open('pic.jpg', 'rb').read()

    def is_emulated(self):
        return True

    def capture(self):
        """Capture a (fake) picture. This really copies a stock jpeg."""
        filename = self.get_new_photo_filename()
        open(self.camid + '/' + filename, 'wb').write(self.fake_shot)
        return filename

    def capture_timelapse(self, count, interval):
        """Capture a time lapse."""
        filename = self.get_new_photo_filename('_{0:03d}_{1:03d}')
        for i in range(count):
            open(self.camid + '/' + filename.format(i, count), 'wb').write(
                self.fake_shot)
            time.sleep(interval)
        return filename.format(0, count)


def is_hardware_present():
    """Check if there is a Raspberry Pi camera module available."""
    if picamera is None:
        return False
    try:
        # start the Pi camera and watch for errors
        with picamera.PiCamera() as camera:
            camera.start_preview()
    except:
        return False
    return True

# load the cameras global with the list of available cameras
cameras['fake'] = FakeCamera()
if is_hardware_present():
    cameras['pi'] = PiCamera()


def background(f):
    """Decorator that runs the wrapped function as a background task. It is
    assumed that this function creates a new resource, and takes a long time
    to do so. The response has status code 202 Accepted and includes a Location
    header with the URL of a task resource. Sending a GET request to the task
    will continue to return 202 for as long as the task is running. When the task
    has finished, a status code 303 See Other will be returned, along with a
    Location header that points to the newly created resource. The client then
    needs to send a DELETE request to the task resource to remove it from the
    system."""
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        # The background task needs to be decorated with Flask's
        # copy_current_request_context to have access to context globals.
        @copy_current_request_context
        def task():
            global background_tasks
            try:
                # invoke the wrapped function and record the returned
                # response in the background_tasks dictionary
                background_tasks[id] = make_response(f(*args, **kwargs))
            except:
                # the wrapped function raised an exception, return a 500
                # response
                background_tasks[id] = make_response(internal_server_error())

        # store the background task under a randomly generated identifier
        # and start it
        global background_tasks
        id = uuid.uuid4().hex
        background_tasks[id] = Thread(target=task)
        background_tasks[id].start()

        # return a 202 Accepted response with the location of the task status
        # resource
        return jsonify({}), 202, {'Location': url_for('get_task_status', id=id)}
    return wrapped


@app.route('/cameras/', methods=['GET'])
def get_cameras():
    """Return a list of available cameras."""
    return jsonify({'cameras': [url_for('get_camera', camid=camid,
                                        _external=True)
                                for camid in cameras.keys()]})

@app.route('/cameras/<camid>', methods=['GET'])
def get_camera(camid):
    """Return information about a camera."""
    camera = get_camera_from_id(camid)
    return jsonify(camera.export_data())

@app.route('/cameras/<camid>/photos/', methods=['GET'])
def get_camera_photos(camid):
    """Return the collection of photos of a camera."""
    camera = get_camera_from_id(camid)
    photos = camera.get_photos()
    return jsonify({'photos': [url_for('get_photo', camid=camid,
                                       filename=photo, _external=True)
                               for photo in photos]})

@app.route('/cameras/<camid>/photos/<filename>', methods=['GET'])
def get_photo(camid, filename):
    """Return a photo. Photos are in jpeg format, they can be viewed in
    a web browser."""
    camera = get_camera_from_id(camid)
    path = camera.get_photo_path(filename)
    return send_file(path)

@app.route('/cameras/<camid>/photos/', methods=['POST'])
def capture_photo(camid):
    """Capture a photo."""
    camera = get_camera_from_id(camid)
    filename = camera.capture()
    return jsonify({}), 201, {'Location': url_for('get_photo', camid=camid,
                                                  filename=filename,
                                                  _external=True)}

@app.route('/cameras/<camid>/photos/<filename>', methods=['DELETE'])
def delete_photo(camid, filename):
    """Delete a photo."""
    camera = get_camera_from_id(camid)
    path = camera.get_photo_path(filename)
    os.remove(path)
    return jsonify({})

def stream_timelapse(path):
    """Stream the jpegs in a time lapse as a multipart response."""
    parts = path.split('.')[0].split('_')
    count = int(parts[2])
    filename = parts[0] + '_{0:03d}_{1:03d}.jpg'
    for i in range(count):
        frame = open(filename.format(i, count), 'rb').read()
        yield b'--frame\r\nContent-Type: image/jpeg\r\nContent-Length: ' + \
            str(len(frame)).encode() + b'\r\n\r\n' + frame + b'\r\n'
        time.sleep(0.5)

@app.route('/cameras/<camid>/timelapses/<filename>', methods=['GET'])
def get_timelapse(camid, filename):
    """Return a time lapse sequence. Time lapses are returned as a streamed
    multipart response. Most browsers display the sequence of pictures."""
    camera = get_camera_from_id(camid)
    path = camera.get_photo_path(filename)
    return Response(stream_timelapse(path),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/cameras/<camid>/timelapses/<filename>/html', methods=['GET'])
def get_timelapse_html(camid, filename):
    """Return an HTML wrapper page for the timelapse stream. This is required
    by some browsers (i.e Chrome)."""
    return '<img src="{0}">'.format(url_for('get_timelapse', camid=camid,
                                            filename=filename))

@app.route('/cameras/<camid>/timelapses/', methods=['POST'])
@background
def capture_timelapse(camid):
    """Capture a 30 second time lapse sequence, at a rate of a picture per
    second. Note this is an asynchronous request."""
    count = request.args.get('count', 30, type=int)
    interval = request.args.get('interval', 1, type=float)
    camera = get_camera_from_id(camid)
    filename = camera.capture_timelapse(count, interval)
    return jsonify({}), 201, {'Location': url_for('get_timelapse',
                                                  camid=camid,
                                                  filename=filename,
                                                  _external=True)}

@app.route('/status/<id>', methods=['GET'])
def get_task_status(id):
    """Query the status of an asynchronous task."""
    # obtain the task and validate it
    global background_tasks
    rv = background_tasks.get(id)
    if rv is None:
        return not_found(None)

    # if the task object is a Thread object that means that the task is still
    # running. In this case return the 202 status message again.
    if isinstance(rv, Thread):
        return jsonify({}), 202, {'Location': url_for('get_task_status', id=id)}

    # If the task object is not a Thread then it is assumed to be the response
    # of the finished task, so that is the response that is returned.
    # If the application is configured to auto-delete task status resources once
    # the task is done then the deletion happens now, if not the client is
    # expected to send a delete request.
    if app.config['AUTO_DELETE_BG_TASKS']:
        del background_tasks[id]
    return rv

@app.route('/status/<id>', methods=['DELETE'])
def delete_task_status(id):
    """Delete an asynchronous task resource."""
    # obtain the task and validate it
    global background_tasks
    rv = background_tasks.get(id)
    if rv is None:
        return not_found(None)

    # if the task is still running it cannot be deleted
    if isinstance(rv, Thread):
        return bad_request()

    del background_tasks[id]
    return jsonify({}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
