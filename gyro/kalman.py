

class KalmanFilter:
    def __init__(self):
        self.angle = 0.
        self.speed = 0.
        self.gain = 0.

    def _state_update(self, measurement, dt):
        self.state = (measurement - self.state) * self.gain

    def _covariance_update(self):
        self.estimate_variance = (1 - self.gain) * self.estimate_variance

    def kalman_gain(self):
        return self.estimate_variance / (self.estimate_variance + self.measurement_variance)

    def state_update_angle(self, measurement, dt):
        return self.angle + 