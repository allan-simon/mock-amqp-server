class Message():
    def __init__(self, header):
        self.header = header
        self.content = b''

    def add_content(self, content):
        self.content += content

    def is_complete(self):
        return self.header.body_size == len(self.content)
