import os
from math import floor
import bpy
from bpy.types import Operator
from bpy.props import (
    FloatVectorProperty,
    StringProperty,
    EnumProperty,
    BoolProperty,
    FloatProperty,
    IntProperty,
    PointerProperty)

from ..operators.assign_reference_object import (
    create_helper_object,
    assign_obj_to_obj_texture_coords)

from ..utils.registration import get_prefs

from ..lib.utils.vertex_groups import construct_displacement_mod_vert_group
from ..lib.utils.collections import add_object_to_collection, create_collection
from ..lib.utils.selection import select, deselect_all, activate
from ..lib.utils.multimethod import multimethod
from ..materials.materials import assign_mat_to_vert_group
from ..lib.utils.utils import get_all_subclasses

from ..enums.enums import (
    tile_blueprints,
    curve_types,
    base_socket_side,
    units,
    openlock_column_types,
    column_socket_style,
    collection_types)


def create_tile_type_enums(self, context):
    """Create an enum of tile types out of subclasses of MT_OT_Make_Tile."""
    enum_items = []
    if context is None:
        return enum_items

    # blueprint = context.scene.mt_scene_props.tile_blueprint
    subclasses = get_all_subclasses(MT_Tile_Generator)

    for subclass in subclasses:
        # if hasattr(subclass, 'mt_blueprint'):
        if 'INTERNAL' not in subclass.bl_options:
            enum = (subclass.mt_type, subclass.bl_label, "")
            enum_items.append(enum)
    return sorted(enum_items)


def create_main_part_blueprint_enums(self, context):
    """Dynamically creates a list of enum items depending on what is set in the tile_type defaults.

    Args:
        context (bpy.Context): scene context

    Returns:
        list[enum_item]: list of enum items
    """
    enum_items = []
    scene = context.scene
    scene_props = scene.mt_scene_props

    if context is None:
        return enum_items

    if 'tile_defaults' not in scene_props:
        return enum_items

    tile_type = scene_props.tile_type
    tile_defaults = scene_props['tile_defaults']

    for default in tile_defaults:
        if default['type'] == tile_type:
            for key, value in default['main_part_blueprints'].items():
                enum = (key, value, "")
                enum_items.append(enum)
            return sorted(enum_items)
    return enum_items


def create_base_blueprint_enums(self, context):
    enum_items = []
    scene = context.scene
    scene_props = scene.mt_scene_props

    if context is None:
        return enum_items

    if 'tile_defaults' not in scene_props:
        return enum_items

    tile_type = scene_props.tile_type
    tile_defaults = scene_props['tile_defaults']

    for default in tile_defaults:
        if default['type'] == tile_type:
            for key, value in default['base_blueprints'].items():
                enum = (key, value, "")
                enum_items.append(enum)
            return sorted(enum_items)
    return enum_items


def create_material_enums(self, context):
    """Create a list of enum items of materials compatible with the MakeTile material system.

    Args:
        context (bpy.context): context

    Returns:
        list[EnumPropertyItem]: enum items
    """
    enum_items = []
    if context is None:
        return enum_items

    materials = bpy.data.materials
    for material in materials:
        if 'mt_material' in material.keys():
            if material['mt_material']:
                enum = (material.name, material.name, "")
                enum_items.append(enum)
    return enum_items

