#!/bin/bash
for id in `ogr2ogr -f CSV /vsistdout/ ../../departamentos_shp/paisxdpto2010.shp -sql "select LINK from paisxdpto2010"`; do
    wget -O $id.svg "http://www.opex.sig.indec.gov.ar/codgeo/mapas/link2svg.php?link=$id&width=1350&height=1500";
done
