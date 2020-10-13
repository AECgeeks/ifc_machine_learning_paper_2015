import sys
import math
import operator

from collections import namedtuple

from functools import lru_cache

from OCC.Core import gp
from OCC.Core import Bnd
from OCC.Core import GProp
from OCC.Core import BRepGProp
from OCC.Core import BRepBndLib
from OCC.Core import BRepExtrema

import ifcopenshell.geom

bb = namedtuple('bb', ('min', 'max'))
pt = namedtuple('pt', tuple('xyz'))

@lru_cache(maxsize=None)
def obtain_shape(instance):
    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_PYTHON_OPENCASCADE, True)
    try:
        return ifcopenshell.geom.create_shape(settings, instance).geometry
    except: return None

@lru_cache(maxsize=None)
def obtain_distance_(ab):
    s1, s2 = map(obtain_shape, ab)
    if s1 and s2:
        dist = BRepExtrema.BRepExtrema_DistShapeShape(s1, s2)
        if dist.Perform():
            return dist.Value()
            
def obtain_distance(a, b):
    """
    Distance a - b is equal to b - a so we
    defer this call to a cached function based
    on a frozenset of {a, b}
    """
    
    return obtain_distance_(frozenset({a,b}))

@lru_cache(maxsize=None)
def obtain_boundingbox(instance):
    s = obtain_shape(instance)
    if s:
        bbox = Bnd.Bnd_Box()
        BRepBndLib.brepbndlib_Add(s, bbox)
        bbox = bbox.Get()
        return bb(pt(*bbox[:3]), pt(*bbox[3:]))
    
@lru_cache(maxsize=None)
def obtain_volumeproperties(instance):
    s = obtain_shape(instance)
    if s:
        props = GProp.GProp_GProps()
        BRepGProp.brepgprop_VolumeProperties(s, props)
        return props
        
@lru_cache(maxsize=None)
def obtain_surfaceproperties(instance):
    s = obtain_shape(instance)
    if s:
        props = GProp.GProp_GProps()
        BRepGProp.brepgprop_SurfaceProperties(s, props)
        return props

@lru_cache(maxsize=None)
def obtain_gyradius(instance):
    props = obtain_volumeproperties(instance)
    if props:
        gyradius = props.RadiusOfGyration(gp.gp_Ax1(props.CentreOfMass(), gp.gp_DZ()))
        return gyradius
    
@lru_cache(maxsize=None)
def obtain_volume(instance):
    props = obtain_volumeproperties(instance)
    if props:
        return props.Mass()
    
@lru_cache(maxsize=None)
def obtain_area(instance):
    props = obtain_surfaceproperties(instance)
    if props:
        return props.Mass()

class orientation:
    class top: pass
    class bottom: pass
    
def boundingbox_distance(bb1, bb2, axes='xyz'):
    """
    Computes distance between two bounding boxes
    over any of the axes specified.
    """
    
    # Distances along selected axes
    ds = []
    
    for ax in axes:
        c1 = (getattr(bb1.min, ax) + getattr(bb1.max, ax)) / 2.
        c2 = (getattr(bb2.min, ax) + getattr(bb2.max, ax)) / 2.
        w1 = (getattr(bb1.max, ax) - getattr(bb1.min, ax)) / 2.
        w2 = (getattr(bb2.max, ax) - getattr(bb2.min, ax)) / 2.
        d = abs(c2-c1) - (w1+w2)
        ds.append(d)
    
    # In case of overlap return a negative value
    if max(ds) < -1.e-3:
        # overlap
        return max(ds)
    
    # Norm2 of the distance components
    return math.sqrt(sum(map(lambda x: x*x if x > 0. else 0., ds)))
        
class distance_to(object):
    """
    
    A functor that based on a set of ifc_extract query iterate
    over selected elements and yield distances to elements above
    or below the element within the search radius.
    
    """

    def __init__(self, q, orientation=None, searchradius=None):
        self.prefix = q.prefix
        self.others = list(map(operator.attrgetter('instance'), q.entities.instances))
        self.orientation = orientation
        self.searchradius = searchradius        
        
    def __call__(self, instance):
        def generate_distances():
            for i, other in enumerate(self.others):
                valid = True
                bb1, bb2 = map(obtain_boundingbox, (instance, other))
                
                if self.orientation:
                    valid = bb1 is not None and bb2 is not None and \
                        boundingbox_distance(bb1, bb2, 'xy') < -1.e-3 and ( #0. is ok because of desired overlap
                        (self.orientation == orientation.top    and bb2.max.z > bb1.max.z + 1e-4) or \
                        (self.orientation == orientation.bottom and bb2.min.z < bb1.min.z - 1e-4)
                    )
                    
                if valid and self.searchradius is not None:
                    d = boundingbox_distance(bb1, bb2)
                    valid = d < self.searchradius
                    
                if valid:
                    d = obtain_distance(instance, other)
                    if d is not None:
                        yield d
                        
        return "Distance to", list(generate_distances())

def wrap(f):
    """
    Wrap the geometrical processing functions to emit output
    in accordance with the ifc_extract operators.
    """
    
    def run(g, args):
        try: return g(*args)
        except: pass

    return lambda *args: (f.__name__, run(f, args))
    
shape_area = wrap(obtain_area)
shape_volume = wrap(obtain_volume)
shape_gyradius = wrap(obtain_gyradius)
