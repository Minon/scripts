bl_info = {
    "name": "Milkshape3D",
    "author": "Minon",
    "version": (1, 0, 0),
    "blender": (2, 80, 0),
    "location": "File > Import",
    "description": "Import Milkshape3D (.ms3d) files",
    "warning": "",
    "wcooliki_url": "",
    "tracker_url": "",
    "category": "Import"}

import bpy
import mathutils
import struct
import math
from pathlib import Path

from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator

"""Importer script for Milkshape3D ms3d files

Author:
    Minon - Mar.9.2023
"""
class MS3D_Import(Operator, ImportHelper):
    """Imports a Milkshape3D file as a single object"""

    @staticmethod
    def readInt16(file):
        return int.from_bytes(file.read(2), 'little')
    
    @staticmethod
    def readFloat(file):
        return struct.unpack('f', file.read(4))[0]
    
    @staticmethod
    def readInt(file):
        return int.from_bytes(file.read(4), 'little')
    
    @staticmethod
    def readString(file, length):
        bytes = file.read(length)
        s = bytes.split(b'\0')[0].decode('ascii')
        s.encode('utf-8', 'strict')
        return s
    
    @staticmethod
    def readVec2(file):
        x = MS3D_Import.readFloat(file)
        y = MS3D_Import.readFloat(file)
        return mathutils.Vector((x, y))
    
    @staticmethod
    def readVec3_raw(file):
        x = MS3D_Import.readFloat(file)
        y = MS3D_Import.readFloat(file)
        z = MS3D_Import.readFloat(file)
        return mathutils.Vector((x, y, z))
    
    @staticmethod
    def readVec3_yz(file):
        x = MS3D_Import.readFloat(file)
        y = MS3D_Import.readFloat(file)
        z = MS3D_Import.readFloat(file)
        return mathutils.Vector((x, y, z))
    
    @staticmethod
    def readVec3_zy(file):
        x = MS3D_Import.readFloat(file)
        y = MS3D_Import.readFloat(file)
        z = MS3D_Import.readFloat(file)
        return mathutils.Vector((x, -z, y))
    
    @staticmethod
    def readRotation_yz(file):
        x = MS3D_Import.readFloat(file)
        y = MS3D_Import.readFloat(file)
        z = MS3D_Import.readFloat(file)
        return mathutils.Euler((x, y, z), 'XYZ')
    
    @staticmethod
    def readRotation_zy(file):
        x = MS3D_Import.readFloat(file)
        y = MS3D_Import.readFloat(file)
        z = MS3D_Import.readFloat(file)
        return mathutils.Euler((x, -z, y), 'XZY')

    @staticmethod
    def splitAnimation(baseAnim, name, startFrame, endFrame):
        anim = bpy.data.actions.new(name)
        for baseF in baseAnim.fcurves:
            f = anim.fcurves.new(baseF.data_path, index=baseF.array_index, action_group=baseF.group.name)
            for baseKf in baseF.keyframe_points:
                if baseKf.co.x < startFrame:
                    continue
                if baseKf.co.x > endFrame:
                    break
                f.keyframe_points.insert(baseKf.co.x - startFrame, baseKf.co.y)
    
    def read_ms3d(self, context, filepath, doFlipYZ, doSplitAnim):
        print("Attempting to open " + filepath)
        f = open(filepath, 'rb')
        lastIndex = filepath.rfind('\\')
        dirpath = filepath[0:lastIndex+1]
        print('directory path: ' + dirpath)
        
        #shortens method calls
        readInt = self.readInt
        readInt16 = self.readInt16
        readFloat = self.readFloat
        readString = self.readString
        readVec2 = self.readVec2
        readVec3_raw = self.readVec3_raw
        if doFlipYZ:
            readVec3 = self.readVec3_zy
            readRotation = self.readRotation_zy
        else:
            readVec3 = self.readVec3_yz
            readRotation = self.readRotation_yz
        
        #read header
        data = f.read(10)
        header = str(data, 'UTF-8')
        if header != 'MS3D000000':
            print('error: invalid header')
            return {'CANCELLED'}
        
        #read file version
        fileVersion = readInt(f)
        if fileVersion != 4:
            print('error: invalid file version: ' + str(fileVersion))
            return {'CANCELLED'}
        
        #read vertices
        vertCount = self.readInt16(f)
        print('vertex count: ' + str(vertCount))
        
        vertPos = []
        vertBIndexes = []
        vertBWeights = []
        
        for i in range(vertCount):
            f.read(1) #flags
            vertPos.append(readVec3(f)) #pos
            vertBIndexes.append((int.from_bytes(f.read(1), 'little'), 0, 0, 0)) #bone index
            vertBWeights.append((1.0, 0.0, 0.0, 0.0))
            f.read(1) #ref count
            
        #read triangles
        triCount = self.readInt16(f)
        print('triangle count: ' + str(triCount))
        
        triIndexes = []
        triNorms = []
        triUVs = []
        triSmoothGroup = []
        triGroupIndex = []
        
        for i in range(triCount):
            f.read(2) #flags
            triIndexes.append((readInt16(f), readInt16(f), readInt16(f))) #indexes
            triNorms.append((readVec3(f), readVec3(f), readVec3(f))) #normals
            triUVs.append((readVec3_raw(f), readVec3_raw(f))) #uvs, for whatever reason stored in order u0, u1, u2, v0, v1, v2
            triSmoothGroup.append(f.read(1)) #smooth group
            triGroupIndex.append(int.from_bytes(f.read(1), 'little')) #group index
        
        #read groups
        groupCount = self.readInt16(f)
        groupMaterialIndex = []
        
        for i in range(groupCount):
            f.read(1) #flags
            readString(f, 32) #group name
            gTriCount = readInt16(f) #triangles in group
            for j in range(gTriCount):
                readInt16(f) #triangle indexes
            groupMaterialIndex.append(int.from_bytes(f.read(1), 'little')) #material index
            
        #read materials
        matCount = readInt16(f)
        materials = []
        
        for i in range(matCount):
            name = readString(f, 32) #material name
            material = bpy.data.materials.new(name)
            materials.append(material)
            material.use_nodes = True
            bsdfNode = material.node_tree.nodes['Principled BSDF']
            readFloat(f) #ambient r
            readFloat(f) #ambient g
            readFloat(f) #ambient b
            readFloat(f) #ambient a
            readFloat(f) #diffuse r
            readFloat(f) #diffuse g
            readFloat(f) #diffuse b
            readFloat(f) #diffuse a
            readFloat(f) #specular r
            readFloat(f) #specular g
            readFloat(f) #specular b
            readFloat(f) #specular a
            readFloat(f) #emissive r
            readFloat(f) #emissive g
            readFloat(f) #emissive b
            readFloat(f) #emissive a
            readFloat(f) #specular power
            readFloat(f) #alpha
            f.read(1) #mode (spheremapping and such, I think)
            strPath = readString(f, 128) #diffuse texture filepath
            if strPath != '':
                texNode = material.node_tree.nodes.new('ShaderNodeTexImage')
                material.node_tree.links.new(texNode.outputs['Color'], bsdfNode.inputs['Base Color'])
                texPath = Path(strPath)
                #if the texture file doesn't exist as-is, attempt to find it in the ms3d file's directory
                if not texPath.exists():
                    strPath = str(texPath)
                    lastIndex = strPath.rfind('\\')
                    texPath = Path(dirpath + strPath[lastIndex+1:])
                if texPath.exists():
                    texNode.image = bpy.data.images.load(str(texPath.absolute()))
                else:
                    print('Warning: texture path not found at: ' + str(texPath.absolute()))
            readString(f, 128) #alphablend(probably) texture filepath
            
        #read animation config
        animFps = readFloat(f)
        readFloat(f) #current time on timeline
        maxFrames = readInt(f)
        
        #read joints (skeleton)
        jointCount = readInt16(f)
        armature = bpy.data.armatures.new("ms3dSkeleton")
        
        #create object
        obj = bpy.data.objects.new("ms3dObj", armature)
        
        #add object to scene
        bpy.context.scene.collection.objects.link(obj)
        
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        editBones = armature.edit_bones
        bonesByIndex = []
        bones = {}
        boneNames = {}
        boneTransforms = {}
        
        defaultAnim = bpy.data.actions.new('default')
        
        #action -> actionGroup > channels > keyframe
        #in my words: animation -> bone -> dimension > keyframe
        #channels are linked to properties using data_path, e.g. 'pose.bones["rHand"].location'
        #    and array_index, which marks the index into the vector of that property
        #    so basically 0 for x, 1 for y, 2 for z
        #actionGroups are actually optional but definitely sensible to have
        
        for i in range(jointCount):
            f.read(1) #flags
            name = readString(f, 32)
            b = editBones.new(name)
            bones[name] = b
            boneNames[b] = name
            bonesByIndex.append(b)
            parnName = readString(f, 32)
            if parnName in bones.keys():
                b.parent = bones[parnName]
            rot = readRotation(f) #joint local rotation
            pos = mathutils.Vector(readVec3(f)) #joint localposition
            b.head = mathutils.Vector((0, 0, 0))
            b.tail = mathutils.Vector((0, 0, 1))
            posMat = mathutils.Matrix.Translation(pos)
            rotMat = rot.to_matrix().to_4x4()
            p = b.parent
            transform = posMat @ rotMat
            if b.parent:
                transform = boneTransforms[b.parent] @ transform
            b.matrix = transform
            boneTransforms[b] = transform
            rotKfCount = readInt16(f) #number of rotation keyframes
            transKfCount = readInt16(f) #number of translation keyframes
            #create animation channels
            actionGroup = defaultAnim.groups.new(name)
            posX = defaultAnim.fcurves.new('pose.bones["' + name + '"].location', index=0, action_group=name)
            posY = defaultAnim.fcurves.new('pose.bones["' + name + '"].location', index=1, action_group=name)
            posZ = defaultAnim.fcurves.new('pose.bones["' + name + '"].location', index=2, action_group=name)
            rotW = defaultAnim.fcurves.new('pose.bones["' + name + '"].rotation_quaternion', index=0, action_group=name)
            rotX = defaultAnim.fcurves.new('pose.bones["' + name + '"].rotation_quaternion', index=1, action_group=name)
            rotY = defaultAnim.fcurves.new('pose.bones["' + name + '"].rotation_quaternion', index=2, action_group=name)
            rotZ = defaultAnim.fcurves.new('pose.bones["' + name + '"].rotation_quaternion', index=3, action_group=name)
            sclX = defaultAnim.fcurves.new('pose.bones["' + name + '"].scale', index=0, action_group=name)
            sclY = defaultAnim.fcurves.new('pose.bones["' + name + '"].scale', index=1, action_group=name)
            sclZ = defaultAnim.fcurves.new('pose.bones["' + name + '"].scale', index=2, action_group=name)
            boneRotMat = rotMat 
            boneRotMat.invert()
            for j in range(rotKfCount):
                t = readFloat(f) * animFps #timePos
                rot = readRotation(f) #rotation
                q = rot.to_quaternion()
                rotW.keyframe_points.insert(t, q.w)
                rotX.keyframe_points.insert(t, q.x)
                rotY.keyframe_points.insert(t, q.y)
                rotZ.keyframe_points.insert(t, q.z)
            for j in range(transKfCount):
                t = readFloat(f) * animFps #timePos
                pos = readVec3(f) #translation
                posX.keyframe_points.insert(t, pos[0])
                posY.keyframe_points.insert(t, pos[1])
                posZ.keyframe_points.insert(t, pos[2])
            sclX.keyframe_points.insert(0, 1)
            sclY.keyframe_points.insert(0, 1)
            sclZ.keyframe_points.insert(0, 1)
            
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        
        #read comments
        subVersion = readInt(f)
        if subVersion == 1:
            #group comments
            count = readInt(f)
            for i in range(count):
                i_group = readInt(f)
                length = readInt(f)
                comment = readString(f, length)
                print('Group comment ' + str(i_group) + ':')
                print(comment)
            #material comments
            count = readInt(f)
            for i in range(count):
                i_material = readInt(f)
                length = readInt(f)
                comment = readString(f, length)
                material = materials[i_material]
                print('Material comment ' + str(i_material) + ':')
                print(comment)
                #use material comment to adjust other values not supported by ms3d
                for line in comment.splitlines():
                    #<inputName> <texture filepath>
                    i_space = line.find(' ')
                    if i_space > 0:
                        strInputName = line[0:i_space]
                        bsdfNode = material.node_tree.nodes['Principled BSDF']
                        i_input = bsdfNode.inputs.find(strInputName)
                        #check if the input exists
                        if i_input > -1:
                            texNode = material.node_tree.nodes.new('ShaderNodeTexImage')
                            material.node_tree.links.new(texNode.outputs['Color'], bsdfNode.inputs[i_input])
                            texPath = Path(line[i_space+1:])
                            #if the texture file doesn't exist as-is, attempt to find it in the ms3d file's directory
                            if not texPath.exists():
                                strPath = str(texPath)
                                lastIndex = strPath.rfind('\\')
                                texPath = Path(dirpath + strPath[lastIndex+1:])
                            if texPath.exists():
                                texNode.image = bpy.data.images.load(str(texPath.absolute()))
                            else:
                                print('Warning: texture path not found at: ' + str(texPath.absolute()))
            #joint comments
            count = readInt(f)
            for i in range(count):
                i_joint = readInt(f)
                length = readInt(f)
                comment = readString(f, length)
                print('Joint comment ' + str(i_joint) + ':')
                print(comment)
            #model comment
            count = readInt(f) #should be 1 at most
            for i in range(count):
                length = readInt(f)
                comment = readString(f, length)
                print('Model comment:')
                print(comment)
                #use model comment to split animations
                for line in comment.splitlines():
                    data = line.split()
                    #anim <animationName> <startFrame> <endFrame>
                    if data[0] == 'anim' and doSplitAnim and len(data) > 2:
                        startFrame = int(data[2])
                        #endFrame is optional, making it a single frame when omitted
                        if len(data) > 3:
                            endFrame = int(data[3])
                        else:
                            endFrame = startFrame
                        self.splitAnimation(defaultAnim, data[1], startFrame, endFrame)
        
        #close file
        f.close()
        
        #build the mesh
        mesh = bpy.data.meshes.new('ms3dMesh')
        mesh.use_auto_smooth = True
        mesh.from_pydata(vertPos, [], triIndexes)
        for material in materials:
            mesh.materials.append(material)
        uvLayer = mesh.uv_layers.new()
        mesh.uv_layers.active = uvLayer
        for i in range(len(mesh.polygons)):
            face = mesh.polygons[i]
            face.material_index = groupMaterialIndex[triGroupIndex[i]]
            for j in range(len(face.vertices)):
                uvLayer.data[face.loop_indices[j]].uv = mathutils.Vector((triUVs[i][0][j], 1.0 - triUVs[i][1][j]))
        
        meshObj = bpy.data.objects.new('ms3dMesh', mesh)
        meshObj.parent = obj
        smoothing = meshObj.modifiers.new('smoothing', 'EDGE_SPLIT')
        smoothing.use_edge_angle = False
        
        bpy.context.scene.collection.objects.link(meshObj)
        meshObj.select_set(True)
        bpy.ops.object.shade_smooth()
        
        #rigging
        #create vertexGroups
        vertGroups = []
        for b in bonesByIndex:
            groupName = boneNames[b] #for some reason using b.name here causes utf8 errors
            group = meshObj.vertex_groups.new(name=groupName)
            vertGroups.append(group)
        
        #add indexes to vertexGroups
        for i in range(len(vertBIndexes)):
            vertGroups[vertBIndexes[i][0]].add([i], 1.0, 'ADD')
            
        #add the armature deform modifier
        deformer = meshObj.modifiers.new('armature', 'ARMATURE')
        deformer.object = obj

        return {'FINISHED'}

    #=== Blender Importer Data
    bl_idname = "import_test.ms3d"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Import MS3D"

    # ImportHelper mixin class uses this
    filename_ext = ".ms3d"

    filter_glob: StringProperty(
        default="*.ms3d",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.
    doYZFlip: BoolProperty(
        name="Use Z as Up",
        description="Flips the Y and Z axis so Up is in the Z axis",
        default=True,
    )
    
    doSplitAnim: BoolProperty(
        name="Split Animations",
        description="Split animations using model comments",
        default=True,
    )

    def execute(self, context):
        return self.read_ms3d(context, self.filepath, self.doYZFlip, self.doSplitAnim)

#==

# Only needed if you want to add into a dynamic menu
def menu_func_import(self, context):
    self.layout.operator(MS3D_Import.bl_idname, text="Milkshape3D (.ms3d)")

# Register and add to the "file selector" menu (required to use F3 search "Text Import Operator" for quick access)
def register():
    bpy.utils.register_class(MS3D_Import)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unregister_class(MS3D_Import)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)


if __name__ == "__main__":
    register()

    # test call
    #bpy.ops.import_test.ms3d('INVOKE_DEFAULT')