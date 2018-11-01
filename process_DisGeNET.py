#
# Copyright 2018 Whole-Systems Enterprises, Inc.
#

#
# import useful libraries
#
import pprint as pp
from neo4j import GraphDatabase
import sys
import utilities as ut

#
# user settings
#
database_dump_file = 'data/DisGeNET/relevant_db_dump.tsv'

chunk_size = 10000
hostname = sys.argv[1]
username = 'neo4j'
password = sys.argv[2]
uri = 'bolt://' + hostname + ':7687'
skip_to_similarity_metrics = True




#
# connect to Neo4j
#
driver = GraphDatabase.driver(uri, auth=(username, password))





if not skip_to_similarity_metrics:

    #
    # load the data
    #
    data_association_type = {}
    data_source = {}
    data = {}
    f = open(database_dump_file)
    for i, line in enumerate(f):
        line = [x.strip() for x in line.split('\t')]
        if i == 0:
            header = line
            continue

        gene_id = int(line[3])
        disease = line[2]
        association_type = line[0]
        source = line[1]

        if not gene_id in data_source:
            data_source[gene_id] = {}
        if not disease in data_source[gene_id]:
            data_source[gene_id][disease] = []
        data_source[gene_id][disease].append(source)

        if not gene_id in data_association_type:
            data_association_type[gene_id] = {}
        if not disease in data_association_type[gene_id]:
            data_association_type[gene_id][disease] = []
        data_association_type[gene_id][disease].append(association_type)

        if not gene_id in data:
            data[gene_id] = {}
        if not disease in data[gene_id]:
            data[gene_id][disease] = {}
        if not source in data[gene_id][disease]:
            data[gene_id][disease][source] = {}
        if not association_type in data[gene_id][disease][source]:
            data[gene_id][disease][source][association_type] = 0
        data[gene_id][disease][source][association_type] += 1

    f.close()

    #
    # get count summary (and get distinct diseases while we are at it)
    #
    reorganized_data = {}
    distinct_diseases = {}
    for gene_id in data.keys():
        reorganized_data[gene_id] = {}
        for disease in data[gene_id].keys():
            distinct_diseases[disease] = None
            count = 0
            for source in data[gene_id][disease].keys():
                for association_type in data[gene_id][disease][source].keys():
                    count += 1
            reorganized_data[gene_id][disease] = count

    #
    # clear the way (CRUDE)
    #
    cmd = 'MATCH (c:DisGeNET_DISEASE)-[r]-() DELETE r;'
    with driver.session() as session:
        session.run(cmd)
    cmd = 'MATCH (c:DisGeNET_DISEASE) DELETE c;'
    with driver.session() as session:
        session.run(cmd)

    #
    # reorganize disease list
    #
    the_list = []
    for disease in sorted(list(distinct_diseases.keys())):
        the_list.append([disease])

    #
    # load diseases
    #
    cmd = 'UNWIND $list_to_use AS n CREATE (c:DisGeNET_DISEASE {id : n[0]}) RETURN c;'
    ut.load_list(the_list, chunk_size, driver, cmd)

    #
    # Make indices on id and name
    #
    cmd = 'CREATE INDEX ON :DisGeNET_DISEASE(id);'
    with driver.session() as session:
        session.run(cmd)

    #
    # reorganize dictionary
    #
    the_list = []
    for gene_id in reorganized_data.keys():
        for disease in reorganized_data[gene_id].keys():
            count = reorganized_data[gene_id][disease]
            the_list.append([gene_id, disease, count])

    #
    # load disease-gene relationships
    #
    cmd = 'UNWIND $list_to_use AS n MATCH (g:NCBI_GENE), (d:DisGeNET_DISEASE) WHERE g.id = n[0] AND d.id = n[1] CREATE (g)-[r:HAS_DisGeNET_DISEASE {entry_count : n[2]}]->(d);'
    ut.load_list(the_list, chunk_size, driver, cmd)

#
# Jaccard similarity
#
cmd = """MATCH (g:NCBI_GENE)-[:HAS_DisGeNET_DISEASE]->(d:DisGeNET_DISEASE)
WITH {item:id(g), categories: collect(id(d))} as geneDiseaseData
WITH collect(geneDiseaseData) as data
CALL algo.similarity.jaccard.stream(data)
YIELD item1, item2, count1, count2, intersection, similarity
RETURN algo.getNodeById(item1).name AS from, algo.getNodeById(item2).name AS to, intersection, similarity
ORDER BY similarity DESC;"""

with driver.session() as session:
    results = session.run(cmd)
    for record in results:
        print(record)

#
# close Neo4j driver
#
driver.close()
