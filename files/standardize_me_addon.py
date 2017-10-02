bl_info = {
    "version": (1, 0),
    "blender": (2, 78, 0),
    "author": "Ákos Tóth",
    "name": "MPEG-4 Standardization",
    "description": "Addon for MPEG-4 standardization of a 3D head model." ,
    "category": "Rigging",
}


import bpy
import bmesh
import os
import math
import mathutils
import numpy
from mathutils import Vector
from mathutils import Matrix

importedMeshes = {}
featurepoints = {}

regions_types_enum = [('L',"Lips","",1),('F',"Face","",2),('E',"Eye","",3), ('N',"Nose","",4)]
lips_featurepoints_enum = [('2.2',"2.2","",1), ('2.6',"2.6","",2), ('2.7',"2.7","",3), ('8.1',"8.1","",4), ('8.2',"8.2","",5), ('8.3',"8.3","",6), ('8.4',"8.4","",7), ('8.5',"8.5","",8), ('8.6',"8.6","",9), ('8.7',"8.7","",10), ('8.8',"8.8","",11)]
face_featurepoints_enum = [('5.1',"5.1","",1), ('5.2',"5.2","",2), ('5.3',"5.3","",3), ('5.4',"5.4","",4), ('2.1',"2.1","",5), ('2.10',"2.10","",6), ('2.11',"2.11","",7), ('2.12',"2.12","",8), ('4.1',"4.1","",9), ('4.2',"4.2","",10), ('4.3',"4.3","",11), ('4.4',"4.4","",12), ('4.5',"4.5","",13), ('4.6',"4.6","",14), ('10.1',"10.1","",15), ('10.2',"10.2","",16), ('10.5',"10.5","",17), ('10.6',"10.6","",18), ('11.1',"11.1","",19), ('11.2',"11.2","",20), ('11.3',"11.3","",21)]
eye_featurepoints_enum = [('3.1',"3.1","",1), ('3.2',"3.2","",2), ('3.3',"3.3","",3), ('3.4',"3.4","",4), ('3.5',"3.5","",5), ('3.6',"3.6","",6), ('3.7',"3.7","",7), ('3.8',"3.8","",8), ('3.11',"3.11","",9), ('3.12',"3.12","",10), ('3.92',"3.92","",11), ('3.93',"3.93","",12), ('3.94',"3.94","",13), ('3.95',"3.95","",14), ('3.96',"3.96","",15), ('3.97',"3.97","",16), ('3.98',"3.98","",17), ('3.99',"3.99","",18)]
nose_featurepoints_enum = [('9.1',"9.1","",1), ('9.2',"9.2","",2), ('9.3',"9.3","",3), ('9.6',"9.6","",4), ('9.7',"9.7","",5), ('9.12',"9.12","",6)]

# 0 = selection mode # 1 = creating mode
phase = 0

def deselect_vertices(self, context):
    
    bpy.ops.mesh.select_all(action = 'DESELECT')

def show_selected_feature_points(current_feature_point):
    
    if phase == 0: 
        index = 0
    
        if current_feature_point in featurepoints:
            index = featurepoints[current_feature_point]
        else:
            return {'FINISHED'}

        obj = bpy.context.active_object
        me = obj.data
        bm = bmesh.from_edit_mesh(me)

        vertices= [v for v in bm.verts]
    
        for vert in vertices:
            if vert.index == index:
                vert.select = True
            else:
                vert.select = False

        bmesh.update_edit_mesh(me, True)     
    else:
        return {'FINISHED'}

def get_vertex_by_index(index):
    
    obj = bpy.context.active_object
    me = obj.data
    bm = bmesh.from_edit_mesh(me)
    
    vertices = [v for v in bm.verts]
    
    x = y = z = 0.0
    
    for vert in vertices:
        if vert.index == index:
            x = vert.co.x
            y = vert.co.y
            z = vert.co.z
    
    return Vector((x, y, z))    

def all_points_inside(model, cage):
    
    mat = model.matrix_world.copy()
    
    vertices = [vert.co * mat for vert in model.data.vertices]    
    #all point inside
    api = True
    
    for v in vertices:
        if is_inside(v, cage) == False:
            api = False
            break    
    
    return api
    
