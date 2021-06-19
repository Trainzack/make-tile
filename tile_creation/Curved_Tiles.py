import os
from math import radians, pi, modf, degrees
from mathutils import Vector
import bpy
from bpy.types import Operator, Panel
from bpy.props import (
    FloatProperty,
    EnumProperty,
    BoolProperty,
    StringProperty)

from ..lib.utils.collections import (
    add_object_to_collection)

from ..utils.registration import get_prefs

from ..lib.bmturtle.scripts import (
    draw_straight_wall_core,
    draw_rectangular_floor_core,
    draw_curved_cuboid)

from ..lib.utils.selection import (
    deselect_all,
    select,
    activate)

from ..lib.utils.utils import (
    add_circle_array,
    get_all_subclasses)


from .create_tile import (
    convert_to_displacement_core,
    spawn_empty_base,
    spawn_prefab,
    set_bool_obj_props,
    set_bool_props,
    load_openlock_top_peg,
    MT_Tile_Generator,
    get_subdivs,
    create_material_enums,
    add_subsurf_modifier)


class MT_PT_Curved_Wall_Tile_Panel(Panel):
    """Draw a tile options panel in the UI."""

    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Make Tile"
    bl_label = "Tile Options"
    bl_order = 1
    bl_idname = "MT_PT_Curved_Wall_Tile_Panel"
    bl_description = "Options to configure the dimensions of a tile"

    @classmethod
    def poll(cls, context):
        """Check tile_type."""
        if hasattr(context.scene, 'mt_scene_props'):
            return context.scene.mt_scene_props.tile_type == "CURVED_WALL"
        return False

    def draw(self, context):
        """Draw the Panel."""
        scene = context.scene
        scene_props = scene.mt_scene_props

        layout = self.layout

        layout.label(text="Blueprints")
        layout.prop(scene_props, 'base_blueprint')
        layout.prop(scene_props, 'main_part_blueprint')

        layout.label(text="Materials")
        layout.prop(scene_props, 'floor_material')
        layout.prop(scene_props, 'wall_material')

        layout.label(text="Tile Properties")

        layout.prop(scene_props, 'tile_z', text="Height")
        layout.prop(scene_props, 'base_radius', text="Radius")
        layout.prop(scene_props, 'degrees_of_arc')
        layout.prop(scene_props, 'base_socket_side', text="Socket Side")
        layout.prop(scene_props, 'curve_texture', text="Curve Texture")

        layout.label(text="Core Properties")
        layout.prop(scene_props, 'tile_y', text="Width")

        if scene_props.base_blueprint in ('OPENLOCK_S_WALL', 'PLAIN_S_WALL'):
            layout.label(text="Floor Thickness")
            layout.prop(scene_props, 'floor_thickness', text="")

            layout.label(text="Wall Position")
            layout.prop(scene_props, 'wall_position', text="")

        layout.label(text="Sync Proportions")
        row = layout.row()
        row.prop(scene_props, 'y_proportionate_scale', text="Width")
        row.prop(scene_props, 'z_proportionate_scale', text="Height")

        layout.label(text="Base Properties")
        layout.prop(scene_props, 'base_y', text="Width")
        layout.prop(scene_props, 'base_z', text="Height")

        layout.label(text="Subdivision Density")
        layout.prop(scene_props, 'subdivision_density', text="")

        layout.label(text="UV Island Margin")
        layout.prop(scene_props, 'UV_island_margin', text="")

        layout.operator('scene.reset_tile_defaults')


class MT_PT_Curved_Floor_Tile_Panel(Panel):
    """Draw a tile options panel in the UI."""

    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Make Tile"
    bl_label = "Tile Options"
    bl_order = 1
    bl_idname = "MT_PT_Curved_Floor_Tile_Panel"
    bl_description = "Options to configure the dimensions of a tile"

    @classmethod
    def poll(cls, context):
        """Check tile_type."""
        if hasattr(context.scene, 'mt_scene_props'):
            return context.scene.mt_scene_props.tile_type == "CURVED_FLOOR"
        return False

    def draw(self, context):
        """Draw the Panel."""
        scene = context.scene
        scene_props = scene.mt_scene_props
        layout = self.layout

        layout.label(text="Blueprints")
        layout.prop(scene_props, 'base_blueprint')
        layout.prop(scene_props, 'main_part_blueprint')

        layout.label(text="Materials")
        layout.prop(scene_props, 'floor_material')

        layout.label(text="Tile Properties")
        layout.prop(scene_props, 'tile_z', text="Height")
        layout.prop(scene_props, 'base_radius', text="Radius")
        layout.prop(scene_props, 'degrees_of_arc')
        layout.prop(scene_props, 'base_socket_side', text="Socket Side")
        layout.prop(scene_props, 'curve_texture', text="Curve Texture")

        layout.label(text="Core Properties")
        layout.prop(scene_props, 'tile_y', text="Width")

        layout.label(text="Sync Proportions")
        row = layout.row()
        row.prop(scene_props, 'y_proportionate_scale', text="Width")
        row.prop(scene_props, 'z_proportionate_scale', text="Height")

        layout.label(text="Base Properties")
        layout.prop(scene_props, 'base_y', text="Width")
        layout.prop(scene_props, 'base_z', text="Height")

        layout.label(text="Subdivision Density")
        layout.prop(scene_props, 'subdivision_density', text="")

        layout.label(text="UV Island Margin")
        layout.prop(scene_props, 'UV_island_margin', text="")

        layout.operator('scene.reset_tile_defaults')


