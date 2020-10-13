import operator

by_entity = lambda instance: instance.is_a()

def by_attribute(attr):
    f = operator.attrgetter(attr)
    if False and attr == 'GlobalId':
        return lambda i: ifcopenshell.guid.expand(f(i))
    else: return f