import datetime

from ifcopenshell import guid

class query_unique:
    pass
    
class query_count:
    pass
    
class group_by:
    def __init__(self, k): 
        self.k = k
        
class split:
    def __init__(self, chr):
        self.chr = chr
        
class regex:
    def __init__(self, pattern):
        self.rx = re.compile(pattern)
    def matches(self, value):
        return self.rx.search(value) is not None
    def evaluate(self, value):
        return self.rx.search(value).group(1)
    
class latlon:
    @staticmethod
    def to_float(compound):
        magnitudes = [1., 60., 3600., 3600.e6][:len(compound)]
        return sum(a/b for a,b in zip(compound, magnitudes))
    def __init__(self, *args):
        self.name, self.compound = args
    def __repr__(self):
        return "%s<%r>"%(self.name, self.compound)
    def to_rdf(self):
        return latlon.to_float(self.compound)

class xsd_date(str):
    def to_rdf(self): return '"%s"^^xsd:date'%self
        
def minimum(parameters):
    if len(parameters) == 0: return ()
    return min(parameters)        
        
time        = lambda ts: xsd_date(datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S'))
latitude    = lambda v: None if v is None else latlon('Latitude', v)                                
longitude   = lambda v: None if v is None else latlon('Longitude', v)                               
join        = lambda li: " ".join(li) if li else None                                               
unique      = query_unique()                                                                        
count       = query_count()                                                                         
expand_guid = guid.expand                                                              
unit        = lambda x: x                                                                           
regex       = regex                                                                                 
split       = split                                                                                 
mapping     = lambda cls: cls().__getitem__                                                         
group_by    = group_by                                                                              
minimum     = minimum                                                                               
