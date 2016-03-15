"""
A generic JSON mesh exporter for Maya.

Authors:
    Sean Griffin
    Matt DesLauriers
"""

import sys

import os.path
import json
import shutil

from pymel.core import *
from maya.OpenMaya import *
from maya.OpenMayaMPx import *

kPluginTranslatorTypeName = 'SimpleJSON.json'
kOptionScript = 'SimpleJSONScript'
kDefaultOptionsString = '0'

FLOAT_PRECISION = 8

class SimpleJSONWriter(object):
    def __init__(self):
        self.componentKeys = [
            'vertices', 'normals', 'groups', 'uvs', 'dedupe',
            'materials', 'diffuseMaps', 'specularMaps', 'bumpMaps',
            'prettyOutput'
        ]

    def write(self, path, optionString, accessMode):
        self.path = path
        self.accessMode = accessMode
        self._parseOptions(optionString)
        self.materials = []
        self.geometries = {}
        self.instances = []
        
        if self.options["materials"]:
            print("Exporting All Materials...")
            self._exportMaterials()

        self._exportMeshes()

        print("Writing file...")
        output = {
            'metadata': {
                'exporter': 'maya-json-export',
                'version': 0.0
            },
            'materials': self.materials,
            'instances': self.instances,
            'geometries': self.geometries
        }

        with file(path, 'w') as f:
            if self.options['prettyOutput']:
                f.write(json.dumps(output, sort_keys=True, indent=4, separators=(',', ': ')))
            else:
                f.write(json.dumps(output, separators=(",",":")))

    def _getMeshes(self, nodes):
        meshes = []
        for node in nodes:
            if nodeType(node) == 'transform' and nodeType(node.getShape()) == 'mesh':
                meshes.append(node.getShape())
            else:
                for child in listRelatives(node, s=1):
                    if nodeType(child) == 'transform' and nodeType(node.getShape()) == 'mesh':
                        meshes.append(child.getShape())
        return meshes

    def _allMeshes(self):
        if self.accessMode == MPxFileTranslator.kExportAccessMode:
            print('Export all...')
            meshes = self._getMeshes(ls())
        elif self.accessMode == MPxFileTranslator.kExportActiveAccessMode:
            print('Export selection...')
            meshes = self._getMeshes(ls(selection=True))

        triMeshes = []
        for mesh in meshes:
            invalid = any(face.polygonVertexCount() != 3 for face in mesh.faces)
            if invalid:
                print('WARN: Skipping %s since it is not triangulated' % mesh.name())
            else:
                triMeshes.append(mesh)

        print('Exporting %d meshes' % len(triMeshes))
        return triMeshes

    def _parseOptions(self, optionsString):
        self.options = dict([(x, False) for x in self.componentKeys])
        for key in self.componentKeys:
            self.options[key] = key in optionsString

    def _exportMeshes(self):
        for mesh in self._allMeshes():
            name = mesh.name()
            underIdx = name.rfind('_')
            if self.options['dedupe'] and underIdx != -1:
                key = name[ : underIdx]
                instanceName = name[underIdx + 1 : ]
                if (key not in self.geometries):
                    self._exportGeometry(mesh, key)
                else:
                    print('Repeating instance %s' % name)
                self._exportMeshInstance(mesh, key, name)
            else:
                self._exportGeometry(mesh, name)
                self._exportMeshInstance(mesh, name, name)

    def _exportGeometry(self, mesh, key):
        print('Exporting geometry %s' % mesh.name())
        geom = {}
        self.geometries[key] = geom
        if self.options['vertices']:
            geom['position'] = self._getVertices(mesh)
            geom['positionIndices'] = self._getFaces(mesh)
        if self.options['normals']:
            geom['normal'] = self._getNormals(mesh)
            geom['normalIndices'] = self._getNormalIndices(mesh)
        if self.options['uvs']:
            geom['uv'] = self._getUVs(mesh)
            geom['uvIndices'] = self._getUVIndices(mesh)
        if self.options['groups']:
            geom['groups'] = self._getGroups(mesh)

    def _exportMeshInstance(self, mesh, geometryName, instanceName):
        parent = mesh.getParent()
        translation = parent.getTranslation(space='world')
        quaternion = parent.getRotation(space='world', quaternion=True)
        scale = parent.getScale()
        self.instances.append({
            'id': geometryName,
            'name': instanceName,
            'position': self._roundPos(translation),
            'scale': scale,
            'quaternion': self._roundQuat(quaternion)
        })

    def _roundPos(self, pos):
        return map(lambda x: round(x, FLOAT_PRECISION), [pos.x, pos.y, pos.z])

    def _roundQuat(self, rot):
        return map(lambda x: round(x, FLOAT_PRECISION), [rot.x, rot.y, rot.z, rot.w])

    def _getGroups(self, mesh):
        matIds = []
        groups = []
        numPoints = len(mesh.faces) * 3
        for face in mesh.faces:
            matIds.append(self._getMaterialIndex(face, mesh))
        # just one material index for whole geometry
        if all(x == matIds[0] for x in matIds):
            groups.append({
                'start': 0,
                'count': numPoints,
                'materialIndex': matIds[0]
            })
        # needs MultiMaterial
        else:
            lastId = matIds[0]
            start = 0
            for idx, matId in enumerate(matIds):
                if matId != lastId:
                    groups.append({
                        'start': start * 3,
                        'count': (idx - start) * 3,
                        'materialIndex': lastId
                    })
                    lastId = matId
                    start = idx
            # add final group
            groups.append({
                'start': start * 3,
                'count': (len(mesh.faces) - start) * 3,
                'materialIndex': lastId
            })
        return groups

    def _getMaterialIndex(self, face, mesh):
        if not hasattr(self, '_materialIndices'):
            self._materialIndices = dict([(mat['DbgName'], i) for i, mat in enumerate(self.materials)])

        if self.options['materials']:
            for engine in mesh.listConnections(type='shadingEngine'):
                if sets(engine, isMember=face) or sets(engine, isMember=mesh):
                    for material in engine.listConnections(type='lambert'):
                        if self._materialIndices.has_key(material.name()):
                            return self._materialIndices[material.name()]
        return -1

    def _getFaces(self, mesh):
        faces = []
        for face in mesh.faces:
            faces += face.getVertices()
        return faces

    def _getVertices(self, mesh, indexed=False):
        points = mesh.getPoints(space='object')
        return [ coord for point in points for coord in self._roundPos(point) ]

    def _getNormals(self, mesh, indexed=False):
        normals = []
        for normal in mesh.getNormals():
            normals += self._roundPos(normal)
        return normals

    def _getNormalIndices(self, mesh):
        indices = []
        for face in mesh.faces:
            for i in range(3):
                indices.append(face.normalIndex(i))
        return indices

    def _getUVIndices(self, mesh):
        indices = []
        for face in mesh.faces:
            for i in range(3):
                indices.append(face.getUVIndex(i))
        return indices

    def _getUVs(self, mesh, indexed=False):
        uvs = []
        us, vs = mesh.getUVs()
        for i, u in enumerate(us):
            uvs.append(u)
            uvs.append(vs[i])
        return uvs

    def _exportMaterials(self):
        for mat in ls(type='lambert'):
            self.materials.append(self._exportMaterial(mat))

    def _exportMaterial(self, mat):
        result = {
            "DbgName": mat.name(),
            "blending": "NormalBlending",
            "colorDiffuse": map(lambda i: i * mat.getDiffuseCoeff(), mat.getColor().rgb),
            "depthTest": True,
            "depthWrite": True,
            "shading": mat.__class__.__name__,
            "opacity": mat.getTransparency().a,
            "transparent": mat.getTransparency().a != 1.0,
            "vertexColors": False
        }
        if isinstance(mat, nodetypes.Phong):
            result["colorSpecular"] = mat.getSpecularColor().rgb
            result["reflectivity"] = mat.getReflectivity()
            result["specularCoef"] = mat.getCosPower()
            if self.options["specularMaps"]:
                self._exportSpecularMap(result, mat)
        if self.options["bumpMaps"]:
            self._exportBumpMap(result, mat)
        if self.options["diffuseMaps"]:
            self._exportDiffuseMap(result, mat)

        return result

    def _exportBumpMap(self, result, mat):
        for bump in mat.listConnections(type='bump2d'):
            for f in bump.listConnections(type='file'):
                result["mapNormalFactor"] = 1
                self._exportFile(result, f, "Normal")

    def _exportDiffuseMap(self, result, mat):
        for f in mat.attr('color').inputs():
            result["colorDiffuse"] = f.attr('defaultColor').get()
            self._exportFile(result, f, "Diffuse")

    def _exportSpecularMap(self, result, mat):
        for f in mat.attr('specularColor').inputs():
            result["colorSpecular"] = f.attr('defaultColor').get()
            self._exportFile(result, f, "Specular")

    def _exportFile(self, result, mapFile, mapType):
        src = mapFile.ftn.get()
        fName = os.path.basename(src)
        result["map" + mapType] = fName
        result["map" + mapType + "Repeat"] = [1, 1]
        result["map" + mapType + "Wrap"] = ["repeat", "repeat"]
        result["map" + mapType + "Anisotropy"] = 4

class SimpleJSONTranslator(MPxFileTranslator):
    def __init__(self):
        MPxFileTranslator.__init__(self)

    def haveWriteMethod(self):
        return True

    def filter(self):
        return '*.js*'

    def defaultExtension(self):
        return 'json'

    def writer(self, fileObject, optionString, accessMode):
        path = fileObject.fullName()
        writer = SimpleJSONWriter()
        writer.write(path, optionString, accessMode)


def translatorCreator():
    return asMPxPtr(SimpleJSONTranslator())

def initializePlugin(mobject):
    mplugin = MFnPlugin(mobject)
    try:
        mplugin.registerFileTranslator(kPluginTranslatorTypeName, None, translatorCreator, kOptionScript, kDefaultOptionsString)
    except:
        sys.stderr.write('Failed to register translator: %s' % kPluginTranslatorTypeName)
        raise

def uninitializePlugin(mobject):
    mplugin = MFnPlugin(mobject)
    try:
        mplugin.deregisterFileTranslator(kPluginTranslatorTypeName)
    except:
        sys.stderr.write('Failed to deregister translator: %s' % kPluginTranslatorTypeName)
        raise
