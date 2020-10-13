import sys
from csv import writer as csv_writer

from collections import defaultdict

class csv_formatter:
    def __lshift__(self, li):
        fields = defaultdict(dict)
        def walk():
            for item in li:
                if len(item.segmentations) or True:
                    for keys, values in item.segmented(True):
                        if keys is not None:
                            key = tuple(keys)
                            for i,k in enumerate(keys):
                                fields[keys]["_segment_%d" % i] = k
                        for p, vs in values.li:
                            if isinstance(vs, (tuple, list)):
                                for v in vs:
                                    fields[keys][p.split(':')[-1]] = v[1]
                                    try:
                                        fields[keys][p.split(':')[-1] + "_instance_name"] = v[0][1][1].id()
                                    except: pass
                            else:
                                fields[keys][p.split(':')[-1]] = vs
        walk()
        dict_rows = sorted(fields.keys())
        dict_columns = sorted(set(sum(map(lambda d: list(d.keys()), fields.values()), [])))
        rows = [dict_columns]
        for k in dict_rows:
            rows.append([fields[k].get(c) for c in dict_columns])
        
        csvwriter = csv_writer(sys.stdout)
        csvwriter.writerows(rows)
        
csv = csv_formatter()