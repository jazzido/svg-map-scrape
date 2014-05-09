#!/bin/bash

# baja los mapas de fracciones y radios (SVG) que están en http://www.opex.sig.indec.gov.ar/codgeo

for id in `ogr2ogr -f CSV /vsistdout/ ../departamentos_shp/paisxdpto2010.shp -sql "select LINK from paisxdpto2010"`; do
    wget -O fracciones/$id.svg "http://www.opex.sig.indec.gov.ar/codgeo/mapas/link2svg.php?link=$id&width=1350&height=1500";
done

for radio_id in `cat fracciones/*svg | grep 'tipo="Fracción' | sed -nE 's/.*clave_unica="([^"]+)".*/\1/p' | sort | uniq`; do
    wget -O radios/$radio_id.svg "http://www.opex.sig.indec.gov.ar/codgeo/mapas/link2svg.php?link=$radio_id&width=1350&height=1500";
done
