from math import tan, radians
import bpy
from ... utils.selection import select_by_loc
from ... utils.utils import mode


def draw_corner_wall(triangles, angle, thickness, wall_height, base_height, inc_vert_locs=True):
    '''Returns a corner wall and optionally locations of bottom verts'''
    vert_locs = draw_corner_2D(triangles, angle, thickness)
    mode('EDIT')
    t = bpy.ops.turtle
    t.select_all()
    t.pd()
    t.up(d=0.001)
    t.up(d=wall_height - base_height - 0.011)
    t.up(d=0.01)
    t.select_all()

    bpy.ops.mesh.normals_make_consistent()

    t.pu()
    t.deselect_all()
    t.home()
    t.set_position(v=(0, 0, 0))

    mode('OBJECT')
    obj = bpy.context.object

    if inc_vert_locs is False:
        return obj
    else:
        return obj, vert_locs


def draw_corner_3D(triangles, angle, thickness, height, inc_vert_locs=False):
    '''Returns a 3D corner piece and optionally locations of bottom verts'''
    vert_loc = draw_corner_2D(triangles, angle, thickness)

    mode('EDIT')
    t = bpy.ops.turtle
    t.select_all()
    t.pd()
    t.up(d=height)
    t.select_all()
    bpy.ops.mesh.normals_make_consistent()
    t.pu()
    t.deselect_all()
    t.home()
    t.set_position(v=(0, 0, 0))

    mode('OBJECT')
    obj = bpy.context.object

    if inc_vert_locs is False:
        return obj
    else:
        return obj, vert_loc


def draw_corner_2D(triangles, angle, thickness):
    '''Draws a 2D corner mesh in which is an "L" shape when the base angle is 90
    and returns a dict containing the location of the verts for making vert
    groups later.'''
    mode('OBJECT')

    turtle = bpy.context.scene.cursor
    orig_loc = turtle.location.copy()
    orig_rot = turtle.rotation_euler.copy()
    t = bpy.ops.turtle
    t.add_turtle()

    # We save the location of each vertex as it is drawn
    # to use for making vert groups & positioning cutters
    vert_loc = {
        'origin': orig_loc
    }
    t.pd()
    # draw X leg
    t.rt(d=angle)
    t.fd(d=triangles['a_adj'] - 0.001)
    vert_loc['x_outer_1'] = turtle.location.copy()
    t.fd(d=0.001)
    vert_loc['x_outer_2'] = turtle.location.copy()
    t.lt(d=90)
    t.fd(d=0.001)
    vert_loc['end_1_1'] = turtle.location.copy()
    t.fd(d=thickness - 0.002)
    vert_loc['end_1_2'] = turtle.location.copy()
    t.fd(d=0.001)
    vert_loc['end_1_3'] = turtle.location.copy()
    t.lt(d=90)
    t.fd(d=0.001)
    vert_loc['x_inner_1'] = turtle.location.copy()
    t.fd(d=triangles['b_adj'] - 0.001)
    vert_loc['x_inner_2'] = turtle.location.copy()
    # home
    t.pu()
    turtle.location = orig_loc
    turtle.rotation_euler = orig_rot

    t.deselect_all()
    t.select_at_cursor(buffer=0.0001)
    t.pd()  # vert loc same as a

    # draw Y leg
    t.fd(d=triangles['c_adj'] - 0.001)
    vert_loc['y_outer_1'] = turtle.location.copy()
    t.fd(d=0.001)
    vert_loc['y_outer_2'] = turtle.location.copy()
    t.rt(d=90)

    t.fd(d=0.001)
    vert_loc['end_2_1'] = turtle.location.copy()

    t.fd(d=thickness - 0.002)
    vert_loc['end_2_2'] = turtle.location.copy()
    t.fd(d=0.001)
    vert_loc['end_2_3'] = turtle.location.copy()
    t.rt(d=90)
    t.fd(d=0.001)
    vert_loc['y_inner_1'] = turtle.location.copy()
    t.fd(d=triangles['d_adj'] - 0.001)  # vert loc same as x_inner_2

    t.select_all()
    t.merge()
    t.pu()
    turtle.location = orig_loc
    turtle.rotation_euler = orig_rot
    bpy.ops.mesh.edge_face_add()
    t.deselect_all()

    select_by_loc(
        lbound=vert_loc['origin'],
        ubound=vert_loc['origin'],
        buffer=0.0001)

    select_by_loc(
        lbound=vert_loc['x_inner_2'],
        ubound=vert_loc['x_inner_2'],
        buffer=0.0001,
        additive=True)

    bpy.ops.mesh.vert_connect_path()

    select_by_loc(
        lbound=vert_loc['y_inner_1'],
        ubound=vert_loc['y_inner_1'],
        buffer=0.0001
    )
    select_by_loc(
        lbound=vert_loc['y_outer_1'],
        ubound=vert_loc['y_outer_1'],
        buffer=0.0001,
        additive=True
    )

    bpy.ops.mesh.vert_connect_path()

    select_by_loc(
        lbound=vert_loc['x_inner_1'],
        ubound=vert_loc['x_inner_1'],
        buffer=0.0001)

    select_by_loc(
        lbound=vert_loc['x_outer_1'],
        ubound=vert_loc['x_outer_1'],
        buffer=0.0001,
        additive=True)

    bpy.ops.mesh.vert_connect_path()

    mode('OBJECT')

    return vert_loc

def calculate_corner_wall_triangles(
        leg_1_len,
        leg_2_len,
        thickness,
        angle):
    # X leg
    # right triangle
    tri_a_angle = angle / 2
    tri_a_adj = leg_1_len
    tri_a_opp = tri_a_adj * tan(radians(tri_a_angle))

    # right triangle
    tri_b_angle = 180 - tri_a_angle - 90
    tri_b_opp = tri_a_opp - thickness
    tri_b_adj = tri_b_opp * tan(radians(tri_b_angle))

    # Y leg
    # right triangle
    tri_c_angle = angle / 2
    tri_c_adj = leg_2_len
    tri_c_opp = tri_c_adj * tan(radians(tri_c_angle))

    tri_d_angle = 180 - tri_c_angle - 90
    tri_d_opp = tri_c_opp - thickness
    tri_d_adj = tri_d_opp * tan(radians(tri_d_angle))

    triangles = {
        'a_adj': tri_a_adj,  # leg 1 outer leg length
        'b_adj': tri_b_adj,  # leg 1 inner leg length
        'c_adj': tri_c_adj,  # leg 2 outer leg length
        'd_adj': tri_d_adj}  # leg 2 inner leg length

    return triangles


def move_cursor_to_wall_start(triangles, angle, thickness, base_height):
    turtle = bpy.context.scene.cursor
    t = bpy.ops.turtle
    t.add_turtle()
    orig_rot = turtle.rotation_euler.copy()
    t.pu()
    t.up(d=base_height, m=True)
    t.rt(d=angle)
    t.fd(d=triangles['a_adj'])
    t.lt(d=90)
    t.fd(d=thickness)
    t.lt(d=90)
    t.fd(d=triangles['b_adj'])
    turtle.rotation_euler = orig_rot
