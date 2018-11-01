#
# useful libraries
#
import pprint as pp
from neo4j import GraphDatabase
import argparse
import sys
import os

#
# CRUDE
#
cwd = '/'.join(os.getcwd().split('/')[0:-1])
sys.path.append(cwd)
import utilities as ut

#
# command line arguments
#
parser = argparse.ArgumentParser(description='Set up SageMaker training data.')
parser.add_argument('--hostname', type=str, help='Hostname.', required=True)
parser.add_argument('--username', type=str, help='Neo4j username.', required=True)
parser.add_argument('--password', type=str, help='Neo4j password.', required=True)
parser.add_argument('--chunk-size', type=int, help='Chunk size.', default=25000)
args = parser.parse_args()

chunk_size = args.chunk_size

#
# configure Neo4j connection
#
username = args.username
password = args.password
uri = 'bolt://' + args.hostname + ':7687'

#
# connect to Neo4j
#
driver = GraphDatabase.driver(uri, auth=(username, password))

#
# get data
#
data = {}
cmd = 'MATCH (d:HMS_DISEASE)-[rdgc:HAS_HMS_DISEASE]-(gc:HMS_GENE_COMBO)-[rg:HAS_NCBI_GENE]-(g:NCBI_GENE)-[rt:HAS_NCBI_TAXONOMY]-(t:NCBI_TAXONOMY) WHERE t.id = 9606 RETURN d, rdgc, gc, rg, g, rt, t'
with driver.session() as session:
    results = session.run(cmd)
    for record in results:
        disease = record['d']['name']
        gene = record['g']['symbol']

        if not disease in data:
            data[disease] = {}
        data[disease][gene] = None

#
# reorganize
#
the_list = []
for disease in data.keys():
    for gene in data[disease].keys():
        the_list.append([disease, gene])

cmd = 'UNWIND $list_to_use AS n MATCH (g:NCBI_GENE), (d:HMS_DISEASE) WHERE d.name = n[0] AND g.symbol = n[1] CREATE (d)-[r:INVOLVES_NCBI_GENE]->(g) RETURN d, r, g;'
ut.load_list(the_list, chunk_size, driver, cmd)

#
# close Neo4j driver
#
driver.close()


