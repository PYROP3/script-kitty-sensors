

class AlphaBetaGamma:
    def __init__(self, alpha, beta):
        self.state = 0.
        self.state_prime = 0.
        self.alpha = alpha
        self.beta = beta

    def initialize(self, measurement):
        self.state = measurement

    def _state_update(self, measurement):
        return self.state + self.alpha * (measurement - self.state)

    def _state_derivative_update(self, measurement, dt):
        return self.state_prime + self.beta * (measurement - self.state) / dt