class MT_Curved_Tile:
    def update_curve_texture(self, context):
        """Change whether the texture on a curved floor tile follows the curve or not."""
        if self.tile_name:
            tile_collection = bpy.data.collections[self.tile_name]
            for obj in tile_collection.objects:
                obj_props = obj.mt_object_props
                if obj_props.is_displacement:
                    try:
                        mod = obj.modifiers['Simple_Deform']
                        if mod.show_render:
                            mod.show_render = False
                        else:
                            mod.show_render = True
                    except KeyError:
                        pass
        else:
            try:
                obj = context.active_object
                obj_props = obj.mt_object_props
                if obj_props.is_displacement:
                    try:
                        mod = obj.modifiers['Simple_Deform']
                        if mod.show_render:
                            mod.show_render = False
                        else:
                            mod.show_render = True
                    except KeyError:
                        pass
            except AttributeError:
                pass

    base_socket_side: EnumProperty(
        items=[
            ("INNER", "Inner", "", 1),
            ("OUTER", "Outer", "", 2)],
        name="Socket Side",
        default="INNER",
    )

    degrees_of_arc: FloatProperty(
        name="Degrees of arc",
        default=90,
        step=45,
        precision=1,
        max=359.999,
        min=0
    )

    # Used for curved wall tiles
    base_radius: FloatProperty(
        name="Base inner radius",
        default=2.0,
        step=50,
        precision=1,
        min=0,
    )

    wall_radius: FloatProperty(
        name="Wall inner radius",
        default=2.0,
        step=50,
        precision=1,
        min=0
    )

    # used for curved floors
    curve_type: EnumProperty(
        items=[
            ("POS", "Positive", "", 1),
            ("NEG", "Negative", "", 2)],
        name="Curve type",
        default="POS",
        description="Whether the tile has a positive or negative curvature"
    )

    curve_texture: BoolProperty(
        name="Curve Texture",
        description="WARNING! You will need to make tile 3D to see the effects. Setting this to true will make the texture follow the curve of the tile. Useful for decorative elements, borders etc.",
        default=False,
        update=update_curve_texture
    )


class MT_OT_Make_Curved_Wall_Tile(Operator, MT_Curved_Tile, MT_Tile_Generator):
    """Create a Curved Wall Tile."""

    bl_idname = "object.make_curved_wall"
    bl_label = "Curved Wall"
    bl_options = {'UNDO', 'REGISTER'}
    mt_blueprint = "CUSTOM"
    mt_type = "CURVED_WALL"

    # S Wall Props
    wall_position: EnumProperty(
        name="Wall Position",
        items=[
            ("CENTER", "Center", "Wall is in Center of base."),
            ("SIDE", "Side", "Wall is on the side of base.")],
        default="CENTER")

    floor_thickness: FloatProperty(
        name="Floor Thickness",
        default=0.0245,
        step=0.01,
        precision=4)

    floor_material: EnumProperty(
        items=create_material_enums,
        name="Floor Material")

    wall_material: EnumProperty(
        items=create_material_enums,
        name="Wall Material")

    def execute(self, context):
        """Execute the operator."""
        super().execute(context)
        if not self.refresh:
            return{'PASS_THROUGH'}

        scene = context.scene
        scene_props = scene.mt_scene_props
        base_blueprint = self.base_blueprint
        core_blueprint = self.main_part_blueprint
        base_type = 'CURVED_BASE'
        core_type = 'CURVED_WALL_CORE'
        subclasses = get_all_subclasses(MT_Tile_Generator)

        kwargs = {"tile_name": self.tile_name}
        base = spawn_prefab(context, subclasses, base_blueprint, base_type, **kwargs)

        kwargs["base_name"] = base.name
        if core_blueprint == 'NONE':
            wall_core = None
        else:
            wall_core = spawn_prefab(context, subclasses, core_blueprint, core_type, **kwargs)

        # We temporarily override tile_props.base_size to generate floor core for S-Tiles.
        # It is easier to do it this way as the PropertyGroup.copy() method produces a dict
        tile_props = context.collection.mt_tile_props

        orig_tile_size = []
        for c, v in enumerate(tile_props.tile_size):
            orig_tile_size.append(v)

        tile_props.tile_size = (
            tile_props.base_size[0],
            tile_props.base_size[1],
            scene_props.base_z + self.floor_thickness)

        if base_blueprint in {'OPENLOCK_S_WALL', 'PLAIN_S_WALL'}:
            floor_core = spawn_prefab(context, subclasses, 'PLAIN', 'CURVED_FLOOR_CORE', **kwargs)
            self.finalise_tile(context, base, wall_core, floor_core)
        else:
            self.finalise_tile(context, base, wall_core)

        tile_props.tile_size = orig_tile_size

        return {'FINISHED'}

    def init(self, context):
        super().init(context)
        tile_collection = bpy.data.collections[self.tile_name]
        tile_props = tile_collection.mt_tile_props
        tile_props.collection_type = "TILE"
        tile_props.tile_size = (self.tile_x, self.tile_y, self.tile_z)
        tile_props.base_size = (self.base_x, self.base_y, self.base_z)

    def draw(self, context):
        super().draw(context)
        layout = self.layout

        layout.label(text="Blueprints")
        layout.prop(self, 'base_blueprint')
        layout.prop(self, 'main_part_blueprint')

        layout.label(text="Materials")
        layout.prop(self, 'floor_material')
        layout.prop(self, 'wall_material')

        layout.label(text="Tile Properties")
        layout.prop(self, 'tile_z', text="Height")
        layout.prop(self, 'base_radius', text="Radius")
        layout.prop(self, 'degrees_of_arc')
        layout.prop(self, 'base_socket_side', text="Socket Side")
        layout.prop(self, 'curve_texture', text="Curve Texture")

        layout.label(text="Core Properties")
        layout.prop(self, 'tile_y', text="Width")

        if self.base_blueprint in ('OPENLOCK_S_WALL', 'PLAIN_S_WALL'):
            layout.label(text="Floor Thickness")
            layout.prop(self, 'floor_thickness', text="")

            layout.label(text="Wall Position")
            layout.prop(self, 'wall_position', text="")

        layout.label(text="Sync Proportions")
        row = layout.row()
        row.prop(self, 'y_proportionate_scale', text="Width")
        row.prop(self, 'z_proportionate_scale', text="Height")

        layout.label(text="Base Properties")
        layout.prop(self, 'base_y', text="Width")
        layout.prop(self, 'base_z', text="Height")

        layout.label(text="UV Island Margin")
        layout.prop(self, 'UV_island_margin', text="")

