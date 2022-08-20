from typing import Iterable

class Source:
    def __init__(self, iterable: Iterable, position=0):
        self.iterable = iterable
        self.position = position
    
    def __iter__(self):
        iterable_length = len(self.iterable)

        while self.position < iterable_length:
            yield self.look()
        
        return
    
    def look(self, by=1):
        if by <= 0:
            raise ValueError("by must be greater than zero")
        elif self.position >= len(self.iterable):
            return None
        
        if by > 1:
            part = self.iterable[self.position: self.position + by]
        else:
            part = self.iterable[self.position]
        
        self.position += by

        return part
    
    def unlook(self, by=1):
        self.position -= by

        if self.position < 0:
            self.position = 0
        
        return