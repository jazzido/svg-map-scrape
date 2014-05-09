#!/bin/bash

# baja los mapas de fracciones y radios (SVG) que están en http://www.opex.sig.indec.gov.ar/codgeo

for dpto_id in `ogr2ogr -f CSV /vsistdout/ ../departamentos_shp/paisxdpto2010.shp -sql "select LINK from paisxdpto2010"`; do
    wget -O - "http://www.opex.sig.indec.gov.ar/codgeo/mapas/link2svg.php?link=$dpto_id&width=1350&height=1500" | tidy -xml > fracciones/$dpto_id.svg;
done

for fraccion_id in `cat fracciones/*svg | grep 'tipo="Fracción' | sed -nE 's/.*clave_unica="([^"]+)".*/\1/p' | sort | uniq`; do
    wget -O - "http://www.opex.sig.indec.gov.ar/codgeo/mapas/link2svg.php?link=$fraccion_id&width=1350&height=1500" | tidy -xml > radios/$fraccion_id.svg ;
done