def is_inside(point, ob):
    
    # axes = [ mathutils.Vector((1,0,0)), mathutils.Vector((0,1,0)), mathutils.Vector((0,0,1))  ]
    # @Abel, ok just one then
    axes = [ Vector((1,0,0)) ]
    outside = False
    for axis in axes:
        # @Atom you're right, ray_cast is in object_space
        # http://www.blender.org/documentation/250PythonDoc/bpy.types.Object.html#bpy.types.Object.ray_cast
        #mat = ob.matrix_world.copy()
        
        #get cage world matrix, because:
        #https://stackoverflow.com/questions/17181778/cannot-get-ray-cast-in-blender-to-work 
        sx, sy, sz = ob.scale
        mat_scX = Matrix.Scale(sx, 4, Vector([1, 0, 0]))
        mat_scY = Matrix.Scale(sy, 4, Vector([0, 1, 0]))
        mat_scZ = Matrix.Scale(sz, 4, Vector([0, 0, 1]))
        mat = mat_scX * mat_scY * mat_scZ
        orig = mat.inverted()*point
        count = 0
        while True:
            result,location,normal,index = ob.ray_cast(orig,orig+axis*10000.0)
            if index == -1: break
            count += 1
            orig = location + axis*0.00001
        if count%2 == 0:
            outside = True
            break
    return not outside

def betweentwopoints(a, b, c):
    
    minX = min(a[0], b[0])
    minY = min(a[1], b[1])
    minZ = min(a[2], b[2])
    
    maxX = max(a[0], b[0])
    maxY = max(a[1], b[1])
    maxZ = max(a[2], b[2])
    
    if (minX < c[0] and c[0] < maxX) and (minY < c[1] and c[1] < maxY) and (minZ < c[2] and c[2] < maxZ):
        return True
    else:
        return False

def projection(model, cage):
    
    model_mat = model.matrix_world.copy()
    cage_mat = cage.matrix_world.copy()
    cage_origo = cage_mat * cage.location
    
    cage_mesh = cage.data
    cage_verts = cage_mesh.vertices
    
    vertices = [cage_mat * vert.co for vert in cage.data.vertices]
    
    i = 0
    db = 0
    averageDist = 0.0
    noIntersectionPoints = []
    
    left_ear = [555, 558, 559, 729, 732, 733, 945, 1288, 1291, 1292, 1293, 1480, 1481]
    right_ear = [528, 529, 531, 716, 719, 720, 1018, 1019, 1020, 1335, 1390, 1478, 1479]
    
    #for 3 iter subdiv
    #left_ear = [2929, 2944, 2947, 2950, 2957, 2958, 2959, 3851, 3860, 3863, 3866, 3873, 3874, 3875, 4769, 5147, 5568, 5575, 5576, 5577, 5578, 5579, 5580, 5581, 5944, 5945]
    #right_ear = [2784, 2791, 2792, 2793, 2805, 2808, 2811, 3780, 3795, 3798, 3801, 3808, 3809, 3810, 4938, 4939, 4940, 4941, 4942, 4943, 4944, 5357, 5679, 5806, 5942, 5943]
        
    for v in vertices:
        
        cage_vertex_in_model_system = model_mat.inverted() * v
        origo_in_model_system = model_mat.inverted() * cage_origo
        direction = origo_in_model_system - cage_vertex_in_model_system
        direction.normalize()
        
        result, location, normal, index = model.ray_cast(cage_vertex_in_model_system, direction)
        
        globalofresult = model_mat * location
        result_in_cage_system = cage_mat.inverted() * globalofresult
            
        if betweentwopoints(cage_vertex_in_model_system, origo_in_model_system, location):
            
            translationMatrix = Matrix.Translation((result_in_cage_system - cage_verts[i].co) / 1.05)
            cage_verts[i].co = translationMatrix * cage_verts[i].co
            averageDist = averageDist + numpy.linalg.norm(cage_origo - cage_verts[i].co)  
            db = db + 1
        else:
            noIntersectionPoints.append(i)
                 
        i = i + 1
        
    averageDist = (averageDist / db) * 1.2
    
    for p in noIntersectionPoints:
        temp = cage_verts[p].co
        rate = 1.0 - (averageDist / numpy.linalg.norm(cage_origo - temp))
        translationMatrix = Matrix.Translation((cage_origo - temp) * rate)        
        cage_verts[p].co = translationMatrix * cage_verts[p].co    
    
    cage_details = bounds(model, False)
    
    for j in left_ear:
        temp = Vector((cage_details.x.min, 0, 0))
        temp = cage_mat.inverted() * temp
        cage_verts[j].co.x = temp[0]
    
    for j in right_ear:
        temp = Vector((cage_details.x.max, 0, 0))
        temp = cage_mat.inverted() * temp
        cage_verts[j].co.x = temp[0]
    
    return {'FINISHED'}

