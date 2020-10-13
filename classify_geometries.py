import os
import csv
import sys

from sklearn.covariance import EllipticEnvelope
from collections import defaultdict

import numpy as np
import matplotlib.cm as cm
import matplotlib.colors as clrs
import matplotlib.pyplot as plt

cmap = clrs.LinearSegmentedColormap("blaaa", { 'red': [ (0.0, 0.0, 0.0), (0.3, 0.0, 0.0), (0.7, 1.0, 1.0), (1.0, 1.0, 1.0) ], 'green': [ (0.0, 0.0, 0.0), (0.3, 0.0, 0.0), (0.7, 1.0, 1.0), (1.0, 1.0, 1.0) ], 'blue': [ (0.0, 0.0, 0.0), (0.3, 0.0, 0.0), (0.7, 1.0, 1.0), (1.0, 1.0, 1.0) ]})                    
cmap2 = clrs.LinearSegmentedColormap("blaaa", { 'red': [ (0.0, 1.0, 1.0), (1.0, 0.0, 0.0) ], 'green': [ (0.0, 0.0, 0.0), (1.0, 1.0, 1.0) ], 'blue': [ (0.0, 0.0, 0.0), (1.0, 0.0, 0.0) ]})

by_entity = defaultdict(list)
by_entity_g = defaultdict(list)

defaults = {
    'distance_from_bottom': 1e9,
    'distance_from_top': 1e9,
    'shape_area': 0,
    'shape_gyradius': 0,
    'shape_volume': 0
}

hd = None

with open(sys.argv[1], newline='') as f:
    r = csv.reader(f)
    for i, l in enumerate(r):
        if i == 0:
            columns = l
        else:
            di = dict(zip(columns, l))
            li = []
            _hd = []
            for k,v in sorted(di.items()):
                if k.endswith('instance_name') or k.startswith('_segment') or k.startswith('distance'): continue
                try: 
                    li.append(float(v))
                    _hd.append(k.replace("_", " ").title())
                except: pass
            
            if len(li) == 3:
                if hd is None: hd = _hd
                by_entity[di['_segment_0']].append(li)
                by_entity_g[di['_segment_0']].append(di['_segment_1'])
            
for k, vs in by_entity.items():
    # if k != 'IfcWallStandardCase': continue
    arr = np.array(vs)
    fig = plt.figure()

    ax = fig.add_subplot(111)
    arr[:,0] /= arr[:,2]
    arr[:,1] /= arr[:,2]
    a = arr[:,0:2]
    ee = EllipticEnvelope()
    try: ee.fit(a)
    except: continue
    
    dsts = ee.decision_function(a).ravel()
    m1, m2 = min(dsts), max(dsts)
    
    maaa = ee.mahalanobis(a)
    
    min_x, max_x = min(arr[:,0]), max(arr[:,0])
    min_y, max_y = min(arr[:,1]), max(arr[:,1])
    
    min_x -= 10
    max_x += 10
    min_y -= 10
    max_y += 10
    
    xx, yy = np.meshgrid(np.linspace(min_x, max_x, 500), np.linspace(min_y, max_y, 500))
    Z = ee.decision_function(np.c_[xx.ravel(), yy.ravel()])
    Z = Z.reshape(xx.shape)
    
    ax.contour(xx, yy, Z, linestyles=["dashed"], cmap=cmap, levels=np.linspace(Z.min(), Z.max(), 10))
    
    for x,y,c in zip(arr[:,0], arr[:,1], dsts):
        c = (c-m1)/(m2-m1)
        ax.scatter(x,y,color=cmap2(c))
    
    ax.set_xlabel("%s / %s" % (hd[0], hd[2]))
    ax.set_ylabel("%s / %s" % (hd[1], hd[2]))
    ax.axis('tight')
    ax.set_xlim((min_x, max_x))
    ax.set_ylim((min_y, max_y))

    for madist, dist, guid in sorted(zip(maaa, dsts, by_entity_g[k])):
        print(guid, madist)

    plt.savefig('output/%s-anomalies.pdf'%k)
                