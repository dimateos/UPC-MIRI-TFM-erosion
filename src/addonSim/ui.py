import bpy
import bpy.types as types
from mathutils import Vector, Matrix

from .properties import (
    MW_gen_cfg,
)

from .utils_cfg import getProps_names
from .utils_dev import DEV


#-------------------------------------------------------------------

def draw_toggleBox(metadata, propToggle_name:str, layout: types.UILayout) -> tuple[bool, types.UILayout]:
    """ Create a box with a toggle. Return the state of the toggle and the created layout """
    box = layout.box()
    box.prop(metadata, propToggle_name, toggle=True, icon="DOWNARROW_HLT")
    open = getattr(metadata, propToggle_name)
    return open, box

def draw_props(data, propFilter:str, layout: types.UILayout):
    """ Draw all properties of an object in a sub layout. """
    # dynamic filter prop
    prop_names = getProps_names(data)
    if propFilter:
        excluding = propFilter[0]=="-"
        if excluding: propFilter = propFilter[1:]
        filtered_props = propFilter.split(",")
    else:
        filtered_props = []

    for prop_name in prop_names:
        # apply excluding/including filter
        if filtered_props:
            filterMask = [ f.strip().lower() in prop_name.strip().lower() for f in filtered_props ]
            if excluding:
                if any(filterMask): continue
            elif not any(filterMask): continue

        layout.row().prop(data, prop_name, text=prop_name)

def draw_propsToggle(data, metadata, propToggle_name:str, propFilter_name:str, propEdit_name:str, layout: types.UILayout):
    """ Draw all properties of an object under a toggleable layout. """
    open, box = draw_toggleBox(metadata, propToggle_name, layout)
    if open:
        split = box.split(factor=0.75)
        split.prop(metadata, propFilter_name)
        split.prop(metadata, propEdit_name)
        col = box.column()
        col.enabled = getattr(metadata, propEdit_name)
        propFilter = getattr(metadata, propFilter_name)
        draw_props(data, propFilter, col)

#-------------------------------------------------------------------

def draw_refresh(data, layout: types.UILayout):
    row = layout.box().row()
    row.scale_y = 1.5
    split = row.split(factor=0.75)
    split.prop(data, "meta_auto_refresh", toggle=True, icon_only=False, icon='FILE_REFRESH')
    split.prop(data, "meta_refresh", toggle=True, icon_only=True, icon='FILE_REFRESH')

def draw_inspectObject(obj: types.Object, layout: types.UILayout, drawTrans=True) -> types.UILayout:
    mainBox = layout.box()
    mainCol = mainBox.column()
    mainCol.label(text="Object: " + obj.name),
    mainCol.scale_y = 0.8

    # OPT:: maybe for vertices too, not just whole objects
    box = mainCol.box()
    col = box.column()
    col.label(text="Type: " + obj.type, icon="MESH_DATA")
    if obj.type == "MESH":
        mesh: types.Mesh = obj.data
        col.label(text=f"V: {len(mesh.vertices)}   E: {len(mesh.edges)}   F: {len(mesh.polygons)}   T: {len(mesh.loop_triangles)}")

    if drawTrans:
        # shared decimal format
        fmt = ">6.3f"
        fmt_vec = f"({{:{fmt}}}, {{:{fmt}}}, {{:{fmt}}})"
        from math import degrees

        # group world
        box = mainCol.box()
        col = box.column()
        col.label(text="World transform")

        matrix: Matrix = obj.matrix_world
        pos = matrix.to_translation()
        col.label(text=f"pos: {fmt_vec}".format(*pos))
        rot = matrix.to_euler()
        rot_deg = tuple(degrees(r) for r in rot)
        col.label(text=f"rot:  {fmt_vec}".format(*rot_deg))
        sca = matrix.to_scale()
        col.label(text=f"sca: {fmt_vec}".format(*sca))

        # group local
        box = col.box()
        col = box.column()
        col.label(text="Local transform")

        matrix: Matrix = obj.matrix_basis
        pos = matrix.to_translation()
        col.label(text=f"pos: {fmt_vec}".format(*pos))
        rot = matrix.to_euler()
        rot_deg = tuple(degrees(r) for r in rot)
        col.label(text=f"rot:  {fmt_vec}".format(*rot_deg))
        sca = matrix.to_scale()
        col.label(text=f"sca: {fmt_vec}".format(*sca))

    return mainCol, mainBox

#-------------------------------------------------------------------

def draw_gen_cfg(cfg: MW_gen_cfg, layout: types.UILayout, context: types.Context):
    box = layout.box()
    col = box.column()

    factor = 0.4
    rowsub = col.row().split(factor=factor)
    rowsub.alignment = "LEFT"
    rowsub.label(text="Point Source:")
    split = rowsub.split()
    split.enabled = False
    split.alignment = "LEFT"
    split.label(text=cfg.struct_nameOriginal)

    rowsub = col.row().split(factor=factor)
    rowsub.alignment = "LEFT"
    rowsub.prop(cfg, "struct_namePrefix")
    split = rowsub.split()
    split.enabled = False
    split.alignment = "LEFT"
    split.label(text=cfg.get_struct_name())

    rowsub = col.row()
    rowsub.prop(cfg, "source")

    rowsub = col.row()
    rowsub.prop(cfg, "source_limit")
    # IDEA:: show current num found? could do 1 frame delayed stored somewhere
    rowsub = col.row()
    rowsub.prop(cfg, "source_noise")
    rowsub.prop(cfg, "rnd_seed")

    # OPT:: limit avaialble e.g. show convex when available
    box = layout.box()
    col = box.column()
    col.label(text="Generation:")
    rowsub = col.row(align=True)
    rowsub.prop(cfg, "shape_useConvexHull")
    rowsub.prop(cfg, "shape_useWalls")
    rowsub = col.row(align=True)
    rowsub.prop(cfg, "margin_box_bounds")
    rowsub.prop(cfg, "margin_face_bounds")


    box = layout.box()
    col = box.column()
    col.label(text="Links:")
    rowsub = col.row(align=True)
    rowsub.prop(cfg, "links_width")
    rowsub.prop(cfg, "links_res")

    draw_gen_cfgDebug(cfg, layout)

def draw_gen_cfgDebug(cfg: MW_gen_cfg, layout: types.UILayout):
    # OPT:: not all debug etc... sensible ui in the end

    # Careful with circular deps
    from .preferences import getPrefs
    prefs = getPrefs()

    open, box = draw_toggleBox(prefs, "PT_gen_show_tmpDebug", layout)
    if open:
        col = box.column()
        col.label(text="Show:")
        rowsub = col.row(align=True)
        rowsub.prop(cfg, "struct_showShards")
        rowsub.prop(cfg, "struct_showLinks")
        rowsub.prop(cfg, "struct_showLinks_walls")

        rowsub = col.row(align=True)
        rowsub.prop(cfg, "struct_showPoints")
        rowsub.prop(cfg, "struct_showBB")
        rowsub.prop(cfg, "struct_showOrignal_scene")

        rowsub = col.row(align=True)
        rowsub.prop(cfg, "struct_showOrignal")
        rowsub.prop(cfg, "struct_showConvex")
        rowsub.prop(cfg, "struct_showLow")