def bounds(obj, local=True):
    local_coords = obj.bound_box[:]
    om = obj.matrix_world

    if not local:    
        worldify = lambda p: om * Vector(p[:]) 
        coords = [worldify(p).to_tuple() for p in local_coords]
    else:
        coords = [p[:] for p in local_coords]

    rotated = zip(*coords[::-1])
    
    push_axis = []
    for (axis, _list) in zip('xyz', rotated):
        info = lambda: None
        info.max = max(_list)
        info.min = min(_list)
        info.distance = info.max - info.min
        push_axis.append(info)

    import collections

    originals = dict(zip(['x', 'y', 'z'], push_axis))

    o_details = collections.namedtuple('object_details', 'x y z')
    return o_details(**originals)

def compute_auxiliary_points():
        
        obj = bpy.data.objects[importedMeshes["original"]]
        obj_details = bounds(obj)
        
        featurepoints["12.1"] = Vector((get_vertex_by_index(featurepoints["11.2"]).x , obj_details.y.max, get_vertex_by_index(featurepoints["11.2"]).z))    
        featurepoints["12.2"] = Vector((get_vertex_by_index(featurepoints["11.3"]).x , obj_details.y.max, get_vertex_by_index(featurepoints["11.3"]).z))    
        featurepoints["12.3"] = Vector((get_vertex_by_index(featurepoints["5.1"]).x , obj_details.y.min, get_vertex_by_index(featurepoints["5.1"]).z))
        featurepoints["12.4"] = Vector((get_vertex_by_index(featurepoints["5.2"]).x , obj_details.y.min, get_vertex_by_index(featurepoints["5.2"]).z))    
        featurepoints["12.5"] = Vector((get_vertex_by_index(featurepoints["10.1"]).x , obj_details.y.max, obj_details.z.min))    
        featurepoints["12.6"] = Vector((get_vertex_by_index(featurepoints["10.2"]).x , obj_details.y.max, obj_details.z.min))    
        featurepoints["12.7"] = Vector((get_vertex_by_index(featurepoints["10.1"]).x , obj_details.y.min, obj_details.z.min))    
        featurepoints["12.8"] = Vector((get_vertex_by_index(featurepoints["10.2"]).x , obj_details.y.min, obj_details.z.min))    
            

def deformation():
        
    generic = bpy.data.meshes[importedMeshes["generic"]]
    genericObject = bpy.data.objects[importedMeshes["generic"]]

    genericCage = bpy.data.meshes[importedMeshes["generic_cage"]]
    genericCageObject = bpy.data.objects[importedMeshes["generic_cage"]]
    
    target = bpy.data.meshes[importedMeshes["original_cage"]]
    targetObject = bpy.data.objects[importedMeshes["original_cage"]]
    
    genericObject.modifiers.new("md", type = "MESH_DEFORM")
    genericObject.modifiers['md'].object = genericCageObject
    genericObject.modifiers['md'].precision = 4
    
    bpy.context.scene.objects.active = genericObject
    bpy.ops.object.meshdeform_bind(modifier = "md")   
    
    i = 0
    
    for v in target.vertices:
        x = y = z = 0
        
        x = target.vertices[i].co.x - genericCage.vertices[i].co.x
        y = target.vertices[i].co.y - genericCage.vertices[i].co.y
        z = target.vertices[i].co.z - genericCage.vertices[i].co.z
	
        genericCage.vertices[i].co.x = genericCage.vertices[i].co.x + x
        genericCage.vertices[i].co.y = genericCage.vertices[i].co.y + y
        genericCage.vertices[i].co.z = genericCage.vertices[i].co.z + z
    
        i = i + 1 
    
    bpy.ops.object.modifier_apply(apply_as = 'DATA', modifier = "md")
    bpy.ops.object.select_all(action='DESELECT')
    
    bpy.data.objects[importedMeshes["original"]].hide = True
    bpy.data.objects[importedMeshes["original_cage"]].hide = True
    bpy.data.objects[importedMeshes["generic_cage"]].hide = True
    
    originalDimX = bpy.data.objects[importedMeshes["original"]].dimensions.x
    originalDimY = bpy.data.objects[importedMeshes["original"]].dimensions.y
    originalDimZ = bpy.data.objects[importedMeshes["original"]].dimensions.z
    
    bpy.data.objects[importedMeshes["generic"]].dimensions = [originalDimX, originalDimY, originalDimZ]
    
