import configparser
import os

dir_path = os.path.dirname(os.path.realpath(__file__))
path = dir_path + '/configs/cameras.conf'


# save_camera_config is a method that should write its config into the file
def save_camera_config(cameras):
    config = configparser.ConfigParser()
    config.read(path)
    for camera in cameras:
        key = str(camera.key)
        config[key] = {}
        config[key]['LowerHue'] = str(camera.BALL_LOWER[0])
        config[key]['LowerSaturation'] = str(camera.BALL_LOWER[1])
        config[key]['LowerValue'] = str(camera.BALL_LOWER[2])
        config[key]['HigherHue'] = str(camera.BALL_UPPER[0])
        config[key]['HigherSaturation'] = str(camera.BALL_UPPER[1])
        config[key]['HigherValue'] = str(camera.BALL_UPPER[2])

    with open(path, 'w') as configfile:
        config.write(configfile)


def load_camera_config(camera_map):
    config = configparser.ConfigParser()
    config.read(path)
    for key in config.keys():
        camera = camera_map.get(key)
        if camera:
            camera.set_channel('H', int(config[key]['lowerhue']), int(config[key]['higherhue']))
            camera.set_channel('S', int(config[key]['lowersaturation']), int(config[key]['highersaturation']))
            camera.set_channel('V', int(config[key]['lowervalue']), int(config[key]['highervalue']))
