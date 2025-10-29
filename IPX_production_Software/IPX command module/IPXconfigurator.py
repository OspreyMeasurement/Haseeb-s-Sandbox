





# create new IPX configurator class?

class IPXConfigurator:
    def __init__(self, port, max_retries: int=3, retry_delay: int=2):
        self.port = port
        self.max_retries = max_retries
        self.retry_delay = retry_delay