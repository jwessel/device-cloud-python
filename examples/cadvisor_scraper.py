import requests
import json

cadvisor_hostname = 'oci-cadvisor.cube.lan'
cadvisor_port = '8080'
cadvisor_base = 'http://%s:%s/api/v1.2' % (cadvisor_hostname, cadvisor_port)

# For machine metrics
id_num_cores = 'num_cores'
id_cpu_frequency = 'cpu_frequency_khz'
id_memory_capacity = 'memory_capacity'
id_filesystems = 'filesystems'

# For containers metrics
id_subcontainers = 'subcontainers'
id_stats = 'stats'

id_appcontainer = '/cube-gw'

# Get Machine metrics
r = requests.get('%s/machine' % cadvisor_base)

items = r.json()

if id_num_cores in items:
    print items[id_num_cores]

if id_cpu_frequency in items:
    print items[id_cpu_frequency]

if id_memory_capacity in items:
    print items[id_memory_capacity]

if id_filesystems in items:
    for key in items[id_filesystems]:
        print json.dumps(key, sort_keys=True, indent=4, separators=(',', ': '))

# Get Container metrics
r = requests.get('%s/containers' % cadvisor_base)

items = r.json()
if id_subcontainers in items:
    print items[id_subcontainers]
    for element in items[id_subcontainers]:
        if 'name' in element:
            print("%s" % element['name'])
    print

if id_stats in items:
    for element in items[id_stats]:
        if 'timestamp' in element:
            print("%s" % element['timestamp'])
        if 'cpu' in element and 'usage' in element['cpu']:
            print("%s" % element['cpu']['usage']['total'])
        # print json.dumps(element, sort_keys=True, indent=4, separators=(',', ': '))

# Get Subcontainers metrics
r = requests.get('%s/subcontainers' % cadvisor_base)

items = r.json()
for element in items:
    if 'name' in element:
        # print("%s" % element['name'])
        if element['name'] == id_appcontainer:
            print("My container %s" % id_appcontainer)
            print json.dumps(element, sort_keys=True, indent=4, separators=(',', ': '))

