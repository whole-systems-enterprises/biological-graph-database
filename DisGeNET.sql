.headers ON
.separator \t
.output stdout

SELECT gd.associationType, gd.source, da.diseaseId, ga.geneId 
FROM geneDiseaseNetwork gd, diseaseAttributes da, geneAttributes ga 
WHERE 
gd.diseaseNID = da.diseaseNID AND 
gd.geneNID = ga.geneNID
;