class MT_OT_Make_Curved_Floor_Tile(Operator, MT_Curved_Tile, MT_Tile_Generator):
    """Create a Curved Floor Tile."""

    bl_idname = "object.make_curved_floor"
    bl_label = "Curved Floor"
    bl_options = {'UNDO', 'REGISTER'}
    mt_blueprint = "CUSTOM"
    mt_type = "CURVED_FLOOR"

    floor_material: EnumProperty(
        items=create_material_enums,
        name="Floor Material")

    def execute(self, context):
        """Execute the operator."""
        super().execute(context)
        if not self.refresh:
            return{'PASS_THROUGH'}

        scene = context.scene
        base_blueprint = self.base_blueprint
        core_blueprint = self.main_part_blueprint
        base_type = 'CURVED_BASE'
        core_type = 'CURVED_FLOOR_CORE'
        subclasses = get_all_subclasses(MT_Tile_Generator)

        kwargs = {"tile_name": self.tile_name}
        base = spawn_prefab(context, subclasses, base_blueprint, base_type, **kwargs)

        kwargs["base_name"] = base.name
        if core_blueprint == 'NONE':
            preview_core = None
        else:
            preview_core = spawn_prefab(context, subclasses, core_blueprint, core_type, **kwargs)

        self.finalise_tile(context, base, preview_core)

        return {'FINISHED'}

    def init(self, context):
        super().init(context)
        tile_collection = bpy.data.collections[self.tile_name]
        tile_props = tile_collection.mt_tile_props
        tile_props.collection_type = "TILE"
        tile_props.tile_size = (self.tile_x, self.tile_y, self.tile_z)
        tile_props.base_size = (self.base_x, self.base_y, self.base_z)

    def draw(self, context):
        super().draw(context)
        layout = self.layout

        layout.label(text="Blueprints")
        layout.prop(self, 'base_blueprint')
        layout.prop(self, 'main_part_blueprint')

        layout.label(text="Materials")
        layout.prop(self, 'floor_material')

        layout.label(text="Tile Properties")
        layout.prop(self, 'tile_z', text="Height")
        layout.prop(self, 'base_radius', text="Radius")
        layout.prop(self, 'degrees_of_arc')
        layout.prop(self, 'base_socket_side', text="Socket Side")
        layout.prop(self, 'curve_texture', text="Curve Texture")

        layout.label(text="Core Properties")
        layout.prop(self, 'tile_y', text="Width")

        layout.label(text="Sync Proportions")
        row = layout.row()
        row.prop(self, 'y_proportionate_scale', text="Width")
        row.prop(self, 'z_proportionate_scale', text="Height")

        layout.label(text="Base Properties")
        layout.prop(self, 'base_y', text="Width")
        layout.prop(self, 'base_z', text="Height")

        layout.label(text="UV Island Margin")
        layout.prop(self, 'UV_island_margin', text="")


class MT_OT_Make_Openlock_Curved_Base(MT_Tile_Generator, Operator):
    """Internal Operator. Generate an OpenLOCK curved base."""

    bl_idname = "object.make_openlock_curved_base"
    bl_label = "OpenLOCK Curved Base"
    bl_options = {'INTERNAL'}
    mt_blueprint = "OPENLOCK"
    mt_type = "CURVED_BASE"

    def execute(self, context):
        """Execute the operator."""
        tile_props = bpy.data.collections[self.tile_name].mt_tile_props
        spawn_openlock_base(self, tile_props)
        return{'FINISHED'}


