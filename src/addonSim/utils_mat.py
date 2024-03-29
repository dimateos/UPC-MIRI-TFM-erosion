import bpy
import bpy.types as types
from mathutils import Vector, Matrix
from random import uniform
import numpy as np

from . import utils, utils_scene
from .utils_dev import DEV

#-------------------------------------------------------------------

class COLORS:
    """ Common colors and generators, using vec4 with alpha"""
    _default_alpha = 1.0
    _default_precision = 1

    @staticmethod
    def with_alpha(c: Vector, alpha = _default_alpha):
        """ Limit color precision (alpha too or not), returns a new vector (expects alpha) """
        cc = c.copy()
        cc[3] = alpha
        return cc

    @staticmethod
    def from_256(c):
        c.xyz *= 1.0 / 256.0
        return c # return in case of used before assigment

    @staticmethod
    def rounded(c: Vector, precision=_default_precision, alphaToo = False):
        """ Limit color precision (alpha too or not), returns a new vector (expects alpha) """
        cc = Vector().to_4d()
        cc[0] = round(c[0], precision)
        cc[1] = round(c[1], precision)
        cc[2] = round(c[2], precision)
        cc[3] = round(c[3], precision) if alphaToo else c[3]
        return cc

    @staticmethod
    def clamp(c: Vector, min=0, max=1):
        """ Clapm color values, returns a new vector (expects alpha) """
        cc = Vector().to_4d()
        cc[0] = utils.clamp(c[0], min, max)
        cc[1] = utils.clamp(c[1], min, max)
        cc[2] = utils.clamp(c[2], min, max)
        cc[3] = utils.clamp(c[3], min, max)
        return cc

    red      = Vector([1.0, 0.0, 0.0, _default_alpha])
    green    = Vector([0.0, 1.0, 0.0, _default_alpha])
    blue     = Vector([0.0, 0.0, 1.0, _default_alpha])
    list_rgb = [red, green, blue]

    yellow    = clamp(red+green)
    pink      = clamp(red+blue)
    cyan      = clamp(green+blue)
    orange    = (red+yellow) * 0.5
    list_fade = [red, orange, yellow, green, cyan, blue, pink]

    black     = Vector([0.0, 0.0, 0.0, _default_alpha])
    white     = Vector([1.0, 1.0, 1.0, _default_alpha])
    gray      = (white+black) * 0.5
    list_gray = [black, gray, white]

    #cool     = from_256(Vector([97, 130, 234,  _default_alpha])) # Lyon
    #white_cw = from_256(Vector([221, 221, 221, _default_alpha]))
    #warm     = from_256(Vector([220, 94, 75,   _default_alpha]))
    cool     = from_256(Vector([69, 81, 192,   _default_alpha])) # matplot mod
    white_cw = from_256(Vector([210, 210, 210, _default_alpha]))
    warm     = from_256(Vector([163, 81, 44,   _default_alpha]))

    sky      = from_256(Vector([78, 146, 255,  _default_alpha]))
    dark     = with_alpha(white*0.33, _default_alpha)

    @staticmethod
    def get_random(minC=0.0, maxC=1.0, alpha=_default_alpha) -> Vector:
        c = Vector( [uniform(minC,maxC), uniform(minC,maxC), uniform(minC,maxC), alpha] )
        return c

    @staticmethod
    def get_ramp(start = 0.1, stop = 0.9, step = 0.2, alpha=_default_alpha) -> list[Vector]:
        """ List of colors lerping all RGB """
        startV = Vector( [start]*3 )
        stepV = Vector( [step]*3 )

        colors: list[Vector] = []
        for x in range(int((stop - start) / step) + 1):
            for y in range(int((stop - start) / step) + 1):
                for z in range(int((stop - start) / step) + 1):
                    c = startV + Vector( [x,y,z] ) *stepV
                    c = c.to_4d()
                    c.w = alpha
                    colors.append(c)
        return colors

def gen_colorMat(color=COLORS.red, name="color"):
    name_mat = name+"_mat"
    mat = bpy.data.materials.new(name_mat)
    mat.use_nodes = False

    color = COLORS.rounded(color)
    mat.diffuse_color[0] = color[0]
    mat.diffuse_color[1] = color[1]
    mat.diffuse_color[2] = color[2]
    mat.diffuse_color[3] = color[3]
    return mat

