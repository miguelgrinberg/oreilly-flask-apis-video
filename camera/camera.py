import os
import time
import uuid
from glob import glob
from flask import Flask, url_for, jsonify, send_file

try:
    # This will only work on a Raspberry Pi
    import picamera
except:
    picamera = None

cameras = {}  # available cameras
app = Flask(__name__)


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

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'resource not found'}), 404

@app.errorhandler(405)
def method_not_supported(e):
    return jsonify({'error': 'method not supported'}), 405

@app.errorhandler(500)
def internal_server_error(e):
    return jsonify({'error': 'internal server error'}), 500


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
                'emulated': self.is_emulated()}

    def get_photos_url(self):
        return url_for('get_camera_photos', camid=self.camid, _external=True)

    def get_photos(self):
        return [os.path.basename(f) for f in glob(self.camid + '/*.jpg')]

    def get_photo_path(self, filename):
        path = self.camid + '/' + filename
        if not os.path.exists(path):
            raise InvalidPhoto()
        return path

    def get_new_photo_filename(self):
        return uuid.uuid4().hex + '.jpg'

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
            camera.start_preview()
            time.sleep(2)  # wait for camera to warm up
            camera.capture(self.camid + '/' + filename)
        return filename


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
    os.remove(filename)
    return jsonify({})


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
