import re
import sys
import ifcopenshell
import operator
import itertools

from .operations import *

class query:
    class instance_list:
        def __init__(self, prefix=None, instances=None):
            self.prefix = prefix or ''
            self.instances = [] if instances is None else list(instances)
        def __add__(self, other):
            return query.instance_list(
                self.prefix if len(self.prefix) > len(other.prefix) else other.prefix,
                self.instances + other.instances
            )
        def __getattr__(self, k):
            li = list(map(lambda e: getattr(e, k), self.instances))
            classes = list(map(type, li))
            if query.instance_list in classes:
                return sum(li, query.instance_list())
            return li
        def __repr__(self):
            return ",\n".join("  - %s"%v.instance for v in self.instances)
        def __len__(self): return len(self.instances)
        def select(self, ty):
            return query.instance_list(
                self.prefix, 
                [i for i in self.instances if i.instance.wrapped_data.is_a(ty)]
            )
            
    class instance:
        def __init__(self, prefix, instance):
            self.prefix = prefix
            self.instance = instance
        def wrap_value(self, v, k):
            wrap = lambda e: query.instance("%s.%s"%(self.prefix,k), e)
            if isinstance(v, ifcopenshell.entity_instance): return wrap(v)
            elif isinstance(v, (tuple, list)) and len(v):
                classes = list(map(type, v))
                if ifcopenshell.entity_instance in classes: 
                    return query.instance_list("%s.%s"%(self.prefix,k), list(map(wrap, v)))
            return v
        def __getattr__(self, k):
            return self.wrap_value(getattr(self.instance, k), k)
            
    class parameter_list:
        def __init__(self, li=None):
            self.li = []
            for nm, val in (li or []):
                self.li.append((nm, val))
                
        def __add__(self, other):
            return query.parameter_list(self.li + other.li)
            
        def __or__(self, other):
            result = query.parameter_list()
            for i in range(max(len(self.li), len(other.li))):
                a1,b1, a2,b2 = '', None, '', None
                try: a1, b1 = self.li[i]
                except: pass
                try: a2, b2 = other.li[i]
                except: pass
                result.li.append((a1 if len(a1) > len(a2) else a2, b1 if b1 else b2))
            return result
            
        def __and__(self, other):
            e = lambda s: s if s else ""
            result = query.parameter_list()
            for i in range(max(len(self.li), len(other.li))):
                a1,b1, a2,b2 = '', None, '', None
                try: a1, b1 = self.li[i]
                except: pass
                try: a2, b2 = other.li[i]
                except: pass
                result.li.append(('(%s + %s)'%(a1, a2), e(b1) + e(b2)))
            return result
            
        def bind(self, name):
            return query.parameter_list([(name, v) for old_name, v in self.li])
            
        @staticmethod
        def count(query):
            return query.parameter_list([("%s.Count"%(query.prefix), len(query.entities))])
            
        def unique(self):
            value_set = set()
            result = query.parameter_list()
            for k, v in self.li:
                if v not in value_set:
                    value_set.add(v)
                    result.li.append((k, v))
            return result
            
        def apply(self, fn):
            return query.parameter_list([(k, fn(v)) for k, v in self.li])
            
        def filter(self, regex):
            return query.parameter_list([(k, regex.evaluate(v)) for k, v in self.li if regex.matches(v)])
            
        def __repr__(self):
            return ",\n".join("  - %s: %s"%(k,v) for k,v in self.li)

    
    def __init__(self, instances, prefix=None):
        self.prefix = prefix or ""
        self.segmentations = []
        if instances == [[]]: instances = []
        is_instance_list = isinstance(instances, query.instance_list)
        if not is_instance_list:
            classes = list(map(type, instances))
            if query.instance in classes or len(instances) == 0:
                is_instance_list = True
                instances = query.instance_list(self.prefix, instances)                
        if is_instance_list:
            self.entities = instances
            self.params = None
        else:
            self.entities = None
            self.params = query.parameter_list([(self.prefix, v) for v in instances])
            
    def select(self, ty):
        return query(self.entities.select(ty), self.prefix)
        
    def __getattr__(self, k):
        if self.params: 
            return query([], "%s.%s"%(self.prefix,k))
        q = query(getattr(self.entities, k), "%s.%s"%(self.prefix,k))
        q.segmentations = list(self.segmentations)
        return q
        
    def __sub__(self, other):
        assert type(other) == type(self)
        q = query([], self.prefix)
        q.segmentations = list(self.segmentations)
        other_ids = set(map(lambda i: i.instance.id(), other.entities.instances))
        q.entities = query.instance_list(instances=list(filter(lambda i: i.instance.id() not in other_ids, self.entities.instances)))
        return q
        
    def __or__(self, other):
        if self.entities and other.entities:
            q = query(self.entities + other.entities, self.prefix)
        elif self.params and other.params:
            q = query([], self.prefix)
            q.params = self.params | other.params
        else: raise AttributeError()
        return q
        
    def __rshift__(self, other):
        q = query([], self.prefix)
        q.segmentations = list(self.segmentations)
        if isinstance(other, str) or (isinstance(other, (tuple, list)) and set(map(type,other)) == {str}): 
            # `other` is a string that describes the new name bound to the parameters in this query object
            q.params = (self.params or query.parameter_list()).bind(other)
        elif isinstance(other, group_by):
            q.params = (query.parameter_list() + self.params) if self.params is not None else None
            q.entities = (query.instance_list() + self.entities) if self.entities is not None else None
            q.segmentations.append(list(map(other.k, q.entities.instances)))
        elif isinstance(other, query_count):
            # `other` is the formatters.count object, which means we add a new result parameter and initialize it to
            # the amount of instances
            q.params = query.parameter_list.count(self)
        elif isinstance(other, query_unique):
            # `other` is the formatters.unique object, which means filter out non-unique parameters
            q.params = (self.params or query.parameter_list()).unique()
        elif hasattr(other, '__call__'):
            # some lambda function, probably also an attribute of the formatters collection class
            if self.params:
                q.params = self.params.apply(other)
            else:
                li = []
                for i, inst in enumerate(self.entities.instances):
                    sys.stderr.write("\r%d                  " % i)
                    li.append(other(inst.instance))
                q.params = query.parameter_list(li)
        elif isinstance(other, regex):
            q.params = (self.params or query.parameter_list()).filter(other)
        elif isinstance(other, split):
            orig = (self.params or query.parameter_list())
            def generate():
                for k,v in orig.li:
                    for s in v.split(split.chr):
                        yield k,s
            q.params = query.parameter_list(list(generate()))
        else: raise
        return q
        
    def __add__(self, other):
        if isinstance(other, self.__class__):
            q = query([], self.prefix)
            q.params = (self.params or query.parameter_list()) & (other.params or query.parameter_list())
            return q
        else:
            return self >> (lambda s: (s or '') + other)
            
    def filter(self, **kwargs):
        pattern_class = re.compile("").__class__
        def matches(entity):
            for k, v in kwargs.items():
                val = getattr(entity, k)
                if isinstance(v, pattern_class):
                    if not val or v.match(val) is None: return False
                else:
                    if val != v: return False
            return True
        q = query([i for i in self.entities.instances if matches(i)], self.prefix)
        return q
        
    def segmented(self, params=False):
        keys = list(zip(*self.segmentations))
        get0, get1 = map(operator.itemgetter, range(2))
        orig = self.params.li if params else self.entities.instances
        if len(keys) != len(orig):
            keys = [(i,) for i in range(len(orig))]
        values = sorted(zip(keys, orig), key=get0)
        if params:
            def wrap(li):
                return query.parameter_list(li=list(map(get1, li)))
        else:
            def wrap(li):
                return query.instance_list(instances=list(map(get1, li)))
        return [(k, wrap(v)) for k,v in itertools.groupby(values, get0)]

    def __repr__(self):
        if self.segmentations:
            if self.entities:
                s = "<Segmented unbound query '%s'" % self.prefix
                for segmentations, instances in self.segmented():
                    s += "\n  " + ", ".join(map(repr, segmentations)) + " Entities: \n"
                    s += repr(instances)
                s += ">"
                return s
            else:
                s = "<Segmented bound query '%s'" % self.prefix
                for segmentations, params in self.segmented(True):
                    s += "\n  " + ", ".join(map(repr, segmentations)) + " Parameters: \n"
                    s += repr(params)
                s += ">"
                return s
        else:
            if self.entities:
                return "<Unbound query '%s'\n  Entities:\n%s\n>"%(self.prefix, self.entities)
            else:
                return "<Bound query '%s'\n  Parameters:\n%s\n>"%(self.prefix, self.params)
            
            
class file:            
    class query_wrapper:
        def __init__(self, *args):
            self.prefix, self.instance = args
        def __getattr__(self, k):
            return query.instance(self.prefix, getattr(self.instance, k))

    def __init__(self, ifcfile):
        self.file = ifcfile

    def __getattr__(self, attr):
        if attr == 'header':
            return query([query.instance('<file header>', file.query_wrapper('<file header>', self.file.header))], '<file header>')
        else:
            try: by_type = self.file.by_type(attr)
            except: raise AttributeError("file object does not have an attribute '%s'"%attr)
            instances = list(map(lambda e: query.instance(attr, e), by_type))
            return query(instances, attr)

def open(fn): return file(ifcopenshell.open(fn))
