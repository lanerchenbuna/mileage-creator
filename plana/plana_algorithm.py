
# -*- coding: utf-8 -*-

"""
/***************************************************************************
 Mileage
                                 A QGIS plugin
 plana
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2024-05-17
        copyright            : (C) 2024 by lanerchen
        email                : 1452052463@qq.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

__author__ = 'lanerchen'
__date__ = '2024-05-17'
__copyright__ = '(C) 2024 by lanerchen'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

from qgis.core import (QgsProcessingAlgorithm, QgsProcessing, QgsProcessingParameterFeatureSink, QgsFeatureSink, QgsProcessingParameterFeatureSource,
                       QgsVectorLayer, QgsField, QgsFeature, QgsGeometry,
                       QgsPointXY, QgsProject)
from qgis.PyQt.QtCore import QVariant, QCoreApplication
import pandas as pd
from math import radians, degrees, floor, ceil


class MileageAlgorithm(QgsProcessingAlgorithm):
    INPUT = 'INPUT'
    OUTPUT = 'OUTPUT'
    # OUTPUT = 'OUTPUT'

    def initAlgorithm(self, config):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                self.tr('Input layer'),
                [QgsProcessing.TypeVectorAnyGeometry]
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr('Output layer')
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.INPUT, context)
        (sink, dest_id) = self.parameterAsSink(parameters, self.OUTPUT,
                                               context, source.fields(), source.wkbType(), source.sourceCrs())

        features = source.getFeatures()
        cols = [field.name() for field in source.fields()]
        records = [feat.attributes() for feat in features]
        df = pd.DataFrame(records, columns=cols)
        result_points = self.process(df)
        output_layer = self.add_points_to_layer(result_points)
        layers = output_layer.getFeatures()
        total = 100.0 / output_layer.featureCount() if output_layer.featureCount() else 0
        for current, feature in enumerate(layers):
            if feedback.isCanceled():
                break
            sink.addFeature(feature, QgsFeatureSink.FastInsert)
            feedback.setProgress(int(current * total))
        return {self.OUTPUT: dest_id}

    def calculate_haversine(self, point1_lat, point1_lon, point2_lat, point2_lon, num_points):
        lat1 = radians(point1_lat)
        lon1 = radians(point1_lon)
        lat2 = radians(point2_lat)
        lon2 = radians(point2_lon)
        delta_lat = (lat2 - lat1) / (num_points + 1)
        delta_lon = (lon2 - lon1) / (num_points + 1)
        points = []
        for i in range(1, num_points + 1):
            lat_i = lat1 + i * delta_lat
            lon_i = lon1 + i * delta_lon
            points.append((degrees(lat_i), degrees(lon_i)))
        return points

    def process(self, df):
        re_df = df[(df['type'] == 'mileage_number') & (df['range_query'] == 50)]
        re_df = re_df.sort_values(by=['line_id', 'position', 'mileage_value'])
        result_points = []
        for (line_id, position), group in re_df.groupby(['line_id', 'position']):
            group = group.reset_index()
            for i in range(len(group)-1):
                point1 = group.iloc[i]
                point2 = group.iloc[i + 1]
                num_points = ceil(point2['mileage_value']) - floor(point1['mileage_value']) -1
                if num_points > 0:
                    new_points = self.calculate_haversine(point1['latitude'], point1['longitude'], point2['latitude'],
                                                          point2['longitude'], num_points)
                    for j, (lat, lon) in enumerate(new_points):
                        mb=floor(point1['mileage_value']) + 1 + j
                        result_points.append({
                            'code': 'K' + str(floor(mb / 1000)) + "+" + str((mb - floor(mb / 1000) * 1000)),
                            'name': 'K'+str(floor(mb/1000))+"+"+str((mb-floor(mb/1000)*1000)),
                            'state': '0',
                            'mileage': 'K' + str(floor(mb / 1000)) + "+" + str((mb - floor(mb / 1000) * 1000)),
                            'mileage_value': mb,
                            'position': point1['position'],
                            'range_query': 5,
                            'type': 'mileage_number',
                            'project_id': point1['project_id'],
                            'record_create_date': point1['record_create_date'],
                            'record_update_date': point1['record_update_date'],
                            'line_id': point1['line_id'],
                            'latitude': lat,
                            'longitude': lon,
                            'parent_id': point1['id'],
                            'om_id': None,
                            'sync_delete': 1,
                        })

        return result_points

    def add_points_to_layer(self, points):
        vlayer = QgsVectorLayer("Point", "Points", "memory")
        pr = vlayer.dataProvider()
        pr.addAttributes([
            QgsField("id", QVariant.String),
            QgsField("code", QVariant.String),
            QgsField("name", QVariant.String),
            QgsField("state", QVariant.String),
            QgsField("mileage", QVariant.String),
            QgsField("mileage_value", QVariant.Double),
            QgsField("position", QVariant.String),
            QgsField("range_query", QVariant.Int),
            QgsField('type', QVariant.String),
            QgsField('project_id', QVariant.Int),
            QgsField('record_create_date', QVariant.String),
            QgsField('record_update_date', QVariant.String),
            QgsField("line_id", QVariant.Int),
            QgsField("latitude", QVariant.Double),
            QgsField("longitude", QVariant.Double),
            QgsField("parent_id", QVariant.Int),
            QgsField('om_id', QVariant.String),
            QgsField("sync_delete", QVariant.Int)
        ])
        vlayer.updateFields()
        for point in points:
            fet = QgsFeature()
            fet.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(point['longitude'], point['latitude'])))
            fet.setAttributes([None,
                point["code"], point["name"], int(point["state"]), point["mileage"],
                float(point['mileage_value']), point['position'], int(point['range_query']),
                point['type'], int(point['project_id']),
                point['record_create_date'],
                point['record_update_date'],
                int(point['line_id']), float(point['latitude']),
                float(point['longitude']),
                int(point['parent_id']),
                point['om_id'],
                int(point['sync_delete'])
            ])
            pr.addFeature(fet)
        vlayer.updateExtents()
        return vlayer

    def name(self):
        return 'mileage_algorithm'

    def displayName(self):
        return self.tr(self.name())

    def group(self):
        return self.tr(self.groupId())

    def groupId(self):
        return 'my_custom_algorithms'

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return MileageAlgorithm()