class MT_OT_Make_Openlock_S_Wall_Straight_Base(MT_Tile_Generator, Operator):
    """Internal Operator. Generate an OpenLOCK S Wall curved base."""

    bl_idname = "object.make_openlock_s_wall_curved_base"
    bl_label = "OpenLOCK Curved Base"
    bl_options = {'INTERNAL'}
    mt_blueprint = "OPENLOCK_S_WALL"
    mt_type = "CURVED_BASE"

    def execute(self, context):
        """Execute the operator."""
        tile_props = bpy.data.collections[self.tile_name].mt_tile_props
        spawn_openlock_base(self, tile_props)
        return{'FINISHED'}


class MT_OT_Make_Plain_Curved_Base(MT_Tile_Generator, Operator):
    """Internal Operator. Generate a plain curved base."""

    bl_idname = "object.make_plain_curved_base"
    bl_label = "Plain Curved Base"
    bl_options = {'INTERNAL'}
    mt_blueprint = "PLAIN"
    mt_type = "CURVED_BASE"

    def execute(self, context):
        """Execute the operator."""
        tile_props = bpy.data.collections[self.tile_name].mt_tile_props
        spawn_plain_base(self, tile_props)
        return{'FINISHED'}


class MT_OT_Make_Plain_S_Wall_Curved_Base(MT_Tile_Generator, Operator):
    """Internal Operator. Generate a plain curved base."""

    bl_idname = "object.make_plain_s_wall_curved_base"
    bl_label = "Plain Curved Base"
    bl_options = {'INTERNAL'}
    mt_blueprint = "PLAIN_S_WALL"
    mt_type = "CURVED_BASE"

    def execute(self, context):
        """Execute the operator."""
        tile_props = bpy.data.collections[self.tile_name].mt_tile_props
        spawn_plain_base(self, tile_props)
        return{'FINISHED'}


class MT_OT_Make_Empty_Curved_Base(MT_Tile_Generator, Operator):
    """Internal Operator. Generate an empty curved base."""

    bl_idname = "object.make_empty_curved_base"
    bl_label = "Empty Curved Base"
    bl_options = {'INTERNAL'}
    mt_blueprint = "NONE"
    mt_type = "CURVED_BASE"

    def execute(self, context):
        """Execute the operator."""
        tile_props = bpy.data.collections[self.tile_name].mt_tile_props
        spawn_empty_base(tile_props)
        return{'FINISHED'}


class MT_OT_Make_Plain_Curved_Wall_Core(MT_Tile_Generator, Operator):
    """Internal Operator. Generate a plain curved wall core."""

    bl_idname = "object.make_plain_curved_wall_core"
    bl_label = "Curved Wall Core"
    bl_options = {'INTERNAL'}
    mt_blueprint = "PLAIN"
    mt_type = "CURVED_WALL_CORE"
    base_name: StringProperty()

    def execute(self, context):
        """Execute the operator."""
        tile_props = bpy.data.collections[self.tile_name].mt_tile_props
        spawn_plain_wall_cores(self, tile_props)
        return{'FINISHED'}


class MT_OT_Make_Openlock_Curved_Wall_Core(MT_Tile_Generator, Operator):
    """Internal Operator. Generate an openlock curved wall core."""

    bl_idname = "object.make_openlock_curved_wall_core"
    bl_label = "Curved Wall Core"
    bl_options = {'INTERNAL', 'REGISTER'}
    mt_blueprint = "OPENLOCK"
    mt_type = "CURVED_WALL_CORE"
    base_name: StringProperty()

    def execute(self, context):
        """Execute the operator."""
        tile_props = bpy.data.collections[self.tile_name].mt_tile_props
        base = bpy.data.objects[self.base_name]

        spawn_openlock_wall_cores(self, base, tile_props)
        return{'FINISHED'}


class MT_OT_Make_Empty_Curved_Wall_Core(MT_Tile_Generator, Operator):
    """Internal Operator. Generate an empty curved wall core."""

    bl_idname = "object.make_empty_curved_wall_core"
    bl_label = "Curved Wall Core"
    bl_options = {'INTERNAL'}
    mt_blueprint = "NONE"
    mt_type = "CURVED_WALL_CORE"

    def execute(self, context):
        """Execute the operator."""
        return {'PASS_THROUGH'}


class MT_OT_Make_Plain_Curved_Floor_Core(MT_Tile_Generator, Operator):
    """Internal Operator. Generate a plain curved wall core."""

    bl_idname = "object.make_plain_curved_floor_core"
    bl_label = "Curved Floor Core"
    bl_options = {'INTERNAL'}
    mt_blueprint = "PLAIN"
    mt_type = "CURVED_FLOOR_CORE"
    base_name: StringProperty()

    def execute(self, context):
        """Execute the operator."""
        tile_props = bpy.data.collections[self.tile_name].mt_tile_props
        base = bpy.data.objects[self.base_name]
        spawn_plain_floor_cores(self, tile_props)
        return{'FINISHED'}