def gen_randomMat(minC=0.0, maxC=1.0, alpha=COLORS._default_alpha, name="rnd"):
    color = COLORS.get_random(minC, maxC, alpha)
    name_mat = name+"_mat"
    mat = gen_colorMat(color, name_mat)
    return mat

#-------------------------------------------------------------------

class ATTRS:
    """ Common mesh attributes """
    attrs_atype = [ 'FLOAT', 'FLOAT_COLOR', 'FLOAT2', 'FLOAT_VECTOR', 'BYTE_COLOR', 'BOOLEAN', 'INT', 'INT8', 'STRING' ]
    attrs_adomain = [ 'POINT', 'CORNER', 'EDGE', 'FACE', 'CURVE' ] # INSTANCE too
    attrsColor_atype = [ "FLOAT_COLOR", "BYTE_COLOR" ]
    attrsColor_adomain = [ "POINT", "CORNER" ]

    @staticmethod
    def get_src_inDomain(mesh: types.Mesh, adomain:str):
        """ Map the str to the mesh data """
        if adomain == "POINT": return mesh.vertices
        elif adomain == "EDGE": return mesh.edges
        elif adomain == "FACE": return mesh.polygons
        elif adomain == "CORNER": return mesh.loops
        else: raise TypeError(f"{adomain} not in {ATTRS.attrs_adomain}")

    @staticmethod
    def get_value_inType(atype:str, v, alpha = COLORS._default_alpha):
        """ Get a value of the type aprox """
        if   atype == "FLOAT"       : val= v
        elif atype == "FLOAT_COLOR" : val= Vector((v,v,v, alpha))
        elif atype == "FLOAT2"      : val= Vector((v,v))
        elif atype == "FLOAT_VECTOR": val= Vector((v,v,v))
        elif atype == "BYTE_COLOR"  : val= Vector((v,v,v, alpha)) * 256
        elif atype == "BOOL"        : val= bool(v)
        elif atype == "INT"         : val= round(v)
        elif atype == "INT8"        : val= round(v * 256)
        elif atype == "STRING"      : val= str(v)
        else                        : raise TypeError(f"{atype} not in {ATTRS.attrs_atype}")
        return val

    @staticmethod
    def get_attrName_inType(atype:str):
        """ Get the attr name of the type aprox """
        if   atype == "FLOAT"       : name = "value"
        elif atype == "FLOAT_COLOR" : name = "color"
        elif atype == "FLOAT2"      : name = "vector"
        elif atype == "FLOAT_VECTOR": name = "vector"
        elif atype == "BYTE_COLOR"  : name = "color"
        elif atype == "BOOL"        : name = "value"
        elif atype == "INT"         : name = "value"
        elif atype == "INT8"        : name = "value"
        elif atype == "STRING"      : name = "value"
        else                        : raise TypeError(f"{atype} not in {ATTRS.attrs_atype}")
        return name

    @staticmethod
    def get_attrName_inData(dataAttr):
        """ Map the data type to the data access attr """
        if isinstance(dataAttr, types.MeshLoopColorLayer): return "uv"
        elif isinstance(dataAttr, types.Attribute):
            return ATTRS.get_attrName_inType(dataAttr.data_type)
        else: raise TypeError(f"{dataAttr.name} could not be mapped")

    #-------------------------------------------------------------------

    @staticmethod
    def get_rnd_inType(atype:str, minC = 0.0, maxC = 1.0, alpha = COLORS._default_alpha):
        """ Get a random value of the type aprox """
        if   atype == "FLOAT"       : rnd= uniform(minC, maxC)
        elif atype == "FLOAT_COLOR" : rnd= COLORS.get_random(minC, maxC, alpha)
        elif atype == "FLOAT2"      : rnd= Vector((uniform(minC, maxC), uniform(minC, maxC)))
        elif atype == "FLOAT_VECTOR": rnd= COLORS.get_random(minC, maxC)
        elif atype == "BYTE_COLOR"  : rnd= COLORS.get_random(minC, maxC, alpha) * 256
        elif atype == "BOOL"        : rnd= round(uniform(minC,maxC))
        elif atype == "INT"         : rnd= round(minC + uniform(0,1) * maxC)
        elif atype == "INT8"        : rnd= round(uniform(0,1) * 256)
        elif atype == "STRING"      : rnd= utils.rnd_string(maxC-minC)
        else                        : raise TypeError(f"{atype} not in {ATTRS.attrs_atype}")
        return rnd

    @staticmethod
    def get_periodic_inType(atype:str, minC = 0.0, maxC = 1.0, period_id:int = None, period = 2, alpha = COLORS._default_alpha):
        """ Get periodic value in the type (building a ramp from 0-1 in period)"""
        step = int((period_id % period) / period) + 1
        stepVal = minC + step * maxC
        val = ATTRS.get_value_inType(atype, stepVal, alpha)
        return val

    rndRep_vals = { atype: list() for atype in attrs_atype }
    rndRep_count = { atype: 0 for atype in attrs_atype }
    @staticmethod
    def get_rnd_periodic_inType(atype:str, minC = 0.0, maxC = 1.0, period = 2, alpha = COLORS._default_alpha):
        """ Get a random value of the type with certain periodicity (limit rnd values) """
        if len(ATTRS.rndRep_vals[atype]) < period:
            ATTRS.rndRep_vals[atype].append(ATTRS.get_rnd_inType(atype, minC, maxC, alpha))

        vid = ATTRS.rndRep_count[atype] % period
        rndRep = ATTRS.rndRep_vals[atype][vid]
        ATTRS.rndRep_count[atype] +=1
        return rndRep

    @staticmethod
    def get_deferred_inType(atype:str, minC = 0.0, maxC = 1.0, period_id:int = None, period = 2, alpha=COLORS._default_alpha):
        """ Proxy function to pick the random method used in other functions"""
        return ATTRS.get_rnd_inType(atype, minC, maxC, alpha)
        #return ATTRS.get_periodic_inType(atype, minC, maxC, period_id, period, alpha)
        #return ATTRS.get_rnd_periodic_inType(atype, minC, maxC, period, alpha)

