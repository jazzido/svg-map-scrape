import sys, re, os, traceback
from contextlib import contextmanager

import unicodecsv
from svg.path import parse_path
from lxml import etree
import ogr
import numpy as np
from skimage import transform

DEPARTAMENTOS_SHP = 'departamentos_shp/paisxdpto2010.shp'
SVG_NS = "http://www.w3.org/2000/svg"

# convertir un iterable de de complex() a un array de numpy
np_array  = lambda points: np.array([[p.real, p.imag] for p in points])

# invertir un complex() respecto del eje y
# (porque la proyección SVG está al revés que la proyección POSGAR Argentina 3)
invert_y  = lambda p0, h: complex(p0.real, h - p0.imag)

# query XPATH, incluyendo al namespace de SVG
xpath_svg = lambda tree, exp: tree.xpath(exp, namespaces={ 'svg': SVG_NS })

# estimar una transforación geométrica entre dos conjuntos de puntos
estimate_transform = lambda svg_points, shp_points: transform.estimate_transform('projective',
                                                                                 np_array(svg_points),
                                                                                 np_array(shp_points))

# retorna un list() de complex():
# con todos los puntos en un iterable de paths SVG (lista de lista de complex())
svg_paths_points = lambda paths, tr, svg_height: [(p.attrib,
                                                   [[p2c(tr(c2p(invert_y(line.start, svg_height)))[0])
                                                     for line in parse_path(ring + ' Z')]
                                                    for ring in p.attrib['d'].split('Z') if ring != ''])
                                                  for p in paths]

# todos los puntos en una geometria OGR
# set() de complex()
ogr_geom_points = lambda geom: set([complex(geom.GetPoint(i)[0], geom.GetPoint(i)[1]) for i in range(geom.GetPointCount())])

# convertir complex() a una tupla (r,i)
c2p = lambda c: (c.real, c.imag)
# convertir tupla (r,i) a un complex()
p2c = lambda p: complex(*p)

def find_bounding_box(points):
    """ envolvente de un iterable de puntos (complex()) """
    _t = sorted(map(lambda p: p.real, points))
    min_x, max_x = _t[0], _t[-1]

    _t = sorted(map(lambda p: p.imag, points))
    min_y, max_y = _t[0], _t[-1]

    return (
        complex(min_x, max_y),
        complex(max_x, max_y),
        complex(min_x, min_y),
        complex(max_x, min_y)
    )

def geocode_depto(prov, dpto, envelope_func=find_bounding_box):
    """
    Acá está la magia
    """
    fname = "source_svgs/fracciones/%02d%03d.svg" % (prov, dpto)

    with open(fname, 'r') as f:
        tree = etree.parse(f)

    svg_width = int(xpath_svg(tree, "//svg:svg/@width")[0])
    svg_height = int(xpath_svg(tree, "//svg:svg/@height")[0])
    paths = xpath_svg(tree,
                      "//svg:path[contains(@class, 'fraccion') and starts-with(@clave_unica, '%02d%03d')]" % (prov, dpto))

    # points:
    #   todos los vertices de todas las fracciones contenidas en el SVG
    points = set([
        invert_y(line.start, svg_height)
        for path_def in [q.attrib['d'] for q in paths]
        for line in parse_path(path_def)
    ])

    # svg_bounding_points:
    #  puntos extremos de points
    svg_bounding_points = envelope_func(points)

    shp_points = shapefile_points(DEPARTAMENTOS_SHP, "PROV = '%02d' AND DEPTO = '%03d'" % (prov, dpto))
    shp_bounding_points = envelope_func(shp_points)

    # tr:
    #  transformacion estimada a partir de los conjuntos de
    #  puntos extremos del SVG y del SHP
    tr = estimate_transform(svg_bounding_points, shp_bounding_points)

    # retorna:
    #  tuple list [ (atributos_path,  [ (line_start, line_end), ... ]), ... ]
    return svg_paths_points(paths, tr, svg_height)

def geocode_fraccion(prov, dpto, fraccion, reference_geom, envelope_func=find_bounding_box):
    fname = "source_svgs/radios/%02d%03d%02d.svg" % (prov, dpto, fraccion)
    print >>sys.stderr, fname
    with open(fname, 'r') as f:
        tree = etree.parse(f)

    svg_width = int(xpath_svg(tree, "//svg:svg/@width")[0])
    svg_height = int(xpath_svg(tree, "//svg:svg/@height")[0])
    paths = xpath_svg(tree,
                      "//svg:path[contains(@class, 'radio') and starts-with(@clave_unica, '%02d%03d%02d')]" % (prov, dpto, fraccion))

    # points:
    #   todos los vertices de todas las fracciones contenidas en el SVG
    points = set([
        invert_y(line.start, svg_height)
        for path_def in [q.attrib['d'] for q in paths]
        for line in parse_path(path_def)
    ])

    # svg_bounding_points:
    #  puntos extremos de points
    svg_bounding_points = envelope_func(points)

    shp_points = ogr_geom_points(reference_geom)
    shp_bounding_points = envelope_func(shp_points)

    # tr:
    #  transformacion estimada a partir de los conjuntos de
    #  puntos extremos del SVG y del SHP
    tr = estimate_transform(svg_bounding_points, shp_bounding_points)

    # retorna:
    #  tuple list [ (atributos_path,  [ (line_start, line_end), ... ]), ... ]
    return svg_paths_points(paths, tr, svg_height)


