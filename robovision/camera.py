from threading import Thread, Event
import cv2
from time import time, sleep
import numpy as np
import configman

FONT = cv2.FONT_HERSHEY_SIMPLEX
FONT_COLOR = (255, 255, 255)


class CameraMaster:
    """docstring for CameraMaster"""
    VIDEO_MODE = 0
    DEBUG_MODE = 1
    COMBO_MODE = 2

    def __init__(self):
        self.slaves = {}
        self.spawn_slaves()
        configman.load_camera_config(self.slaves)

    @property
    def slave_count(self):
        return len(self.alive_slaves)

    @property
    def alive_slaves(self):
        return dict((k, v) for k, v in self.slaves.items() if v.running)

    def spawn_slaves(self):
        # loads camera, bad indices are skipped
        for index in range(10):
            camera_id = index
            self.slaves[camera_id] = FrameGrabber(key=index)

    def get_slave_photo(self, camera_id, mode=0, TILE_SIZE=(320, 240)):
        camera = self.alive_slaves.get(camera_id)
        frame = camera.frame
        if mode == CameraMaster.VIDEO_MODE:
            pass
        elif mode == CameraMaster.DEBUG_MODE:
            frame = cv2.bitwise_and(frame, frame, mask=camera.debug_frame)
        elif mode == CameraMaster.COMBO_MODE:
            cutout = cv2.bitwise_and(frame, frame, mask=camera.debug_frame)
            frame = np.vstack([frame, cutout])
        stack_height = 2 if mode == CameraMaster.COMBO_MODE else 1
        tile_size = (TILE_SIZE[0], TILE_SIZE[1] * stack_height)
        frame = cv2.resize(frame, tile_size)
        cv2.putText(frame, "%.01f fps cam%s" % (camera.fps, camera_id), (10, 50), FONT, 1, FONT_COLOR, 1)
        center = int(camera.center[0] * TILE_SIZE[0]), int(camera.center[1] * TILE_SIZE[1])
        cv2.putText(frame, "{:.3f}".format(camera.radius), center, FONT, 1, FONT_COLOR, 1)
        cv2.circle(frame, center, int(camera.radius * TILE_SIZE[0]), (0, 0, 255), 5)
        return frame

    def get_group_photo(self, mode=0, TILE_SIZE=(320, 240)):
        frames = list(self.get_slave_photo(c_key, mode=mode, TILE_SIZE=TILE_SIZE) for c_key in self.alive_slaves.keys())
        if len(frames) == 1:
            return frames[0]
        elif len(frames) % 2:
            stack_height = 2 if mode == CameraMaster.COMBO_MODE else 1
            padding = np.zeros((TILE_SIZE[1] * stack_height, TILE_SIZE[0], 3))
            frames.append(padding)
        v_stacks = (np.vstack([frames[i], frames[i + 1]]) for i in range(0, self.slave_count, 2))
        stack = np.hstack(v_stacks)
        return stack

    def get_slaves_list(self):
        return list(self.alive_slaves.items())

    def set_slave_properties(self, camera_id, channel, LOWER, UPPER):
        camera = self.slaves.get(camera_id)
        camera.set_channel(channel, LOWER, UPPER)
        configman.save_camera_config(self.slaves.values())


class FrameGrabber(Thread):
    def __init__(self, width=640, height=480, key=None):
        Thread.__init__(self)
        self.daemon = True
        self.running = False
        self.camera = None

        self.key = key
        self.width, self.height = width, height
        self.BALL_LOWER = (0, 140, 140)
        self.BALL_UPPER = (10, 255, 255)

        self.timestamp = time()
        self.frames = 0
        self.fps = 0

        self.scan_times = [0] * 40

        self.c_ms = 0
        self.center = (-1, -1)
        self.radius = -1
        self.frame = None
        self.debug_frame = None

        self.start()

    def connect_camera(self):
        temp_camera = cv2.VideoCapture(self.key)
        _, _ = temp_camera.read()
        sleep(0.08)
        success, _ = temp_camera.read()
        print('cam{} running:{}'.format(self.key, success))
        if not success: return

        self.camera = temp_camera
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.camera.set(cv2.CAP_PROP_FPS, 60)
        self.running = True

    def set_channel(self, channel, LOWER, UPPER):
        index = ['H', 'S', 'V'].index(channel)
        L, U = list(self.BALL_LOWER), list(self.BALL_UPPER)
        L[index], U[index] = LOWER, UPPER
        self.BALL_LOWER = tuple(L)
        self.BALL_UPPER = tuple(U)

    def run(self):
        self.connect_camera()
        while self.running:
            self.process_frame()
            self.tick_fps()

    def tick_fps(self):
        self.frames += 1
        timestamp_begin = time()
        if not self.frames % 60:
            self.fps = 60 / (timestamp_begin - self.timestamp)
            self.timestamp = timestamp_begin
            print(
                'rate {}: cap={:.4f} process={:.4f} fps={:.1f} '.format(self.key, self.c_ms, sum(self.scan_times) / 40,
                                                                        self.fps))

    def capture_frame(self):
        success, frame = self.camera.read()
        start = time()
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        self.c_ms = time() - start
        return hsv

    def process_frame(self):
        frame = self.capture_frame()
        start = time()
        frame = cv2.blur(frame, (4, 4))
        mask = cv2.inRange(frame, self.BALL_LOWER, self.BALL_UPPER)
        mask = cv2.dilate(mask, None, iterations=2)
        im2, cnts, hierarchy = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if cnts:
            c = max(cnts, key=cv2.contourArea)
            center, radius = cv2.minEnclosingCircle(c)
            self.center = center[0] / self.width, center[1] / self.height
            self.radius = radius / self.width

        self.frame = frame
        self.debug_frame = mask
        self.scan_times[self.frames % 40] = time() - start
