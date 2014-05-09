# *Scrapeando* mapas: reconstruyendo fracciones y radios censales

*(También publicado en http://blog.jazzido.com/2014/05/09/scrapeando-mapas-reconstruyendo-fracciones-y-radios-censales/)*

Como a casi todos los que todos los que trabajamos con información pública, me interesa
conseguir información al menor nivel de *desagregación* posible. Para decirlo de otro modo, en alta
definición. Esa fue la idea detrás del [mapa de resultados electorales a nivel de *centro de
votación*](http://interactivos.lanacion.com.ar/mapa-elecciones-2013/) que hice el año pasado en
[LaNacion.com](http://lanacion.com), como becario
[Knight-Mozilla OpenNews](http://opennews.org). El primer proyecto que desarrollé durante esa beca,
fue una
[visualización interactiva de los datos arrojados por los dos últimos censos de población en Argentina](http://interactivos.lanacion.com.ar/censo/#Poblacion_Total-intercensal). El
plan original para ese proyecto también era mostrar los datos al menor nivel de desagregación
posible que para el censo son los *radios censales*, [definidos] [1] como una porción del espacio
geográfico que contiene en promedio 300 viviendas. Por desgracia, no estaban disponibles los mapas
que definen los radios, ni los datos de las variables censales a ese nivel.

[1]: https://www.santafe.gov.ar/index.php/web/content/view/full/163619/%28subtema%29/93664 "SantaFe.gov.ar"

Los radios censales son partes de una *fracción censal*, que están a su vez contenidas en los
departamentos o partidos, el segundo nivel de división administrativa en Argentina. Hoy es posible
disponer de los datos del último censo a nivel de radio censal. Cabe destacar que no fueron
publicados oficialmente, sino que
[aparecieron en el *tracker* de BitTorrent The Pirate Bay](https://thepiratebay.se/torrent/9642504/CPV2010BArgVer1.exe)
(!). Fueron publicados dentro de una aplicación basada en el sistema
[REDATAM](http://www.eclac.cl/redatam/default.asp?idioma=IN) y en [febrero pasado convertí esas tablas
a un formato más universal](http://blog.jazzido.com/2014/02/24/resultados-censo-2010-radio-censal/). Notar
que es necesario el uso de REDATAM para análisis tales como tabulaciones cruzadas (tablas
de contingencia). Por ejemplo, *universitarios que tienen acceso a internet por fracción censal en la provincia x*.

## La otra pieza del rompecabezas

Por supuesto, para visualizar estos resultados nos hacen falta las descripciones geográficas de las
fracciones y radios censales. A partir de los datos del censo, podemos acceder a todas las variables
—por ejemplo— del radio 300080111 y sabemos que está en la localidad de Colón de la provincia de Entre Ríos,
pero no conocemos sus límites exactos. Sólo la [provincia de Buenos Aires](http://www.ec.gba.gov.ar/estadistica/censo2010/cartografia.html)
y la
[Ciudad Autónoma de Buenos Aires](http://www.buenosaires.gob.ar/areas/hacienda/sis_estadistico/cartografia_censal_cnphv_2010.php?menu_id=35240)
publican cartografía censal en formatos estándar. El [INDEC](http://www.indec.gov.ar) mantiene un [sitio informativo sobre
"unidades geoestadísticas"](http://www.opex.sig.indec.gov.ar/codgeo/index.php?pagina=mapas) en el
que publica información geográfica hasta el nivel de radio censal (en formato SVG) pero desprovista de
georeferenciación. Es decir, podemos obtener la geometría de cualquier provincia,
departamento/partido, fracción o radio censal pero no está asociada al espacio físico. Este post
describirá un método de georeferenciación de esos gráficos vectoriales, usando *otro* mapa
publicado por INDEC como referencia.

## ¿Cómo se *scrapea* un mapa?

Podemos definir *scraping* como un proceso en el que recojemos información no estructurada y la
ajustamos a un esquema predefinido. Por ejemplo, un *scraper* de resultados de búsqueda de Google que
los almacene en una base de datos estructurada. Para este experimento, vamos a llevar a cabo un
procedimiento análogo, pero aplicado a mapas. Es decir, vamos a tomar gráficos vectoriales no-georeferenciados
del sitio de unidades geoestadísticas de INDEC y vamos a ajustarlo a una proyección geográfica
(POSGAR 94 Argentina 3).

## Malabares vectoriales

Los gráficos publicados en el nivel "departamento" de los SVG de INDEC son un gráfico vectorial de un
partido/departamento que contiene *fracciones*, que son el siguiente nivel en la jerarquía de
unidades geoestadísticas:

![Fracciones de Bahía Blanca](img/06056.png?raw=True)

En el gráfico de arriba, vemos los límites del partido de Bahía Blanca y sus divisiones internas
(fracciones).

Aunque INDEC no publica las unidades geoestadísticas de menor nivel en un formato georeferenciado,
sí pone a disposición un [mapa de departamentos](http://www.indec.gov.ar/default_gis.htm)
tal como fueron considerados para el último censo. Ese mapa será nuestra referencia para
georeferenciar los SVGs ya mencionados.

Para eso, vamos a tomar los puntos extremos (extremos de la envolvente) de un partido tal como fue publicado en el
SVG y del *mismo* partido tal como fue publicado en el mapa de departamentos, que sí está georeferenciado:

![Puntos correspondientes](img/puntos_correspondientes.png?raw=true)

Los puntos del mapa de la derecha están georeferenciados, y "sabemos" (asumimos, en realidad) que se corresponden con los
puntos del de la izquierda. Con ese par de conjuntos de puntos, podemos calcular una transformación
tal que convierta los vectores no-georeferenciados al espacio de coordenadas del mapa
georeferenciado. Para eso, vamos a usar el módulo [`transform`](http://scikit-image.org/docs/dev/api/skimage.transform.html)
de la librería [`scikit-image`](http://scikit-image.org/). Aclaremos cuanto antes, para que no se ofendan los cartógrafos y geómetras: este
procedimiento es muy poco formal (se muy poco de cartografía y de geometría) y poco preciso (el SVG está muy simplificado con respecto al mapa original).

Aplicandos esa transformación a todas las fracciones contenidas en el departamento, y procediendo de
manera análoga para el siguiente nivel geoestadístico (radios), vamos a obtener una aproximación
bastante burda a un mapa de fracciones y radios censales.

## Implementación

El procedimiento tal como se describió de manera muy resumida, está implementado en el programa
[`georef_svg.py`](https://github.com/jazzido/svg-map-scrape/blob/master/georef_svg.py). Para
correrlo, hay que instalar las dependencias listadas en `requirements.txt` y bajar los SVGs del
sitio de INDEC. Para eso, se provee el script
[`source_svg/download.sh`](https://github.com/jazzido/svg-map-scrape/blob/master/source_svgs/download.sh). Ejecutando
`python georef_svg.py .`, obtendremos dos *shapefiles* `fracciones.shp` y `radios.shp`, que
contienen el resultado del proceso.

El resultado no debe ser considerado como un mapa usable de fracciones y radios, dada las
imprecisiones y errores que contiene. En el mejor de los casos, quizás pueda ser un punto de partida
para la confección de un mapa apropiado...hasta que INDEC (o quien corresponda) publique la
información en un formato geográfico estándar.
