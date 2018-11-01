#
# import useful libraries
#
import pprint as pp
import pickle
from neo4j import GraphDatabase
import sys
import glob
import utilities as ut

#
# user settings
#
chunk_size = 25000
output_directory = 'output'
username = 'neo4j'
password = sys.argv[2]

hostname = sys.argv[1]
uri = 'bolt://' + hostname + ':7687'

#
# get file list
#
filename_list = glob.glob(output_directory + '/gene_lists/*')

#
# connect to Neo4j
#
driver = GraphDatabase.driver(uri, auth=(username, password))

#
# clear the way (CRUDE)
#
cmd = 'MATCH (c:NCBI_GENE)-[r]-() DELETE r;'
with driver.session() as session:
    session.run(cmd)
cmd = 'MATCH (c:NCBI_GENE) DELETE c;'
with driver.session() as session:
    session.run(cmd)

#
# iterate through the files
#
for filename in filename_list:
    with open(filename, 'rb') as f:
        names_list = pickle.load(f)
    
    #
    # load database
    #
    cmd = 'UNWIND $list_to_use AS n CREATE (g:NCBI_GENE {id : n[0], symbol : n[1], type_of_gene: n[2], name : n[3]}) RETURN g;'
    ut.load_list(names_list, chunk_size, driver, cmd)

#
# Make indices on id and name
#
cmd = 'CREATE INDEX ON :NCBI_GENE(id);'
with driver.session() as session:
    session.run(cmd)
cmd = 'CREATE INDEX ON :NCBI_GENE(symbol);'
with driver.session() as session:
    session.run(cmd)

#
# close Neo4j driver
#
driver.close()