class MT_Tile_Generator:
    """Subclass this to create your tile operator."""
    refresh: BoolProperty(
        name="Refresh",
        default=False,
        description="Refresh")

    auto_refresh: BoolProperty(
        name="Auto",
        default=True,
        description="Automatic Refresh")

    # Universal properties
    tile_type: EnumProperty(
        items=create_tile_type_enums,
        name="Tile Type",
        description="The type of tile e.g. Straight Wall, Curved Floor"
    )

    tile_material_1: EnumProperty(
        items=create_material_enums,
        name="Material"
    )

    # Tile type #
    main_part_blueprint: EnumProperty(
        items=create_main_part_blueprint_enums,
        name="Core"
    )

    base_blueprint: EnumProperty(
        items=create_base_blueprint_enums,
        name="Base"
    )

    # Native Subdivisions
    subdivision_density: EnumProperty(
        items=[
            ("HIGH", "High", "", 1),
            ("MEDIUM", "Medium", "", 2),
            ("LOW", "Low", "", 3)],
        default="MEDIUM",
        name="Subdivision Density")

    # Subsurf modifier subdivisions #
    subdivisions: IntProperty(
        name="Subdivisions",
        description="Subsurf modifier subdivision levels",
        default=3
    )

    # UV smart projection correction
    UV_island_margin: FloatProperty(
        name="UV Margin",
        default=0.012,
        min=0,
        step=0.001,
        description="Tweak this if you have gaps at edges of tiles when you Make3D"
    )

    # stops texture projecting beyond bounds of vert group
    texture_margin: FloatProperty(
        name="Texture Margin",
        description="Margin around displacement texture. Used for correcting distortion",
        default=0.001,
        min=0.0001,
        soft_max=0.1,
        step=0.0001
    )

    # Dimensions #
    # Tile size
    tile_x: FloatProperty(
        name="X",
        default=2.0,
        step=50,
        precision=2,
        min=0
    )

    tile_y: FloatProperty(
        name="Y",
        default=0.3,
        step=50,
        precision=2,
        min=0
    )

    tile_z: FloatProperty(
        name="Z",
        default=2.0,
        step=50,
        precision=2,
        min=0
    )

    # Base size
    base_x: FloatProperty(
        name="X",
        default=2.0,
        step=50,
        precision=2,
        min=0
    )

    base_y: FloatProperty(
        name="Y",
        default=0.5,
        step=50,
        precision=2,
        min=0
    )

    base_z: FloatProperty(
        name="Z",
        default=0.3,
        step=50,
        precision=2,
        min=0
    )

    tile_units: EnumProperty(
        name="Tile Units",
        items=units
    )

    @classmethod
    def poll(cls, context):
        if context.object is not None:
            return context.object.mode == 'OBJECT'
        else:
            return True

    def invoke(self, context, event):
        self.refresh = True
        scene_props = context.scene.mt_scene_props
        copy_property_group_values(scene_props, self)
        deselect_all()
        return self.execute(context)

    def execute(self, context):
        deselect_all()

    def draw(self, context):
        layout = self.layout
        if self.auto_refresh is False:
            self.refresh = False
        elif self.auto_refresh is True:
            self.refresh = True

        # Refresh options
        row = layout.box().row()
        split = row.split()
        split.scale_y = 1.5
        split.prop(self, "auto_refresh", toggle=True, icon_only=True, icon='AUTO')
        split.prop(self, "refresh", toggle=True, icon_only=True, icon='FILE_REFRESH')
        self.draw_universal_props(context)

    def draw_universal_props(self, context):
        layout = self.layout
        layout.prop(self, 'base_blueprint')
        layout.prop(self, 'main_part_blueprint')
        layout.prop(self, 'subdivision_density')


