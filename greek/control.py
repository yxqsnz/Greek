from typing import Iterable

class Control:
    def __init__(self, iterable: Iterable, position=0):
        self.iterable = iterable
        self.position = position
    
    def __iter__(self):
        iterable_length = len(self.iterable)

        while self.position < iterable_length:
            yield self.take()
        
        return
    
    def take(self, piece_length=1):
        if self.position >= len(self.iterable):
            piece = ''
        elif piece_length > 1:
            piece = self.iterable[self.position: self.position + piece_length]
        else:
            piece = self.iterable[self.position]
        
        self.position += piece_length

        return piece
    
    def equals(self, iterable: Iterable) -> Iterable:
        iterable_length = len(iterable)

        if (piece := self.take(iterable_length)) == iterable:
            return piece
        
        return self.drop(iterable_length)
    
    def drop(self, piece_length=1):
        self.position -= piece_length