class ImportFileOperator(bpy.types.Operator):
    bl_idname = "import.mpeg4model"
    bl_label = "Import Model"
    type = bpy.props.StringProperty()
    filepath = bpy.props.StringProperty(subtype="FILE_PATH")
    
    def execute(self, context):
        bpy.ops.import_scene.obj(filepath = self.filepath, split_mode = "OFF")
        path_list = self.filepath.split(os.sep)
        filenames = path_list[-1].split(".")
        importedMeshes[self.type] = filenames[0]
        
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class ExportFileOperator(bpy.types.Operator):
    bl_idname = "export.model"
    bl_label = "Export Model"
    filepath = bpy.props.StringProperty(subtype="FILE_PATH")
    
    def execute(self, context):
        bpy.ops.export_scene.obj(filepath=self.filepath, keep_vertex_order = True, use_selection= True, use_normals = True, use_materials = False, group_by_object = False, use_blen_objects = False)
        return {'FINISHED'}
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class CreateCage(bpy.types.Operator):
    bl_idname="create.cage"
    bl_label="createcage"
    
    def execute(self, context):
        #collect vertices
        verts = []

        verts.append(get_vertex_by_index(featurepoints["2.1"])) 
        verts.append(get_vertex_by_index(featurepoints["2.10"]))
        verts.append(get_vertex_by_index(featurepoints["2.12"]))
        verts.append(get_vertex_by_index(featurepoints["8.4"]))
        verts.append(get_vertex_by_index(featurepoints["5.2"]))
        verts.append(get_vertex_by_index(featurepoints["8.8"]))
        verts.append(get_vertex_by_index(featurepoints["2.11"]))
        verts.append(get_vertex_by_index(featurepoints["8.3"]))
        verts.append(get_vertex_by_index(featurepoints["8.7"]))
        verts.append(get_vertex_by_index(featurepoints["5.1"]))
        verts.append(get_vertex_by_index(featurepoints["8.2"]))
        verts.append(get_vertex_by_index(featurepoints["2.7"]))
        verts.append(get_vertex_by_index(featurepoints["8.6"]))
        verts.append(get_vertex_by_index(featurepoints["8.1"]))
        verts.append(get_vertex_by_index(featurepoints["2.2"]))
        verts.append(get_vertex_by_index(featurepoints["2.6"]))    
        verts.append(get_vertex_by_index(featurepoints["8.5"]))
        verts.append(get_vertex_by_index(featurepoints["9.1"]))
        verts.append(get_vertex_by_index(featurepoints["9.2"]))
        verts.append(get_vertex_by_index(featurepoints["5.3"]))
        verts.append(get_vertex_by_index(featurepoints["3.7"]))
        verts.append(get_vertex_by_index(featurepoints["9.7"]))
        verts.append(get_vertex_by_index(featurepoints["9.3"]))
        verts.append(get_vertex_by_index(featurepoints["9.12"]))
        verts.append(get_vertex_by_index(featurepoints["9.6"]))
        verts.append(get_vertex_by_index(featurepoints["5.4"]))
        verts.append(get_vertex_by_index(featurepoints["3.12"]))
        verts.append(get_vertex_by_index(featurepoints["3.99"]))
        verts.append(get_vertex_by_index(featurepoints["3.3"]))
        verts.append(get_vertex_by_index(featurepoints["3.98"]))
        verts.append(get_vertex_by_index(featurepoints["3.11"]))
        verts.append(get_vertex_by_index(featurepoints["3.5"]))
        verts.append(get_vertex_by_index(featurepoints["3.97"]))
        verts.append(get_vertex_by_index(featurepoints["3.1"]))
        verts.append(get_vertex_by_index(featurepoints["3.96"]))
        verts.append(get_vertex_by_index(featurepoints["4.3"]))
        verts.append(get_vertex_by_index(featurepoints["4.1"]))
        verts.append(get_vertex_by_index(featurepoints["4.2"]))
        verts.append(get_vertex_by_index(featurepoints["3.8"]))
        verts.append(get_vertex_by_index(featurepoints["3.95"]))
        verts.append(get_vertex_by_index(featurepoints["3.4"]))
        verts.append(get_vertex_by_index(featurepoints["3.94"]))
        verts.append(get_vertex_by_index(featurepoints["3.92"]))
        verts.append(get_vertex_by_index(featurepoints["3.6"]))
        verts.append(get_vertex_by_index(featurepoints["3.2"]))
        verts.append(get_vertex_by_index(featurepoints["3.93"]))
        verts.append(get_vertex_by_index(featurepoints["4.6"]))
        verts.append(get_vertex_by_index(featurepoints["4.4"]))
        verts.append(get_vertex_by_index(featurepoints["11.2"]))
        verts.append(get_vertex_by_index(featurepoints["11.1"]))
        verts.append(get_vertex_by_index(featurepoints["11.3"]))
        verts.append(get_vertex_by_index(featurepoints["4.5"]))
        verts.append(get_vertex_by_index(featurepoints["10.1"]))
        verts.append(get_vertex_by_index(featurepoints["10.5"]))
        verts.append(get_vertex_by_index(featurepoints["10.2"]))
        verts.append(get_vertex_by_index(featurepoints["10.6"]))
        
        compute_auxiliary_points()
        
        verts.append(featurepoints["12.1"])
        verts.append(featurepoints["12.2"])
        verts.append(featurepoints["12.5"])
        verts.append(featurepoints["12.3"])
        verts.append(featurepoints["12.4"])
        verts.append(featurepoints["12.6"])
        verts.append(featurepoints["12.7"])
        verts.append(featurepoints["12.8"])
        
           
        #collect faces
        faces = [ (0, 1, 2), (2, 3, 4), (2, 5, 3), (2, 1, 5), (0, 6, 1), (6, 7, 8), (6, 8, 1), (6, 9, 7), (1, 8, 10), (1, 10, 5), (5, 11, 3), (3, 11, 12), (5, 10, 11), (11, 13, 12), (10, 14, 11), (14, 13, 11), (10, 15, 14), (14, 15, 13), (15, 10, 8), (15, 16, 13), (15, 8, 7), (15, 7, 16), (9, 16, 7), (12, 4, 3), (9, 17, 16), (13, 16, 17), (13, 17, 18), (13, 18, 12), (12, 18, 4), (9, 19, 17), (9, 20, 19), (19, 21, 17), (17, 22, 18), (17, 23, 22), (17, 21, 23), (24, 23, 21), (24, 18, 23), (18, 22, 23), (24, 25, 18), (18, 25, 4), (4, 25, 26), (19, 27, 28), (19, 29, 21), (21, 29, 30), (27, 20, 31), (31, 32, 33), (20, 32, 31), (34, 31, 33), (34, 35, 36), (30, 34, 36), (32, 35, 33), (33, 35, 34), (21, 30, 36), (21, 36, 37), (24, 21, 37), (37, 38, 24), (24, 39, 25), (25, 39, 40), (25, 41, 26), (42, 43, 44), (38, 45, 43), (39, 38, 43), (43, 45, 44), (46, 42, 47), (42, 44, 47), (37, 47, 45), (44, 45, 47), (46, 47, 48), (47, 49, 48), (49, 47, 37), (36, 49, 37), (49, 36, 35), (49, 35, 50), (50, 35, 51), (52, 20, 9), (52, 9, 53), (9, 6, 53), (51, 20, 52), (50, 51, 52), (26, 54, 55), (26, 55, 4), (2, 4, 55), (46, 54, 26), (46, 48, 54), (48, 49, 56), (49, 50, 57), (49, 57, 56), (57, 50, 58), (50, 52, 58), (53, 6, 59), (6, 0, 59), (0, 2, 60), (59, 0, 60), (2, 55, 60), (54, 48, 61), (48, 56, 61), (56, 57, 61), (57, 58, 61), (59, 62, 53), (63, 60, 55), (59, 60, 62), (60, 63, 62), (62, 52, 53), (62, 58, 52), (55, 54, 63), (61, 63, 54), (58, 62, 61), (63, 61, 62), (40, 39, 43), (41, 40, 43), (26, 41, 43), (42, 26, 43), (26, 42, 46), (37, 45, 38), (41, 25, 40), (39, 24, 38), (34, 30, 31), (29, 31, 30), (29, 28, 31), (27, 31, 28), (32, 51, 35), (32, 20, 51), (29, 19, 28), (27, 19, 20)]
        
        #set new active object
        bpy.ops.object.mode_set(mode='OBJECT')
        active_obj = bpy.data.objects[importedMeshes["original"]]
        active_obj.select=False
        
        
        # Create mesh and object
        name_of_cage = importedMeshes["original"] + "_cage"
        me = bpy.data.meshes.new(name_of_cage)
        ob = bpy.data.objects.new(name_of_cage, me)
        ob.location = Vector((0,0,0))
 
       # Link object to scene and make active
        scn = bpy.context.scene
        scn.objects.link(ob)
        scn.objects.active = ob
        ob.select = True
       
       # Create mesh from given verts, faces.
        me.from_pydata(verts, [], faces)
        # Update mesh with new data
        me.update() 
        ob.rotation_euler = (math.radians(90),0,0)
        
        #update databases
        importedMeshes["original_cage"] = name_of_cage 
        bpy.context.scene.update()        
        
        #set creating mode
        global phase 
        phase = 1
        
        #scale cage        
        modelOB = bpy.data.objects[importedMeshes["original"]]
        cageOB = bpy.data.objects[importedMeshes["original_cage"]]
                
        scale_rate = 1.01
        
        while( not all_points_inside(modelOB, cageOB)):
            cageOB.scale = (scale_rate, scale_rate, scale_rate)
            scale_rate += 0.1
        
        #subdivide cage    
        cageOB.modifiers.new("subdiv", type='SUBSURF')
        cageOB.modifiers['subdiv'].levels = 2
        cageOB.modifiers['subdiv'].render_levels = 2
        cageOB.modifiers['subdiv'].subdivision_type='SIMPLE'        

        bpy.context.scene.objects.active = cageOB
        bpy.ops.object.modifier_apply(apply_as='DATA', modifier="subdiv")
        
        #project cage
        projection(modelOB, cageOB)
                    
        return {'FINISHED'}