#-------------------------------------------------------------------
# NOTE:: all similar functions but then access different paths in the mesh/data e.g. uv.data[i].uv,vc.data[i].color,attr.data[i].value
# NOTE:: set random functions do the same iteration to avoid allocating twice the memory in a tmp list, could change for less code dupe

def gen_meshUV(mesh: types.Mesh, uv_base:Vector|list[Vector] = None, name="UV_map", val_repeats = 1) -> types.MeshUVLoopLayer:
    """ Add a UV layer to the mesh: 2D float PER loop corner """
    uv = mesh.uv_layers.new(name=name)
    if uv_base: set_meshUV(mesh, uv, uv_base, val_repeats)
    return uv

def set_meshUV(mesh: types.Mesh, uv: types.MeshUVLoopLayer|str, uv_base:Vector|list[Vector], val_repeats = 1):
    if isinstance(uv, str): uv = mesh.uv_layers[uv]
    uv_base = utils.assure_list(uv_base)

    # input repetition options on top of periodically repeat val_base over source extent
    assert val_repeats > 0, "val_repeats must be at least 1"
    gen_repIndices = [i for i in range(len(uv_base)) for _ in range(val_repeats)]

    for i, datum in enumerate(mesh.loops):
        i_value = gen_repIndices[i % len(gen_repIndices)]
        val = uv_base[i_value]
        uv.data[i].uv = val

def set_meshUV_rnd(mesh: types.Mesh, uv: types.MeshUVLoopLayer|str, minC=0.0, maxC=1.0):
    if isinstance(uv, str): uv = mesh.uv_layers[uv]
    for i, faceL in enumerate(mesh.loops):
        uv.data[i].uv = ATTRS.get_deferred_inType("FLOAT2", minC, maxC, i)

def set_meshUV_active(mesh: types.Mesh, uv: types.MeshUVLoopLayer|str):
    if isinstance(uv, str): uv = mesh.uv_layers[uv]
    uv.active = True

def delete_meshUV(mesh: types.Mesh):
    while mesh.uv_layers:
        uv_layer = mesh.uv_layers[0]
        mesh.uv_layers.remove(uv_layer)

