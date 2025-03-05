"""
Simplified Vertex class for Streamlit UI
This version doesn't depend on PySide2
"""

class Vertex:
    def __init__(self, x=None, y=None):
        self.x = x
        self.y = y
        self.type = None
        self.last = None
        self.next = None
        self.breaks = False
        self.is_first = False
        self.is_last = False
        self.protected_low = None
        self.protected_high = None
        self.is_choch = False
        self.is_cos = False

    def __repr__(self):
        out = []
        out.append(self.type)
        out.append(self.x)
        out.append(self.y)
        if self.is_cos:
            out.append("COS")
        if self.is_choch:
            out.append("CHOCH")
        return str(out)
    
    def set_last(self, vertex):
        """Set the previous vertex in the chain"""
        self.last = vertex
    
    def set_next(self, vertex):
        """Set the next vertex in the chain"""
        self.next = vertex
    
    def is_higher_high(self):
        """Check if this vertex is a higher high compared to the last high"""
        if self.type != "HH" or self.last is None:
            return False
        
        # Find the last HH
        last_hh = self.last
        while last_hh is not None and last_hh.type != "HH":
            last_hh = last_hh.last
        
        if last_hh is None:
            return True
        
        return self.y > last_hh.y
    
    def is_lower_low(self):
        """Check if this vertex is a lower low compared to the last low"""
        if self.type != "LL" or self.last is None:
            return False
        
        # Find the last LL
        last_ll = self.last
        while last_ll is not None and last_ll.type != "LL":
            last_ll = last_ll.last
        
        if last_ll is None:
            return True
        
        return self.y < last_ll.y 