class ExecuteDeformation(bpy.types.Operator):
    bl_idname = "deformate.mpeg4model"
    bl_label = "DeformateModel"

    def execute(self, context):
        deformation()
        return {'FINISHED'}

class FeaturePointOperator(bpy.types.Operator):
    bl_idname = "feature.point"
    bl_label = "featurepoint"
    mode = bpy.props.StringProperty()

    def execute(self, context):
        object_reference = bpy.context.active_object
        bm = bmesh.from_edit_mesh(object_reference.data)
        selected_verts = [vert for vert in bm.verts if vert.select]
        
        if bpy.context.scene.regions_type == 'L':
            if self.mode == 'SELECT':
                featurepoints[bpy.context.scene.lips_featurepoints] = selected_verts[0].index
            elif self.mode == 'REMOVE':
                del featurepoints[bpy.context.scene.lips_featurepoints]
                bpy.ops.mesh.select_all(action = 'DESELECT')
        elif bpy.context.scene.regions_type == 'F':
            if self.mode == 'SELECT':
                featurepoints[bpy.context.scene.face_featurepoints] = selected_verts[0].index
            elif self.mode == 'REMOVE':
                del featurepoints[bpy.context.scene.face_featurepoints]
                bpy.ops.mesh.select_all(action = 'DESELECT')
        elif bpy.context.scene.regions_type == 'E':
            if self.mode == 'SELECT':
                featurepoints[bpy.context.scene.eye_featurepoints] = selected_verts[0].index
            elif self.mode == 'REMOVE':
                del featurepoints[bpy.context.scene.eye_featurepoints]
                bpy.ops.mesh.select_all(action = 'DESELECT')
        elif bpy.context.scene.regions_type == 'N':
            if self.mode == 'SELECT':
                featurepoints[bpy.context.scene.nose_featurepoints] = selected_verts[0].index
            elif self.mode == 'REMOVE':
                del featurepoints[bpy.context.scene.nose_featurepoints]
                bpy.ops.mesh.select_all(action = 'DESELECT')
        
        return {'FINISHED'}