class MT_PT_Tile_Generator(Operator):
    bl_idname = "object.make_tile"
    bl_label = "New Make Tile"
    bl_description = "Add a Tile"
    bl_options = {'UNDO', 'REGISTER', 'PRESET'}

    refresh: BoolProperty(
        name="Refresh",
        default=False,
        description="Refresh")

    auto_refresh: BoolProperty(
        name="Auto",
        default=True,
        description="Automatic Refresh")

    # Universal properties
    tile_name: StringProperty(
        name="Tile Name",
        default="Tile"
    )

    tile_type: EnumProperty(
        items=create_tile_type_enums,
        name="Tile Type",
        description="The type of tile e.g. Straight Wall, Curved Floor"
    )

    tile_material_1: EnumProperty(
        items=create_material_enums,
        name="Material"
    )

    collection_type: EnumProperty(
        items=collection_types,
        name="Collection Types",
        description="Easy way of distinguishing whether we are dealing with a tile, \
            an architectural element or a larger prefab such as a building or dungeon."
    )

    # Tile type #
    main_part_blueprint: EnumProperty(
        items=create_main_part_blueprint_enums,
        name="Core"
    )

    base_blueprint: EnumProperty(
        items=create_base_blueprint_enums,
        name="Base"
    )


    # Native Subdivisions
    subdivision_density: EnumProperty(
        items=[
            ("HIGH", "High", "", 1),
            ("MEDIUM", "Medium", "", 2),
            ("LOW", "Low", "", 3)],
        default="MEDIUM",
        name="Subdivision Density")

    x_native_subdivisions: IntProperty(
        name="X",
        description="The number of times to subdivide the X axis on creation",
        default=15
    )

    y_native_subdivisions: IntProperty(
        name="Y",
        description="The number of times to subdivide the Y axis on creation",
        default=3
    )

    z_native_subdivisions: IntProperty(
        name="Z",
        description="The number of times to subdivide the Z axis on creation",
        default=15
    )

    opposite_native_subdivisions: IntProperty(
        name="Opposite Side",
        description="The number of times to subdivide the edge opposite the root angle on triangular tile creation",
        default=15
    )

    curve_native_subdivisions: IntProperty(
        name="Curved Side",
        description="The number of times to subdivide the curved side of a tile",
        default=15
    )

    leg_1_native_subdivisions: IntProperty(
        name="Leg 1",
        description="The number of times to subdivide the length of leg 1 of the tile",
        default=15
    )

    leg_2_native_subdivisions: IntProperty(
        name="Leg 2",
        description="The number of times to subdivide the length of leg 2 of the tile",
        default=15
    )

    width_native_subdivisions: IntProperty(
        name="Width",
        description="The number of times to subdivide each leg along its width",
        default=3
    )

    # Subsurf modifier subdivisions #
    subdivisions: IntProperty(
        name="Subdivisions",
        description="Subsurf modifier subdivision levels",
        default=3
    )

    # UV smart projection correction
    UV_island_margin: FloatProperty(
        name="UV Margin",
        default=0.012,
        min=0,
        step=0.001,
        description="Tweak this if you have gaps at edges of tiles when you Make3D"
    )

    # stops texture projecting beyond bounds of vert group
    texture_margin: FloatProperty(
        name="Texture Margin",
        description="Margin around displacement texture. Used for correcting distortion",
        default=0.001,
        min=0.0001,
        soft_max=0.1,
        step=0.0001
    )

    # used for where it makes sense to set displacement thickness directly rather than
    # as an offset between base and core. e.g. connecting columns
    displacement_thickness: FloatProperty(
        name="Displacement Thickness",
        description="Thickness of displacement texture.",
        default=0.05
    )

    # Dimensions #
    tile_size: FloatVectorProperty(
        name="Tile Size"
    )

    base_size: FloatVectorProperty(
        name="Base size"
    )

    base_radius: FloatProperty(
        name="Base Radius"
    )

    wall_radius: FloatProperty(
        name="Wall Radius"
    )

    base_socket_side: EnumProperty(
        name="Socket Side",
        items=base_socket_side
    )

    degrees_of_arc: FloatProperty(
        name="Degrees of Arc"
    )

    angle: FloatProperty(
        name="Angle"
    )

    leg_1_len: FloatProperty(
        name="Leg 1 Length"
    )

    leg_2_len: FloatProperty(
        name="Leg 2 Length"
    )

    curve_type: EnumProperty(
        name="Curve Type",
        items=curve_types
    )

    column_type: EnumProperty(
        items=openlock_column_types,
        name="Column type"
    )

    column_socket_style: EnumProperty(
        name="Socket Style",
        items=column_socket_style,
        default="TEXTURED"
    )

    tile_units: EnumProperty(
        name="Tile Units",
        items=units
    )

    tile_resolution: IntProperty(
        name="Tile Resolution"
    )

    @classmethod
    def poll(cls, context):
        obj = context.object
        if obj is not None:
            if obj.mode == 'EDIT':
                return False
        return True

    def invoke(self, context, event):
        self.refresh = True
        scene_props = context.scene.mt_scene_props
        self.tile_type = scene_props.tile_type
        return self.execute(context)

    def execute(self, context):
        if not self.refresh:
            return {'PASS_THROUGH'}
        print('executing')

        if self.auto_refresh is False:
            self.refresh = False
        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        if self.auto_refresh is False:
            self.refresh = False
        elif self.auto_refresh is True:
            self.refresh = True

        # Refresh options
        row = layout.box().row()
        split = row.split()
        split.scale_y = 1.5
        split.prop(self, "auto_refresh", toggle=True, icon_only=True, icon='AUTO')
        split.prop(self, "refresh", toggle=True, icon_only=True, icon='FILE_REFRESH')
        self.draw_universal_props(context)

    def draw_universal_props(self, context):
        layout = self.layout
        layout.prop(self, 'tile_type')
        layout.prop(self, 'tile_material_1', text="Main Material")
        layout.prop(self, 'UV_island_margin')
        layout.prop(self, 'subdivisions')

