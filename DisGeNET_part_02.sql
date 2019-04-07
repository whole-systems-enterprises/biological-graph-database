.headers ON
.separator \t
.output stdout

SELECT DISTINCT da.diseaseID, da.diseaseName
FROM diseaseAttributes da
;
