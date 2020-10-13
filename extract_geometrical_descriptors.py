import sys

import ifc_extract
import ifc_extract.output
from ifc_extract import operations as op
from ifc_extract.groupings import *

import geom_query

file = ifc_extract.open(sys.argv[1])

print("Extracting data, please be patient...", file=sys.stderr)

products = file.IfcWall >> op.group_by(by_entity) >> op.group_by(by_attribute("GlobalId"))

ifc_extract.output.csv << [
    
    products >>
        geom_query.distance_to(file.IfcProduct - file.IfcSpace - file.IfcOpeningElement, orientation=geom_query.orientation.top, searchradius=0.5) >> 
        op.minimum >>
        "ifc_ml:distance_from_top",
    
    products >>
        geom_query.distance_to(file.IfcProduct - file.IfcSpace - file.IfcOpeningElement, orientation=geom_query.orientation.bottom, searchradius=0.5) >> 
        op.minimum >>
        "ifc_ml:distance_from_bottom",
        
    products >> geom_query.shape_area >> "ifc_ml:shape_area",
    
    products >> geom_query.shape_volume >> "ifc_ml:shape_volume",
    
    products >> geom_query.shape_gyradius >> "ifc_ml:shape_gyradius"   

]