class MT_OT_Make_Openlock_Curved_Floor_Core(MT_Tile_Generator, Operator):
    """Internal Operator. Generate an openlock curved wall core."""

    bl_idname = "object.make_openlock_curved_floor_core"
    bl_label = "Curved Floor Core"
    bl_options = {'INTERNAL'}
    mt_blueprint = "OPENLOCK"
    mt_type = "CURVED_FLOOR_CORE"
    base_name: StringProperty()

    def execute(self, context):
        """Execute the operator."""
        tile_props = bpy.data.collections[self.tile_name].mt_tile_props
        base = bpy.data.objects[self.base_name]
        spawn_plain_floor_cores(self, tile_props)
        return{'FINISHED'}


class MT_OT_Make_Empty_Curved_Floor_Core(MT_Tile_Generator, Operator):
    """Internal Operator. Generate an empty curved wall core."""

    bl_idname = "object.make_empty_curved_floor_core"
    bl_label = "Curved Floor Core"
    bl_options = {'INTERNAL'}
    mt_blueprint = "NONE"
    mt_type = "CURVED_FLOOR_CORE"

    def execute(self, context):
        """Execute the operator."""
        return {'PASS_THROUGH'}


def spawn_plain_wall_cores(self, tile_props):
    """Spawn plain wall cores into scene.

    Args:
        base (bpy.types.Object): tile base
        tile_props (MakeTile.properties.MT_Tile_Properties): tile properties

    Returns:
        (bpy.types.Object): core
    """
    offset = (tile_props.base_size[1] - tile_props.tile_size[1]) / 2
    tile_props.core_radius = tile_props.base_radius + offset
    textured_vertex_groups = ['Front', 'Back']
    core = spawn_wall_core(self, tile_props)
    material = tile_props.wall_material
    subsurf = add_subsurf_modifier(core)
    convert_to_displacement_core(
        core,
        textured_vertex_groups,
        material,
        subsurf)

    return core


def spawn_openlock_wall_cores(self, base, tile_props):
    """Spawn OpenLOCK wall cores into scene.

    Args:
        base (bpy.types.Object): tile base
        tile_props (MakeTile.properties.MT_Tile_Properties): tile properties

    Returns:
        (bpy.types.Object): preview_core
    """
    offset = (tile_props.base_size[1] - tile_props.tile_size[1]) / 2
    tile_props.core_radius = tile_props.base_radius + offset

    core = spawn_wall_core(self, tile_props)
    subsurf = add_subsurf_modifier(core)
    cutters = spawn_openlock_wall_cutters(
        core,
        base.location,
        tile_props)

    kwargs = {
        "tile_props": tile_props}

    top_peg = spawn_openlock_top_pegs(
        base,
        **kwargs)

    set_bool_obj_props(top_peg, base, tile_props, 'UNION')
    set_bool_props(top_peg, core, 'UNION')

    for cutter in cutters:
        set_bool_obj_props(cutter, base, tile_props, 'DIFFERENCE')
        set_bool_props(cutter, core, 'DIFFERENCE')

    textured_vertex_groups = ['Front', 'Back']
    material = tile_props.wall_material
    convert_to_displacement_core(
        core,
        textured_vertex_groups,
        material,
        subsurf)

    activate(core.name)

    return core


def spawn_openlock_top_pegs(base, **kwargs):
    """Spawn top peg(s) for stacking wall tiles and position it.

    Args:
        base (bpy.types.Object): tile base
        tile_props (MakeTile.properties.MT_Tile_Properties): tile properties

    Returns:
        bpy.types.Object: top peg(s)
    """
    tile_props = kwargs['tile_props']

    base_size = tile_props.base_size
    tile_size = tile_props.tile_size
    base_radius = tile_props.base_radius
    peg = load_openlock_top_peg(tile_props)

    array_mod = peg.modifiers.new('Array', 'ARRAY')
    array_mod.use_relative_offset = False
    array_mod.use_constant_offset = True
    array_mod.constant_offset_displace[0] = 0.505
    array_mod.fit_type = 'FIXED_COUNT'
    array_mod.count = 2

    base_location = base.location.copy()

    if tile_props.wall_position == 'CENTER':
        if base_radius >= 1:
            if tile_props.base_socket_side == 'INNER':
                peg.location = (
                    base_location[0] - 0.25,
                    base_location[1] + base_radius + (base_size[1] / 2) + 0.075,
                    base_location[2] + tile_size[2])
            else:
                peg.location = (
                    base_location[0] - 0.25,
                    base_location[1] + base_radius + (base_size[1] / 2) - 0.075,
                    base_location[2] + tile_size[2])

    elif tile_props.wall_position == 'SIDE':
        if base_radius >= 1:
            if tile_props.base_socket_side == 'INNER':
                peg.location = (
                    base_location[0] - 0.25,
                    base_location[1] + base_radius + base_size[1] - 0.33,
                    base_location[2] + tile_size[2])
            else:
                peg.location = (
                    base_location[0] - 0.25,
                    base_location[1] + base_radius + base_size[1] - 0.33,
                    base_location[2] + tile_size[2])
    ctx = {
        'object': peg,
        'active_object': peg,
        'selected_objects': [peg],
        'selected_editable_objects': [peg]
    }

    bpy.ops.transform.rotate(
        ctx,
        value=radians(tile_props.degrees_of_arc / 2) * 1,
        orient_axis='Z',
        orient_type='GLOBAL',
        orient_matrix_type='GLOBAL',
        orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)),
        center_override=base_location)

    return peg


