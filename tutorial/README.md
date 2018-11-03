# Tutorial

## Extremely basic stuff

Find all the taxonomies listed in the database:
```sql
MATCH (t:NCBI_TAXONOMY) RETURN t LIMIT 25;
```

Repeat this procedure in tabular form:
```sql
MATCH (t:NCBI_TAXONOMY) RETURN t.id as taxonomy_id, t.name AS species_name LIMIT 25;
```