@contextmanager
def create_output_shape(dirname):
    out_datasource = ogr.GetDriverByName("ESRI Shapefile").CreateDataSource(dirname)

    yield out_datasource

    out_datasource.Destroy()

def fraccion_field_writer(feature, path):
    for a in ('clave_unica', 'tipo'):
        feature.SetField(a[:10], path[a].encode('utf-8'))
    for k, v in zip(('prov', 'dpto', 'id'), re.match('(\d{2})(\d{3})(\d{2})',
                                                     path['clave_unica']).groups()):
        feature.SetField(k, v)

def radio_field_writer(feature, path):
    feature.SetField('clave_unic', path['clave_unica'])
    feature.SetField('tipo', path['tipo'])
    for k, v in zip(('prov', 'dpto', 'fraccion', 'id'),
                    re.match('(\d{2})(\d{3})(\d{2})(\d{2})',
                             path['clave_unica']).groups()):
        feature.SetField(k, v)


def write_features_to_layer(paths, layer, field_writer):
    for path, rings in paths:
        feature = ogr.Feature(layer.GetLayerDefn())

        field_writer(feature, path)

        poly = ogr.Geometry(ogr.wkbPolygon)
        for i, ring in enumerate(rings):
            ring_geom = ogr.Geometry(ogr.wkbLinearRing)
            for point in ring:
                ring_geom.AddPoint(point.real, point.imag)

            poly.AddGeometry(ring_geom)
            poly.CloseRings()

        feature.SetGeometry(poly)

        layer.CreateFeature(feature)

def shapefile_points(fname, filter_exp):
    """ Collect all the geometries that match +filter_exp+ and return and
        iterable of points """
    ds = ogr.Open(fname)
    layer = ds.GetLayer(0)
    layer.ResetReading()

    layer.SetAttributeFilter(filter_exp)
    feat = layer.next()
    print >>sys.stderr, "%s - %s" %(feat.GetField("NOMPROV"), feat.GetField("NOMDEP1"))
    geom = feat.GetGeometryRef().GetGeometryRef(0)
    geom.SimplifyPreserveTopology(0.01)

    return ogr_geom_points(geom)

def shapefile_features(fname):
    """ Yield every feature in shapefile +fname+  """
    driver = ogr.GetDriverByName("ESRI Shapefile")
    ds = driver.Open(fname, 0)
    layer = ds.GetLayer(0)
    for feature in layer:
        yield feature

    ds.Destroy()

def main():
    with create_output_shape('output_shp') as shp:

        # layer de fracciones
        fracciones = shp.CreateLayer('fracciones', geom_type=ogr.wkbPolygon)
        # campos del layer de fracciones
        for a in ('prov', 'dpto', 'clave_unica', 'tipo', 'id', 'codigo'):
            fracciones.CreateField(ogr.FieldDefn(a[:10]),
                                   ogr.OFTString)

        for d in shapefile_features(DEPARTAMENTOS_SHP):
            prov, dpto = int(d['PROV']), int(d['DEPTO'])
            try:
                paths = geocode_depto(prov, dpto)
                write_features_to_layer(paths,
                                        fracciones,
                                        fraccion_field_writer)
            except Exception, e:
                print >>sys.stderr, "ERROR EN %s - %s (%d %d)" % (d['NOMPROV'], d['NOMDEP1'], prov, dpto)
                print >>sys.stderr, traceback.format_exc()

        shp.SyncToDisk()

        # layer de radios
        radios = shp.CreateLayer('radios', geom_type=ogr.wkbPolygon)
        # campos del layer de radios
        for a in ('prov', 'dpto', 'fraccion', 'clave_unica', 'tipo', 'id', 'codigo'):
            radios.CreateField(ogr.FieldDefn(a[:10]),
                               ogr.OFTString)

        for f in fracciones:
            try:
                paths = geocode_fraccion(int(f.GetField('prov')),
                                         int(f.GetField('dpto')),
                                         int(f.GetField('id')),
                                         f.GetGeometryRef().GetGeometryRef(0))
                write_features_to_layer(paths,
                                        radios,
                                        radio_field_writer)
            except Exception, e:
                print >>sys.stderr, "ERROR EN %s - %s (%d %d)" % (d['NOMPROV'], d['NOMDEP1'], prov, dpto)
                print >>sys.stderr, traceback.format_exc()

        shp.SyncToDisk()



if __name__ == '__main__':
    main()