class MPEG4Panel(bpy.types.Panel):
    bl_label = "MPEG-4 Feature Point Selection Panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_category = "MPEG-4 Standardization"

    def draw(self, context):
        layout = self.layout
        
        layout.operator("import.mpeg4model", text="Import Original Model", icon="FILE_FOLDER").type="original"
        
        layout.label(text = "Regions:")        
        layout.prop(context.scene, 'regions_type', expand= True)
        
        if bpy.context.scene.regions_type == 'L':
            layout.prop(context.scene, 'lips_featurepoints')
            show_selected_feature_points(bpy.context.scene.lips_featurepoints)
        elif bpy.context.scene.regions_type == 'F':
            layout.prop(context.scene, 'face_featurepoints')
            show_selected_feature_points(bpy.context.scene.face_featurepoints) 
        elif bpy.context.scene.regions_type == 'E':
            layout.prop(context.scene, 'eye_featurepoints')
            show_selected_feature_points(bpy.context.scene.eye_featurepoints)    
        elif bpy.context.scene.regions_type == 'N':
            layout.prop(context.scene, 'nose_featurepoints')
            show_selected_feature_points(bpy.context.scene.nose_featurepoints)
        
        row = layout.row(align=True)  
        row.alignment = 'EXPAND'      
        row.operator(FeaturePointOperator.bl_idname, text="Select Feature Point", icon='PINNED').mode='SELECT'
        row.operator(FeaturePointOperator.bl_idname, text="Remove Feature Point", icon='UNPINNED').mode='REMOVE'  
        
        row = layout.row()
        
        row.operator(CreateCage.bl_idname, 'Create Cage', icon = 'MOD_LATTICE')
        row.operator(ExportFileOperator.bl_idname, 'Export Cage', icon = 'EXPORT')
        
        layout.split()
        layout.split()
        layout.split()
        
        layout.operator("import.mpeg4model", text="Import Cage", icon="FILE_FOLDER").type="original_cage"
        layout.operator("import.mpeg4model", text="Import Generic Model", icon="FILE_FOLDER").type="generic"
        layout.operator("import.mpeg4model", text="Import Generic Cage", icon="FILE_FOLDER").type="generic_cage"
        
        layout.split()
        layout.split()
        layout.split()
        
        layout.operator(ExecuteDeformation.bl_idname, text='Run Deformation', icon = 'GROUP')