#-------------------------------------------------------------------

def gen_meshVC_legacy(mesh: types.Mesh, color_base:Vector|list[Vector] = None, joinFaces=True, name="VC_legacy") -> types.MeshLoopColorLayer:
    """ Add a legacy vertex color layer to the mesh: 4D float PER loop corner
        # NOTE:: internally uses the same feature as color attributes, but limited to loops
    """

    vc = mesh.vertex_colors.new(name=name)
    if color_base: set_meshVC_legacy(mesh, vc, color_base, joinFaces)
    return vc

def set_meshVC_legacy(mesh: types.Mesh, vc: types.MeshLoopColorLayer|str, color_base:Vector|list[Vector], joinFaces=True):
    if isinstance(vc, str): vc = mesh.vertex_colors[vc]
    color_base = utils.assure_list(color_base)
    if joinFaces:
        for i, face in enumerate(mesh.polygons):
            c = color_base[i % len(color_base)]
            for j, loopID in enumerate(face.loop_indices):
                vc.data[loopID].color = c
    else:
        for i, faceL in enumerate(mesh.loops):
            c = color_base[i % len(color_base)]
            vc.data[i].color = c

def set_meshVC_legacy_rnd(mesh: types.Mesh, vc: types.MeshLoopColorLayer|str, minC=0.0, maxC=1.0, alpha=1.0, joinFaces=True):
    rndValues = [ ATTRS.get_deferred_inType("FLOAT_COLOR", minC, maxC, i, alpha) for i, faceL in enumerate(mesh.loops) ]
    set_meshVC_legacy(mesh, vc, rndValues, joinFaces)

#-------------------------------------------------------------------

def gen_meshVC(mesh: types.Mesh, color_base:Vector|list[Vector] = None, joinFaces=True, atype="FLOAT_COLOR", adomain="POINT", name="VC") -> types.Attribute:
    """ Add a color layer to the mesh: 4D float PER loop corner / vertex
        # NOTE:: internally color attributes use the same structure as attributes but limited to colors and POINT/CORNER
    """
    assert atype in ATTRS.attrsColor_atype, f"{atype} not in {ATTRS.attrsColor_atype}"
    assert adomain in ATTRS.attrsColor_adomain, f"{adomain} not in {ATTRS.attrsColor_adomain}"
    vc = mesh.color_attributes.new(f"{name}_{adomain}_{atype}", atype, adomain)
    if color_base:
        if not joinFaces or adomain != "CORNER": set_meshVC(mesh, vc, color_base)
        else: set_meshAttr_perFace(mesh, vc, color_base)
    return vc

def set_meshVC(mesh: types.Mesh, vc: types.Attribute|str, color_base:Vector|list[Vector], joinFaces=True):
    if isinstance(vc, str): vc = mesh.color_attributes[vc]
    color_base = utils.assure_list(color_base)
    source = ATTRS.get_src_inDomain(mesh, vc.domain)
    for i, datum in enumerate(source):
        c = color_base[i % len(color_base)]
        vc.data[i].color = c

def set_meshVC_rnd(mesh: types.Mesh, vc: types.Attribute|str, minC=0.0, maxC=1.0, alpha=1.0, joinFaces=True):
    if isinstance(vc, str): vc = mesh.color_attributes[vc]
    source = ATTRS.get_src_inDomain(mesh, vc.domain)
    for i, datum in enumerate(source):
        vc.data[i].color = ATTRS.get_deferred_inType("FLOAT_COLOR", minC, maxC, i, alpha)

#-------------------------------------------------------------------

def gen_meshAC(mesh: types.Mesh, color_base:Vector|list[Vector] = None, atype="FLOAT_COLOR", adomain="EDGE", name="AC") -> types.Attribute:
    """ Add an attribute layer to the mesh to add color: 4D float PER loop, face, edge, vertex, etc
        # NOTE:: when using POINT/CORNER will also be added as a color_attribute
    """
    assert atype in ATTRS.attrsColor_atype, f"{atype} not in {ATTRS.attrsColor_atype}"
    assert adomain in ATTRS.attrs_adomain, f"{adomain} not in {ATTRS.attrs_adomain}"
    ac = mesh.attributes.new(f"{name}_{adomain}_{atype}", atype, adomain)
    if color_base: set_meshAC(mesh, ac, color_base)
    return ac

