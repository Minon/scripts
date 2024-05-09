import bpy

bl_info = {
    "name": "Bone Constraint Toggles",
    "author": "Minon",
    "version": (1, 0),
    "blender": (3, 4, 0),
    "location": "Properties > Object Data (Armature) > Bone Constraint Toggles",
    "description": "Adds a 'Bone Constraint Toggles' panel to the Object Properties view for Armatures.  These can be used to enable/disable groups of bone constraints based on a prefix (or * for all at once)",
    "category": "Animation"}

class boneConstraintToggle(bpy.types.PropertyGroup):
    id : bpy.props.IntProperty()
    prefix : bpy.props.StringProperty()

class addBoneConstraintToggleOperator(bpy.types.Operator):
    bl_idname = "object.add_boneconstrainttoggle_operator"
    bl_label = "Add"
    bl_description = "Add a new bone constraint toggle"
    
    def execute(self, context):
        id = len(context.object.data.boneconstraint_toggles)
        new = context.object.data.boneconstraint_toggles.add()
        new.name = str(id)
        new.id = id
        new.prefix = "*"
        return {'FINISHED'}
    
class removeBoneConstraintToggleOperator(bpy.types.Operator):
    bl_idname = "object.remove_boneconstrainttoggle_operator"
    bl_label = "X"
    bl_description = "Remove this bone constraint toggle"
    
    id : bpy.props.IntProperty()
    
    def execute(self, context):
        index = 0
        while index < len(context.object.data.boneconstraint_toggles):
            if context.object.data.boneconstraint_toggles[index].id == self.id:
                context.object.data.boneconstraint_toggles.remove(index)
                break
            ++index
        return {'FINISHED'}

class boneConstraintToggleOperator(bpy.types.Operator):
    bl_idname = "object.boneconstrainttoggle_operator"
    bl_description = "toggles all bone constraints under this armature with the set prefix.  If the prefix is * it will toggle all of them"
    bl_label = "Toggle"
    
    prefix : bpy.props.StringProperty()
    enable : bpy.props.BoolProperty()
    
    def execute(self, context):
        for bone in context.object.pose.bones:
            for constraint in bone.constraints:
                if self.prefix == "*" or constraint.name.startswith(self.prefix):
                    constraint.enabled = self.enable
        return {'FINISHED'}

class boneConstraintTogglePanel(bpy.types.Panel):
    bl_label = "Bone Constraint Toggles"
    bl_idname = "OBJECT_PT_boneConstraintToggles"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'object'
    
    @classmethod
    def poll(cls, context):
        return context.object.type == 'ARMATURE'
    
    def draw(self, context):
        self.layout.operator("object.add_boneconstrainttoggle_operator")
        for item in context.object.data.boneconstraint_toggles:
            row = self.layout.row(align=True)
            row.prop(item, "prefix")
            op = row.operator("object.boneconstrainttoggle_operator", text="enable")
            op.prefix = item.prefix
            op.enable = True
            op = row.operator("object.boneconstrainttoggle_operator", text="disable")
            op.prefix = item.prefix
            op.enable = False
            row.operator("object.remove_boneconstrainttoggle_operator").id = item.id
    
classes = (
    boneConstraintToggle,
    addBoneConstraintToggleOperator,
    removeBoneConstraintToggleOperator,
    boneConstraintToggleOperator,
    boneConstraintTogglePanel
)    

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Armature.boneconstraint_toggles = bpy.props.CollectionProperty(type = boneConstraintToggle)
        
def unregister():
    del bpy.types.Armature.boneconstraint_toggles
    for cls in classes:
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()

#bpy.utils.unregister_class(bpy.types.OBJECT_PT_boneConstraintToggles)