def spawn_openlock_wall_cutters(core, base_location, tile_props):
    """Spawn OpenLOCK wall cutters into scene and position them.

    Args:
        core (bpy.types.Object): tile core
        base_location (Vector[3]): base location
        tile_props (MakeTile.properties.MT_Tile_Properties): tile properties

    Returns:
        list[bpy.types.Objects]: cutters
    """
    deselect_all()

    tile_name = tile_props.tile_name

    preferences = get_prefs()
    booleans_path = os.path.join(
        preferences.assets_path,
        "meshes",
        "booleans",
        "openlock.blend")

    # load side cutter
    with bpy.data.libraries.load(booleans_path) as (data_from, data_to):
        data_to.objects = ['openlock.wall.cutter.side']

    core_location = core.location.copy()

    cutters = []

    # left side cutters
    left_cutter_bottom = data_to.objects[0].copy()
    left_cutter_bottom.name = 'X Neg Bottom.' + tile_name

    add_object_to_collection(left_cutter_bottom, tile_props.tile_name)

    # move cutter to origin up by 0.63 inches - base height
    left_cutter_bottom.location = (
        core_location[0],
        core_location[1] + (tile_props.tile_size[1] / 2),
        core_location[2] + 0.63 - tile_props.base_size[2])
    if tile_props.wall_position == 'SIDE':
        left_cutter_bottom.location = (
            left_cutter_bottom.location[0],
            left_cutter_bottom.location[1] + (tile_props.base_size[1] / 2) - (tile_props.tile_size[1] / 2) - 0.09,
            left_cutter_bottom.location[2])

    # add array mod
    array_mod = left_cutter_bottom.modifiers.new('Array', 'ARRAY')
    array_mod.use_relative_offset = False
    array_mod.use_constant_offset = True
    array_mod.constant_offset_displace = [0, 0, 2]
    array_mod.fit_type = 'FIT_LENGTH'
    array_mod.fit_length = tile_props.tile_size[2] - 1

    # make a copy of left cutter bottom
    left_cutter_top = left_cutter_bottom.copy()
    add_object_to_collection(left_cutter_top, tile_props.tile_name)
    left_cutter_top.name = 'X Neg Top.' + tile_name

    # move cutter up by 0.75 inches
    left_cutter_top.location[2] = left_cutter_top.location[2] + 0.75

    # modify array
    array_mod = left_cutter_top.modifiers[array_mod.name]
    array_mod.fit_length = tile_props.tile_size[2] - 1.8

    cutters.extend([left_cutter_bottom, left_cutter_top])

    # right side cutters
    right_cutter_bottom = left_cutter_bottom.copy()
    right_cutter_bottom.rotation_euler[2] = radians(180)
    add_object_to_collection(right_cutter_bottom, tile_props.tile_name)

    right_cutter_bottom.name = 'X Pos Bottom.' + tile_name
    circle_center = base_location
    select(right_cutter_bottom.name)
    activate(right_cutter_bottom.name)

    bpy.ops.transform.rotate(
        value=radians(tile_props.degrees_of_arc) * 1,
        orient_axis='Z',
        orient_type='GLOBAL',
        center_override=circle_center)

    right_cutter_top = right_cutter_bottom.copy()
    add_object_to_collection(right_cutter_top, tile_props.tile_name)
    right_cutter_top.name = 'X Pos Top.' + tile_name

    right_cutter_top.location[2] = right_cutter_top.location[2] + 0.75
    # modify array
    array_mod = right_cutter_top.modifiers[array_mod.name]
    array_mod.fit_length = tile_props.tile_size[2] - 1.8

    cutters.extend([right_cutter_bottom, right_cutter_top])

    return cutters


def spawn_plain_base(self, tile_props):
    """Spawn a plain base into the scene.

    Args:
        tile_props (MakeTile.properties.MT_Tile_Properties): tile properties

    Returns:
        bpy.types.Object: tile base
    """
    radius = tile_props.base_radius
    deg = tile_props.degrees_of_arc
    height = tile_props.base_size[2]
    width = tile_props.base_size[1]
    arc = (deg / 360) * (2 * pi) * radius
    subdivs = get_subdivs(tile_props.subdivision_density, [arc, width, height])

    base = draw_curved_cuboid(
        tile_props.tile_name + '.base',
        radius,
        subdivs[0],
        deg,
        height,
        width)

    obj_props = base.mt_object_props
    obj_props.is_mt_object = True
    obj_props.geometry_type = 'BASE'
    obj_props.tile_name = tile_props.tile_name
    bpy.context.view_layer.objects.active = base

    return base