def set_meshAC(mesh: types.Mesh, ac: types.Attribute|str, color_base:Vector|list[Vector]):
    if isinstance(ac, str): ac = mesh.attributes[ac]
    color_base = utils.assure_list(color_base)
    source = ATTRS.get_src_inDomain(mesh, ac.domain)
    for i, datum in enumerate(source):
        c = color_base[i % len(color_base)]
        ac.data[i].color = c

def set_meshAC_rnd(mesh: types.Mesh, ac: types.Attribute|str, minC=0.0, maxC=1.0, alpha=1.0):
    if isinstance(ac, str): ac = mesh.attributes[ac]
    source = ATTRS.get_src_inDomain(mesh, ac.domain)
    for i, datum in enumerate(source):
        ac.data[i].color = ATTRS.get_deferred_inType(ac.data_type, minC, maxC, i, alpha)

#-------------------------------------------------------------------

def gen_meshAttr(mesh: types.Mesh, val_base = None, val_repeats = 1, atype="FLOAT", adomain="EDGE", name="AT") -> types.Attribute:
    """ Add a custom attribute layer to the mesh: vector, float, string, etc PER loop, face, edge, vertex, etc
        # NOTE:: when using colors and POINT/CORNER will also be added as a color_attribute PLUS the access attribute changes
    """
    assert(atype in ATTRS.attrs_atype)
    assert(adomain in ATTRS.attrs_adomain)
    attrs = mesh.attributes.new(f"{name}_{adomain}_{atype}", atype, adomain)
    if val_base: set_meshAttr(mesh, attrs, val_base, val_repeats)
    return attrs

def set_meshAttr(mesh: types.Mesh, attr: types.Attribute|str, val_base, val_repeats = 1):
    """ Set property values, either periodically repeating val_base + repeating each input in order"""
    if isinstance(attr, str): attr = mesh.attributes[attr]
    val_base = utils.assure_list(val_base)
    source = ATTRS.get_src_inDomain(mesh, attr.domain)
    # data attribute access depends on the type...
    dataAttrName = ATTRS.get_attrName_inData(attr)

    # input repetition options on top of periodically repeat val_base over source extent
    assert val_repeats > 0, "val_repeats must be at least 1"
    gen_repIndices = [i for i in range(len(val_base)) for _ in range(val_repeats)]
    for i, datum in enumerate(source):
        i_value = gen_repIndices[i % len(gen_repIndices)]
        val = val_base[i_value]
        attr.data[i].__setattr__(dataAttrName, val)

def set_meshAttr_rnd(mesh: types.Mesh, attr: types.Attribute|str, minC=0.0, maxC=1.0):
    """ Set randomized property values """
    if isinstance(attr, str): attr = mesh.attributes[attr]
    source = ATTRS.get_src_inDomain(mesh, attr.domain)
    # data attribute access depends on the type...
    dataAttrName = ATTRS.get_attrName_inData(attr)
    for i, datum in enumerate(source):
        val = ATTRS.get_deferred_inType(attr.data_type, minC, maxC, i)
        attr.data[i].__setattr__(dataAttrName, val)

def set_meshAttr_perFace(mesh: types.Mesh, dataAttr, values, val_repeats = 1):
    """ Generalized method to set a property per face to corners of a mesh.
        # NOTE:: requires acess to the data not a str to search it in the mesh
    """
    values = utils.assure_list(values)
    dataAttrName = ATTRS.get_attrName_inData(dataAttr)

    # input repetition options on top of periodically repeat val_base over source extent
    gen_repIndices = [i for i in range(len(values)) for _ in range(val_repeats)]
    assert val_repeats > 0, "val_repeats must be at least 1"
    for i, face in enumerate(mesh.polygons):
        i_value = gen_repIndices[i % len(gen_repIndices)]
        val = values[i_value]
        for j, loopID in enumerate(face.loop_indices):
            dataAttr.data[loopID].__setattr__(dataAttrName, val)

#-------------------------------------------------------------------