@multimethod(str, dict)
def get_subdivs(density, dims):
    """Get the number of times to subdivide each side when drawing.

    Args:
        density (ENUM in {'LOW', 'MEDIUM', 'HIGH'}): Density of subdivision
        dims (dict): Dimensions

    Returns:
        [list(int, int, int)]: subdivisions
    """
    subdivs = {}
    if density == 'LOW':
        multiplier = 4
    elif density == 'MEDIUM':
        multiplier = 8
    elif density == 'HIGH':
        multiplier = 16

    for k, v in dims.items():
        v = floor(v * multiplier)
        if v == 0:
            v = v + 1
        subdivs[k] = v
    return subdivs

@multimethod(str, list)
def get_subdivs(density, base_dims):
    """Get the number of times to subdivide each side when drawing.

    Args:
        density (ENUM in {'LOW', 'MEDIUM', 'HIGH'}): Density of subdivision
        base_dims (list(float, float, float)): Base dimensions

    Returns:
        [list(int)]: subdivisions
    """
    subdivs = []
    for x in base_dims:
        if density == 'LOW':
            multiplier = 4
        elif density == 'MEDIUM':
            multiplier = 8
        elif density == 'HIGH':
            multiplier = 16
    for x in base_dims:
        x = floor(x * multiplier)
        subdivs.append(x)
    subdivs = [x + 1 if x == 0 else x for x in subdivs]
    return subdivs

def initialise_tile_creator(context):
    deselect_all()
    scene = context.scene
    scene_props = scene.mt_scene_props

    # Root collection to which we add all tiles
    tiles_collection = create_collection('Tiles', scene.collection)

    # create helper object for material mapping
    create_helper_object(context)

    # set tile name
    tile_name = scene_props.tile_type.lower()

    # We create tile at origin and then move it to original location
    # this stops us from having to update the view layer every time
    # we parent an object
    cursor = scene.cursor
    cursor_orig_loc = cursor.location.copy()
    cursor_orig_rot = cursor.rotation_euler.copy()
    cursor.location = (0, 0, 0)
    cursor.rotation_euler = (0, 0, 0)

    return tile_name, tiles_collection, cursor_orig_loc, cursor_orig_rot


def create_common_tile_props(scene_props, tile_props, tile_collection):
    """Create properties common to all tiles."""
    copy_property_group_values(scene_props, tile_props)

    tile_props.tile_name = tile_collection.name
    tile_props.is_mt_collection = True
    tile_props.collection_type = "TILE"


def copy_property_group_values(source_prop_group, target_prop_group):
    """Set the props in the target property group to the value of the props in the source prop group.

    Props must have same names and be of same type

    Args:
        source_prop_group (bpy.Types.PropertyGroup): Source Property Group
        target_prop_group (bpy.Types.PropertyGroup): Target Property Group
    """
    for key in source_prop_group.__annotations__.keys():
        for k in target_prop_group.__annotations__.keys():
            if k == key:
                setattr(target_prop_group, str(k), getattr(source_prop_group, str(k)))


def lock_all_transforms(obj):
    """Lock all transforms.

    Args:
        obj (bpy.type.Object): object
    """
    # For some reason iterating doesn't work here
    obj.lock_location[0] = True
    obj.lock_location[1] = True
    obj.lock_location[2] = True
    obj.lock_rotation[0] = True
    obj.lock_rotation[1] = True
    obj.lock_rotation[2] = True
    obj.lock_scale[0] = True
    obj.lock_scale[1] = True
    obj.lock_scale[2] = True