def spawn_openlock_base_slot_cutter(self, base, tile_props, offset=0.236):
    """Spawns an openlock base slot cutter into the scene and positions it correctly

    Args:
        base (bpy.types.Object): base
        tile_props (MakeTile.properties.MT_Tile_Properties): tile properties
        offset (float, optional): Offset from base end along x. Defaults to 0.236.

    Returns:
        bpy.types.Object: slot cutter
    """
    clip_side = tile_props.base_socket_side
    base_radius = tile_props.base_radius
    base_degrees = tile_props.degrees_of_arc

    cutter_w = 0.181
    cutter_h = 0.24

    if clip_side == 'INNER':
        cutter_radius = base_radius + 0.25
    else:
        cutter_radius = base_radius + tile_props.base_size[1] - 0.18 - 0.25

    bool_overlap = 0.001  # overlap amount to prevent errors

    cutter_inner_arc_len = (2 * pi * cutter_radius) / (360 / base_degrees) - (offset * 2)
    central_angle = degrees(cutter_inner_arc_len / cutter_radius)

    subdivs = get_subdivs(tile_props.subdivision_density, [cutter_inner_arc_len, cutter_w, cutter_h])

    slot_cutter = draw_curved_cuboid(
        'Slot.' + tile_props.tile_name,
        cutter_radius,
        subdivs[0],
        central_angle,
        cutter_h + bool_overlap,
        cutter_w
    )

    slot_cutter.location[2] = slot_cutter.location[2] - bool_overlap
    slot_cutter.rotation_euler[2] = slot_cutter.rotation_euler[2] - radians((base_degrees - central_angle) / 2)

    ctx = {
        'object': slot_cutter,
        'active_object': slot_cutter,
        'selected_editable_objects': [slot_cutter],
        'selected_objects': [slot_cutter]
    }

    base.select_set(False)
    bpy.ops.object.origin_set(ctx, type='ORIGIN_CURSOR', center='MEDIAN')

    return slot_cutter


def spawn_openlock_base(self, tile_props):
    """Spawn OpenLOCK base into scene.

    Args:
        tile_props (MakeTile.properties.MT_Tile_Properties): tile properties

    Returns:
        bpy.types.Object: base
    """
    radius = tile_props.base_radius
    deg = tile_props.degrees_of_arc
    height = tile_props.base_size[2]
    width = tile_props.base_size[1]
    arc = (deg / 360) * (2 * pi) * radius
    subdivs = get_subdivs(tile_props.subdivision_density, [arc, width, height])
    base = draw_curved_cuboid(
        tile_props.tile_name + '.base',
        radius,
        subdivs[0],
        deg,
        height,
        width)

    slot_cutter = spawn_openlock_base_slot_cutter(self, base, tile_props)
    set_bool_obj_props(slot_cutter, base, tile_props, 'DIFFERENCE')
    set_bool_props(slot_cutter, base, 'DIFFERENCE')

    base.name = tile_props.tile_name + '.base'
    obj_props = base.mt_object_props
    obj_props.is_mt_object = True
    obj_props.geometry_type = 'BASE'
    obj_props.tile_name = tile_props.tile_name

    spawn_openlock_base_clip_cutter(base, tile_props)

    bpy.context.view_layer.objects.active = base

    return base


def spawn_openlock_base_clip_cutter(base, tile_props):
    """Spawn base clip cutter into scene.

    Args:
        base (bpy.types.Object): tile base
        tile_props (MakeTile.properties.MT_Tile_Properties): tile properties

    Returns:
        bpy.types.Object: base clip cutter
    """
    scene = bpy.context.scene
    cursor_orig_loc = scene.cursor.location.copy()
    clip_side = tile_props.base_socket_side

    # load base cutter
    preferences = get_prefs()
    booleans_path = os.path.join(
        preferences.assets_path,
        "meshes",
        "booleans",
        "openlock.blend")

    with bpy.data.libraries.load(booleans_path) as (data_from, data_to):
        data_to.objects = ['openlock.wall.base.cutter.clip_single']

    clip_cutter = data_to.objects[0]
    add_object_to_collection(clip_cutter, tile_props.tile_name)
    deselect_all()
    select(clip_cutter.name)

    if clip_side == 'INNER':
        radius = tile_props.base_radius + 0.25
    else:
        radius = tile_props.base_radius + tile_props.base_size[1] - 0.25

    clip_cutter.location[1] = radius


    if clip_side == 'OUTER':
        clip_cutter.rotation_euler[2] = radians(180)

    num_cutters = modf((tile_props.degrees_of_arc - 22.5) / 22.5)
    circle_center = cursor_orig_loc

    if num_cutters[1] == 1:
        initial_rot = (tile_props.degrees_of_arc / 2)

    else:
        initial_rot = 22.5

    bpy.ops.transform.rotate(
        value=radians(initial_rot) * 1,
        orient_axis='Z',
        center_override=circle_center)

    bpy.ops.object.transform_apply(
        location=False,
        scale=False,
        rotation=True,
        properties=False)

    array_name, empty = add_circle_array(
        clip_cutter,
        tile_props.tile_name,
        circle_center,
        num_cutters[1],
        'Z',
        22.5 * -1)

    empty.parent = base

    #empty.hide_set(True)
    empty.hide_viewport = True
    clip_cutter.name = 'Clip.' + base.name
    set_bool_obj_props(clip_cutter, base, tile_props, 'DIFFERENCE')
    set_bool_props(clip_cutter, base, 'DIFFERENCE')

    return clip_cutter