def register():
    bpy.utils.register_class(MPEG4Panel)
    bpy.utils.register_class(FeaturePointOperator)
    bpy.utils.register_class(CreateCage)
    bpy.utils.register_class(ImportFileOperator)
    bpy.utils.register_class(ExportFileOperator)
    bpy.utils.register_class(ExecuteDeformation)
    bpy.types.Scene.regions_type = bpy.props.EnumProperty(name = "Regions", default = "L", items = regions_types_enum, update = deselect_vertices)
    bpy.types.Scene.lips_featurepoints = bpy.props.EnumProperty(name = "Feature Points", default = "2.2", items = lips_featurepoints_enum, update = deselect_vertices)
    bpy.types.Scene.face_featurepoints = bpy.props.EnumProperty(name = "Feature Points", default = "5.1", items = face_featurepoints_enum, update = deselect_vertices)
    bpy.types.Scene.eye_featurepoints = bpy.props.EnumProperty(name = "Feature Points", default = "3.1", items = eye_featurepoints_enum, update = deselect_vertices)
    bpy.types.Scene.nose_featurepoints = bpy.props.EnumProperty(name = "Feature Points", default = "9.1", items = nose_featurepoints_enum, update = deselect_vertices)

def unregister():
    bpy.utils.unregister_class(MPEG4Panel)
    bpy.utils.unregister_class(FeaturePointOperator)
    bpy.utils.unregister_class(CreateCage)
    bpy.utils.unregister_class(ImportFileOperator)
    bpy.utils.unregister_class(ExportFileOperator)
    bpy.utils.unregister_class(ExecuteDeformation)
    bpy.types.Scene.regions_type
    bpy.types.Scene.lips_featurepoints
    bpy.types.Scene.face_featurepoints
    bpy.types.Scene.eye_featurepoints
    bpy.types.Scene.nose_featurepoints

if __name__ == "__main__":
    register()