def gen_test_colors(obj, mesh, alpha, matName):
    """ # NOTE:: materials can also by aded to the object instead of the data? """
    obj.active_material = gen_randomMat(alpha=alpha, matName=matName)

    # test uv and if attr float 2d is mapped to UV too
    uv = gen_meshUV(mesh, [Vector([0.66, 0.66]), Vector([0.33, 0.33])])
    set_meshUV_rnd(mesh, uv.name)
    auv = gen_meshAttr(mesh, Vector([0.33,0.66]), adomain="CORNER", atype="FLOAT2", name="AUVtest")

    # test vertex colors
    vc_old = gen_meshVC_legacy(mesh, COLORS.pink)
    set_meshVC_legacy(mesh, vc_old, COLORS.list_gray)
    set_meshVC_legacy_rnd(mesh, vc_old)
    vc = gen_meshVC(mesh, COLORS.list_rgb )
    vcFace = gen_meshVC(mesh, COLORS.list_rgb, adomain="CORNER")

    # test attr color
    ac = gen_meshAC(mesh, COLORS.list_fade, adomain="CORNER", name="ACtestcolor")
    ac2 = gen_meshAC(mesh, adomain="FACE")
    ac3 = gen_meshAC(mesh, COLORS.red, adomain="EDGE")

    # test non color attr
    at = gen_meshAttr(mesh, adomain="FACE")
    set_meshAttr_rnd(mesh, at)
    atc = gen_meshAttr(mesh, COLORS.blue, adomain="CORNER", atype="FLOAT_COLOR", name="ATtestcolor")
    set_meshAttr_rnd(mesh, atc)

#-------------------------------------------------------------------

class GRADIENTS:
    _default_res = 128

    @staticmethod
    def lerp_u(p, min_val=0, max_val=_default_res):
        return (p-min_val) / max_val

    @staticmethod
    def lerp_colors(u, c1 = COLORS.black, c2=COLORS.white):
        """ Alpha is not lerped (preserved from c1), return as new vector """
        cc1 = c1.xyz*(1-u)
        cc2 = c2.xyz*u
        c = Vector(cc1+cc2)
        utils.clamp_inplace(c) # already done by blender?
        c = c.to_4d()
        c.w = c1.w
        return c

        # NOTE:: alpha is not lerped in regular viewport when coming from textures!
        cc1 = c1*(1-u)
        cc2 = c2*u
        c = cc1+cc2
        utils.clamp_inplace(c) # already done by blender?
        return c

    @staticmethod
    def lerp_colors_trio(u, c1=COLORS.warm, c2=COLORS.white_cw, c3 = COLORS.cool):
        """ Alpha is not lerped (preserved from c1), return as new vector """
        if u < 0.5:
            return GRADIENTS.lerp_colors(u / 0.5, c1, c2)
        else:
            return GRADIENTS.lerp_colors( (u-0.5) / 0.5, c2, c3)

    red          = lambda p, h: GRADIENTS.lerp_colors(GRADIENTS.lerp_u(p, max_val=h), c2=COLORS.red)
    green        = lambda p, h: GRADIENTS.lerp_colors(GRADIENTS.lerp_u(p, max_val=h), c2=COLORS.green)
    blue         = lambda p, h: GRADIENTS.lerp_colors(GRADIENTS.lerp_u(p, max_val=h), c2=COLORS.blue)
    yellow_white = lambda p, h: GRADIENTS.lerp_colors(GRADIENTS.lerp_u(p, max_val=h), c1=COLORS.yellow, c2=COLORS.white)
    blue_red     = lambda p, h: GRADIENTS.lerp_colors(GRADIENTS.lerp_u(p, max_val=h), c1=COLORS.blue, c2=COLORS.red)
    cool_warm    = lambda p, h: GRADIENTS.lerp_colors_trio(1-GRADIENTS.lerp_u(p, max_val=h))

    def lerp_common(c = COLORS.red, end = COLORS.black):
        return lambda p, h: GRADIENTS.lerp_colors(GRADIENTS.lerp_u(p, max_val=h), c2=c, c1=end)

    def chess_2D_board(x, y, w, h):
        flip = y < h * 0.5
        if x <  w * 0.5:
            return COLORS.black if not flip else COLORS.white
        else: return COLORS.white if not flip else COLORS.black

    def red_2D_green(x, y, w, h):
        c1 = GRADIENTS.lerp_colors(GRADIENTS.lerp_u(x, max_val=w), c2=COLORS.red)
        c2 =  GRADIENTS.lerp_colors(GRADIENTS.lerp_u(y, max_val=h), c2=COLORS.green)
        return c1 + c2
    def red_2D_blue(x, y, w, h):
        c1 = GRADIENTS.lerp_colors(GRADIENTS.lerp_u(x, max_val=w), c2=COLORS.red)
        c2 =  GRADIENTS.lerp_colors(GRADIENTS.lerp_u(y, max_val=h), c2=COLORS.blue)
        return c1 + c2