def spawn_plain_floor_cores(self, tile_props):
    """Spawn preview and displacement cores into scene.

    Args:
        tile_props (MakeTile.properties.MT_Tile_Properties): tile properties

    Returns:
        bpy.types.Object: preview core
    """
    textured_vertex_groups = ['Top']
    tile_props.core_radius = tile_props.base_radius
    core = spawn_floor_core(self, tile_props)
    material = tile_props.floor_material
    subsurf = add_subsurf_modifier(core)
    convert_to_displacement_core(
        core,
        textured_vertex_groups,
        material,
        subsurf)

    return core


def spawn_floor_core(self, tile_props):
    """Spawn core into scene.

    Args:
        tile_props (MakeTile.properties.MT_Tile_Properties): tile properties

    Returns:
        bpy.types.Object: core
    """
    angle = tile_props.degrees_of_arc
    radius = tile_props.core_radius
    width = tile_props.tile_size[1]
    height = tile_props.tile_size[2] - tile_props.base_size[2]
    inner_circumference = 2 * pi * radius
    floor_length = inner_circumference / (360 / angle)
    tile_name = tile_props.tile_name
    arc = (angle / 360) * (2 * pi) * radius
    native_subdivisions = get_subdivs(tile_props.subdivision_density, [arc, width, height])

    # Rather than creating our cores as curved objects we create them as straight cuboids
    # and then add a deform modifier. This allows us to not use the modifier when baking the
    # displacement texture by disabling it in render and thus being able to use
    # standard projections

    core = draw_rectangular_floor_core(
        (floor_length,
         width,
         height),
        native_subdivisions)

    core.name = tile_name + '.core'
    add_object_to_collection(core, tile_props.tile_name)

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

    tile_props.tile_size[0] = floor_length

    core.location = (
        core.location[0],
        core.location[1] + radius,
        core.location[2] + tile_props.base_size[2])

    mod = core.modifiers.new('Simple_Deform', type='SIMPLE_DEFORM')
    mod.deform_method = 'BEND'
    mod.deform_axis = 'Z'
    mod.angle = radians(-angle)

    scene_props = bpy.context.scene.mt_scene_props

    # this controls whether the texture follows the curvature of the tile on render.
    # Useful for decorative elements.
    if scene_props.curve_texture:
        mod.show_render = False

    core.name = tile_props.tile_name + '.floor_core'

    obj_props = core.mt_object_props
    obj_props.is_mt_object = True
    obj_props.tile_name = tile_props.tile_name

    return core


def spawn_wall_core(self, tile_props):
    """Spawn core into scene.

    Args:
        tile_props (MakeTile.properties.MT_Tile_Properties): tile properties

    Returns:
        bpy.types.Object: core
    """
    angle = tile_props.degrees_of_arc
    radius = tile_props.core_radius
    width = tile_props.tile_size[1]
    height = tile_props.tile_size[2] - tile_props.base_size[2]
    inner_circumference = 2 * pi * radius
    wall_length = inner_circumference / (360 / angle)
    tile_name = tile_props.tile_name
    arc = (angle / 360) * (2 * pi) * radius
    native_subdivisions = get_subdivs(tile_props.subdivision_density, [arc, width, height])


    # Rather than creating our cores as curved objects we create them as straight cuboids
    # and then add a deform modifier. This allows us to not use the modifier when baking the
    # displacement texture by disabling it in render and thus being able to use
    # standard projections

    core = draw_straight_wall_core(
        (wall_length,
         width,
         height),
        native_subdivisions)

    core.name = tile_name + '.core'
    add_object_to_collection(core, tile_props.tile_name)

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

    tile_props.tile_size[0] = wall_length

    core.location = (
        core.location[0],
        core.location[1] + radius,
        core.location[2] + tile_props.base_size[2])

    if tile_props.wall_position == 'SIDE':
        cursor = bpy.context.scene.cursor
        orig_cursor_loc = cursor.location.copy()
        cursor.location = core.location
        core.location = (
            core.location[0],
            core.location[1] + (tile_props.base_size[1] / 2) - (tile_props.tile_size[1] / 2) - 0.09,
            core.location[2])


        bpy.ops.object.origin_set(ctx, type='ORIGIN_CURSOR', center='MEDIAN')
        cursor.location = orig_cursor_loc

    mod = core.modifiers.new('Simple_Deform', type='SIMPLE_DEFORM')
    mod.deform_method = 'BEND'
    mod.deform_axis = 'Z'
    mod.angle = radians(-angle)
    mod.show_render = False
    core.name = tile_props.tile_name + '.wall_core'

    obj_props = core.mt_object_props
    obj_props.is_mt_object = True
    obj_props.tile_name = tile_props.tile_name

    return core
