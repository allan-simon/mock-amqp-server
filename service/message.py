class Message:
    def __init__(self, headers):
        self.headers = headers
        self.content = b''

    def add_content(self, content):
        self.content += content

    def is_complete(self):
        return self.headers.body_size == len(self.content)
