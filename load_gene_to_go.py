
#
# import useful libraries
#
import pprint as pp

#
# user settings
#
tax_ids_to_keep = [9606]

#
# read the file
#
go_id_to_term = {}
go_id_to_category = {}
go_id_to_gene = {}
unique_category = {}
f = open('data/gene/gene2go')
for line in f:
    line = [x.strip() for x in line.split('\t')]

    tax_id = line[0]
    if tax_id == '#tax_id':  continue
    tax_id = int(tax_id)
    if not tax_id in tax_ids_to_keep:  continue
    
    
    gene_id = int(line[1])
    go_id = line[2]
    term = line[5]

    pubmed = line[6]
    if pubmed.strip() == '-':
        pubmed = None
    else:
        pubmed = [int(x) for x in pubmed.split('|')]

    category = line[7]

    go_id_to_term[go_id] = term
    go_id_to_category[go_id] = category

    if not go_id in go_id_to_gene:
        go_id_to_gene[go_id] = {}
    go_id_to_gene[go_id][gene_id] = None

    unique_category[category] = None
    
f.close()

pp.pprint(unique_category)