def gen_textureMat_DEVfix():
    DEV.FIX_IMAGES_QUEUE = False # avoid rec
    global _gen_textureMat_queue
    for args in _gen_textureMat_queue:
        gen_textureMat(**args)
    _gen_textureMat_queue.clear()
    DEV.FIX_IMAGES_QUEUE = True

_gen_textureMat_queue = []
def gen_textureMat(uv_layer:str, name:str, width=GRADIENTS._default_res, height=GRADIENTS._default_res*0.5, colorFn = GRADIENTS.red_2D_green, forceNew = False):
    """ generate a 2D image and use colorFn: x, y, w, h to define the color of each pixel
        # NOTE:: tries to shared prev image by matching name (skipped with forceNew)
    """
    if DEV.FIX_IMAGES_QUEUE:
        global _gen_textureMat_queue
        _gen_textureMat_queue.append(utils.get_kwargs())

    name_image = name+"_img"
    image = bpy.data.images.get(name_image)
    if image:
        if forceNew or DEV.FORCE_NEW_MATS:
            image = utils_scene.delete_data(image)

    if image is None:
        # create new image
        width=int(width)
        height=int(height)
        image = bpy.data.images.new(name=name_image, width=width, height=height, alpha=True)

        # Create a NumPy array to store the image data
        pixels = np.empty(width * height * 4, dtype=np.float32)
        for y in range(height):
            for x in range(width):
                # 0,0 at bottom left
                #if y < 5: c = COLORS.black
                #elif x < 5: c = COLORS.white
                #else: c = COLORS.gray

                c = colorFn(x, y, width, height)

                # Set the pixel values (RGBA)
                index = (y * width + x) * 4
                pixels[index]     = c[0]
                pixels[index + 1] = c[1]
                pixels[index + 2] = c[2]
                pixels[index + 3] = c[3]

        # Flatten the NumPy array and assign it to the image
        image.pixels = pixels.tolist()
        image.update()
        image.pack()
        #image.make_local()

    # Create a new material and add it
    name_mat = name+"_mat"
    mat = bpy.data.materials.new(name=name_mat)

    # Cfg default nodes
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    for node in nodes: nodes.remove(node)

    # Add a ShaderNodeTexImage node
    texture_node = nodes.new(type='ShaderNodeTexImage')
    texture_node.location = (0, 0)
    texture_node.image = image
    texture_node.extension = "EXTEND" # NOTE:: better than repeat to debug UV outside ranges

    # Add an Input node for UV coordinates
    uv_map_node = nodes.new(type='ShaderNodeUVMap')
    uv_map_node.location = (-200, 0)
    uv_map_node.uv_map = uv_layer

    # Add an Output node
    output_node = nodes.new(type='ShaderNodeOutputMaterial')
    output_node.location = (400, 0)

    # Connect the nodes
    mat.node_tree.links.new(uv_map_node.outputs['UV'], texture_node.inputs['Vector'])
    mat.node_tree.links.new(texture_node.outputs['Color'], output_node.inputs['Surface'])

    return mat

def gen_gradientMat(uv_layer:str, name:str, width=GRADIENTS._default_res, height=GRADIENTS._default_res*0.5, colorFn = GRADIENTS.red, forceNew = False):
    """ 1D gradient, but use a 2D image with height to visualize better the UV coords """
    gradient = lambda x,y,w,h: colorFn(y, h)
    return gen_textureMat(uv_layer, name, width, height, gradient, forceNew)