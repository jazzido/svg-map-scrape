#!/bin/bash

for radio_id in `cat ../fracciones/*svg | grep 'tipo="Fracción' | sed -nE 's/.*clave_unica="([^"]+)".*/\1/p' | sort | uniq`; do
    wget -O $radio_id.svg "http://www.opex.sig.indec.gov.ar/codgeo/mapas/link2svg.php?link=$radio_id&width=1350&height=1500";
done
