#
# import useful libraries
#
import pprint as pp
import pickle
from neo4j import GraphDatabase
import sys
import argparse
import utilities as ut

#
# command line arguments
#
parser = argparse.ArgumentParser(description='Set up SageMaker training data.')
parser.add_argument('--hostname', type=str, help='Hostname.', required=True)
parser.add_argument('--username', type=str, help='Neo4j username.', required=True)
parser.add_argument('--password', type=str, help='Neo4j password.', required=True)
parser.add_argument('--chunk-size', type=int, help='Chunk size.', default=25000)
parser.add_argument('--limit-taxonomies-to', type=str, help='Comma-delimited, e.g. 9606,10090,10116')
args = parser.parse_args()


chunk_size = args.chunk_size

limit_taxonomies = False
tax_ids_to_keep = []
if args.limit_taxonomies_to != None:
    limit_taxonomies = True
    tax_ids_to_keep = [int(x.strip()) for x in args.limit_taxonomies_to.split(',')] 

#
# fixed user settings
#
names_file = 'data/taxonomy/names.dmp'

#
# configure Neo4j connection
#
username = args.username
password = args.password
uri = 'bolt://' + args.hostname + ':7687'

#
# load names file
#
names_info = {}
f = open(names_file)
for line in f:
    line = [x.strip() for x in line.split('|')]
    tax_id = int(line[0])
    name = line[1]
    name_type = line[3]

    if limit_taxonomies:
        if not tax_id in tax_ids_to_keep:
            continue
    
    if name_type != 'scientific name':
        continue

    if name in ['', '-']:
        name = None

    names_info[tax_id] = name

f.close()

#
# output how many we expect to load
#
print()
print('We expect to load ' + str(len(names_info.keys())) + ' taxonomy nodes.')
print()

#
# connect to Neo4j
#
driver = GraphDatabase.driver(uri, auth=(username, password))

#
# clear the way (CRUDE)
#
cmd = 'MATCH (c:NCBI_TAXONOMY)-[r]-() DELETE r;'
with driver.session() as session:
    session.run(cmd)
cmd = 'MATCH (c:NCBI_TAXONOMY) DELETE c;'
with driver.session() as session:
    session.run(cmd)

#
# reorganize in a format useful for bulk Neo4j load
#
names_list = []
for tax_id in sorted(names_info.keys()):
    names_list.append([tax_id, names_info[tax_id]])

#
# load database
#
cmd = 'UNWIND $list_to_use AS n CREATE (c:NCBI_TAXONOMY {id : n[0], name : n[1]}) RETURN c;'
ut.load_list(names_list, chunk_size, driver, cmd)

#
# Make indices on id and name
#
cmd = 'CREATE INDEX ON :NCBI_TAXONOMY(id);'
with driver.session() as session:
    session.run(cmd)
cmd = 'CREATE INDEX ON :NCBI_TAXONOMY(name);'
with driver.session() as session:
    session.run(cmd)

#
# close Neo4j driver
#
driver.close()