def convert_to_displacement_core(core, textured_vertex_groups):
    """Convert the core part of an object so it can be used by the MakeTile dispacement system.

    Args:
        core (bpy.types.Object): object to convert
        textured_vertex_groups (list[str]): list of vertex group names that should have a texture applied
    """
    scene = bpy.context.scene
    preferences = get_prefs()
    props = core.mt_object_props
    scene_props = scene.mt_scene_props
    primary_material = bpy.data.materials[scene_props.tile_material_1]
    secondary_material = bpy.data.materials[preferences.secondary_material]

    # create new displacement modifier
    disp_mod = core.modifiers.new('MT Displacement', 'DISPLACE')
    disp_mod.strength = 0
    disp_mod.texture_coords = 'UV'
    disp_mod.direction = 'NORMAL'
    disp_mod.mid_level = 0
    disp_mod.show_render = True

    # save modifier name as custom property for use my maketile
    props.disp_mod_name = disp_mod.name
    props.displacement_strength = scene_props.displacement_strength
    # core['disp_mod_name'] = disp_mod.name

    # create a vertex group for the displacement modifier
    vert_group = construct_displacement_mod_vert_group(core, textured_vertex_groups)
    disp_mod.vertex_group = vert_group

    # create texture for displacement modifier
    props.disp_texture = bpy.data.textures.new(core.name + '.texture', 'IMAGE')
    '''
    # add a triangulate modifier to correct for distortion after bools
    core.modifiers.new('MT Triangulate', 'TRIANGULATE')
    '''
    # add a subsurf modifier
    subsurf = core.modifiers.new('MT Subsurf', 'SUBSURF')
    subsurf.subdivision_type = 'SIMPLE'
    props.subsurf_mod_name = subsurf.name
    core.cycles.use_adaptive_subdivision = True

    # move subsurf modifier to top of stack
    ctx = {
        'object': core,
        'active_object': core,
        'selected_objects': [core],
        'selected_editable_objects': [core]
    }

    bpy.ops.object.modifier_move_to_index(ctx, modifier=subsurf.name, index=0)

    subsurf.levels = 3

    # switch off subsurf modifier if we are not in cycles mode
    if bpy.context.scene.render.engine != 'CYCLES':
        subsurf.show_viewport = False

    # assign materials
    if secondary_material.name not in core.data.materials:
        core.data.materials.append(secondary_material)

    if primary_material.name not in core.data.materials:
        core.data.materials.append(primary_material)

    for group in textured_vertex_groups:
        assign_mat_to_vert_group(group, core, primary_material)

    # flag core as a displacement object
    core.mt_object_props.is_displacement = True
    core.mt_object_props.geometry_type = 'CORE'


def finalise_core(core, tile_props):
    """Finalise core.

    Set origin, UV project, set object props

    Args:
        core (bpy.types.Object): core
        tile_props (MakeTile.properties.MT_Tile_Properties): tile properties
    """
    ctx = {
        'object': core,
        'active_object': core,
        'selected_editable_objects': [core],
        'selected_objects': [core]
    }

    bpy.ops.object.origin_set(ctx, type='ORIGIN_CURSOR', center='MEDIAN')

    bpy.ops.object.editmode_toggle(ctx)
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(ctx, island_margin=tile_props.UV_island_margin)
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.object.editmode_toggle(ctx)

    obj_props = core.mt_object_props
    obj_props.is_mt_object = True
    obj_props.tile_name = tile_props.tile_name


def finalise_tile(base, core, cursor_orig_loc, cursor_orig_rot):
    """Finalise tile.

    Parent core to base, assign secondary material to base, reset cursor,
    select and activate base.

    Args:
        base (bpy.type.Object): base
        core (bpy.types.Object or list or tuple of bpy.types.Object): core(s)
        cursor_orig_loc (Vector(3)): original cursor location
        cursor_orig_rot (Vector(3)): original cursor rotation
    """
    context = bpy.context

    # Assign secondary material to our base if its a mesh
    prefs = get_prefs()
    if base.type == 'MESH' and prefs.secondary_material not in base.material_slots:
        base.data.materials.append(bpy.data.materials[prefs.secondary_material])

    # Reset location
    base.location = cursor_orig_loc
    cursor = context.scene.cursor
    cursor.location = cursor_orig_loc
    cursor.rotation_euler = cursor_orig_rot

    # Parent cores to base
    if core is not None:
        if isinstance(core, (list, tuple)):
            for c in core:
                c.parent = base
                lock_all_transforms(c)
        else:
            core.parent = base
            lock_all_transforms(core)

    # deselect any currently selected objects
    for obj in context.selected_objects:
        obj.select_set(False)

    base.select_set(True)
    context.view_layer.objects.active = base


def spawn_empty_base(tile_props):
    """Spawn an empty base into the scene.

    Args:
        tile_props (MakeTile.properties.MT_Tile_Properties): tile properties

    Returns:
        bpy.types.Object: Empty
    """
    tile_name = tile_props.tile_name
    base = bpy.data.objects.new(tile_name + '.base', None)
    base.name = tile_name + '.base'
    add_object_to_collection(base, tile_name)
    obj_props = base.mt_object_props
    obj_props.is_mt_object = True
    obj_props.geometry_type = 'BASE'
    obj_props.tile_name = tile_name
    base.show_in_front = True

    bpy.context.view_layer.objects.active = base
    return base


def spawn_prefab(context, subclasses, blueprint, mt_type):
    """Spawn a maketile prefab such as a base or tile core(s).

    Args:
        context (bpy.context): Blender context
        subclasses (list): list of all subclasses of MT_Tile_Generator
        blueprint (str): mt_blueprint enum item
        type (str): mt_type enum item

    Returns:
        bpy.types.Object: Prefab
    """
    # ensure we can only run bpy.ops in our eval statements
    allowed_names = {k: v for k, v in bpy.__dict__.items() if k == 'ops'}
    for subclass in subclasses:
        if hasattr(subclass, 'mt_type') and hasattr(subclass, 'mt_blueprint'):
            if subclass.mt_type == mt_type and subclass.mt_blueprint == blueprint:
                eval_str = 'ops.' + subclass.bl_idname + '()'
                eval(eval_str, {"__builtins__": {}}, allowed_names)

    prefab = context.active_object
    return prefab


def load_openlock_top_peg(tile_props):
    """Load an openlock style top peg for stacking wall tiles.

    Args:
        tile_props (MakeTile.properties.MT_Tile_Properties): tile properties

    Returns:
        bpy.types.Object: peg
    """
    prefs = get_prefs()
    tile_name = tile_props.tile_name

    booleans_path = os.path.join(
        prefs.assets_path,
        "meshes",
        "booleans",
        "openlock.blend")

    # load peg bool
    with bpy.data.libraries.load(booleans_path) as (data_from, data_to):
        data_to.objects = ['openlock.top_peg']

    peg = data_to.objects[0]
    peg.name = 'Top Peg.' + tile_name
    add_object_to_collection(peg, tile_name)

    return peg

# TODO: #3 Fix bug where toggling booleans in UI doesn't work if core or base have been renamed
def set_bool_obj_props(bool_obj, parent_obj, tile_props, bool_type):
    """Set properties for boolean object used for e.g. clip cutters.

    Args:
        bool_obj (bpy.types.Object): Boolean Object
        parent_obj (bpy.types.Object): Object to parent boolean object to
        MakeTile.properties.MT_Tile_Properties: tile properties
        bool_type (enum): enum in {'DIFFERENCE', 'UNION', 'INTERSECT'}
    """
    bpy.context.view_layer.update()

    if bool_obj.parent:
        matrix_copy = bool_obj.matrix_world.copy()
        bool_obj.parent = None
        bool_obj.matrix_world = matrix_copy

    bool_obj.parent = parent_obj
    bool_obj.matrix_parent_inverse = parent_obj.matrix_world.inverted()

    bool_obj.display_type = 'BOUNDS'
    # bool_obj.hide_set(True)
    bool_obj.hide_viewport = True
    bool_obj.hide_render = True

    bool_obj.mt_object_props.is_mt_object = True
    bool_obj.mt_object_props.boolean_type = bool_type
    bool_obj.mt_object_props.tile_name = tile_props.tile_name


def set_bool_props(bool_obj, target_obj, bool_type, solver='FAST'):
    """Set Properties for boolean and add bool to target_object's cutters collection.

    This allows boolean to be toggled on and off in MakeTile menu

    Args:
        bool_obj (bpy.types.Object): boolean object
        target_obj (bpy.types.Object): target object
        bool_type (enum): enum in {'DIFFERENCE', 'UNION', 'INTERSECT'}
        solver (enum in {'FAST', 'EXACT'}): Whether to use new exact solver
    """
    boolean = target_obj.modifiers.new(bool_obj.name + '.bool', 'BOOLEAN')
    boolean.solver = solver
    boolean.operation = bool_type
    boolean.object = bool_obj
    boolean.show_render = True

    # add cutters to object's cutters_collection
    # so we can activate and deactivate them when necessary
    cutter_coll_item = target_obj.mt_object_props.cutters_collection.add()
    cutter_coll_item.name = bool_obj.name
    cutter_coll_item.value = True
    bpy.context.view_layer.update()
    cutter_coll_item.parent = target_obj.name
