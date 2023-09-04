import bpy
import bpy.types as types

from . import utils, utils_trans
from .utils_dev import DEV


# XXX:: all access to obj.children take O(n) where n is ALL objects of the scene...
# blender scene utils: copy, delete, get, select, hide...
#-------------------------------------------------------------------

def copy_object(obj: types.Object, context: types.Context, link_mesh = False, keep_mods = True, namePreffix = "", nameSuffix = "") -> types.Object:
    """ Copy the object but not its children """
    obj_copy: types.Object = obj.copy()
    context.scene.collection.objects.link(obj_copy)

    # make a raw copy or leave a linked mesh
    if not link_mesh and obj.data:
        obj_copy.data = obj.data.copy()
        obj_copy.data.name = f"{namePreffix}{obj.data.name}{nameSuffix}"

    # remove mods or not
    if not keep_mods:
        for mod in obj_copy.modifiers:
            obj_copy.modifiers.remove(mod)

    # avoid setting name unless specified, otherwise the copy gets the priority name without .001
    if namePreffix or nameSuffix:
        obj_copy.name = f"{namePreffix}{obj.name}{nameSuffix}"

    # keep original visibility
    obj_copy.hide_set(obj.hide_get())

    return obj_copy

def copy_objectRec(obj: types.Object, context: types.Context, link_mesh = False, keep_mods = True, namePreffix = "", nameSuffix = "") -> types.Object:
    """ Copy the object along its children """
    obj_copy = copy_object(**utils.get_kwargs())

    # copy rec + set parenting and force them to keep the original world pos
    for child in obj.children:
        child_copy = copy_objectRec(child, **utils.get_kwargs(1))
        child_copy.parent = obj_copy
        child_copy.matrix_world = child.matrix_world
    return obj_copy

#-------------------------------------------------------------------

def delete_object(obj: types.Object, ignore_data = False, ignore_mat = False):
    data,type,mat = obj.data, obj.type, obj.active_material
    #DEV.log_msg(f"Deleting {obj.name}", {"DELETE", "OBJ"})
    bpy.data.objects.remove(obj)

    # NOTE:: meshes/data is leftover otherwise, delete after removing the object user
    if not ignore_data and data:
        delete_data(data, type)
    if not ignore_mat and mat:
        delete_mat(mat)

def delete_objectRec(obj: types.Object, ignore_data = False, logAmount=False):
    """ Delete the object and children recursively """
    delete_objectChildren(obj, ignore_data, rec=True, logAmount=logAmount)
    delete_object(obj, ignore_data)

def delete_objectChildren(ob_father: types.Object, ignore_data = False, rec=True, logAmount=False):
    """ Delete the children objects """

    # deleting a parent leads to a deleted children (not its mesh tho)
    toDelete = ob_father.children if not rec else ob_father.children_recursive
    if logAmount:
        DEV.log_msg(f"Deleting {len(toDelete)} objects", {"DELETE"})

    for child in reversed(toDelete):
        delete_object(child, ignore_data)

def delete_data(data, type = "MESH", do_unlink=False):
    """ NOTE:: seems like deleting the data deletes the object? """
    if not do_unlink and data.users: return
    #DEV.log_msg(f"Deleting {data.name}", {"DELETE", "DATA"})
    try:
        if type == "MESH":      collection=bpy.data.meshes
        elif type == "CURVE":   collection=bpy.data.curves
        else: raise TypeError(f"Unimplemented data type {type} from {data.name}")
        collection.remove(data, do_unlink=do_unlink)

    except Exception as e:
        DEV.log_msg(str(e), {"DELETE", "DATA", "ERROR"})

def delete_mat(mat, do_unlink=False):
    if not do_unlink and mat.users: return
    bpy.data.materials.remove(mat, do_unlink=do_unlink)

def delete_orphanData(collectionNames = None, logAmount = True):
    """ When an object is deleted its mesh/data may be left over """
    if collectionNames is None: collectionNames = ["meshes", "curves"]
    DEV.log_msg(f"Checking collections: {collectionNames}", {"DELETE"})

    # dynamically check it has the collection
    for colName in collectionNames:
        colName = colName.strip()
        if not hasattr(bpy.data, colName): continue
        collection = getattr(bpy.data, colName)

        toDelete = []
        for data in collection:
            if not data.users: toDelete.append(data)

        if logAmount: DEV.log_msg(f"Deleting {len(toDelete)}/{len(collection)} {colName}", {"DELETE"})
        for data in toDelete:
            collection.remove(data, do_unlink=False)

#-------------------------------------------------------------------

# OPT:: not robuts... All names are unique, even under children hierarchies. Blender adds .001 etc
def get_nameClean(name):
    try: return name if name[-4] != "." else name[:-4]
    except IndexError: return name

def get_object_fromList(objects: list[types.Object], name: str, exactMatch = True) -> types.Object|None:
    """ Find an object by name inside the list provided, returns the first found.
        # IDEA:: maybe all children search based methods should return the explored objs
    """
    if exactMatch:
        for obj in objects:
            if obj.name == name: return obj

    # cleaning the suffix instead of direclty comparing the names
    else:
        name = get_nameClean(name)
        for obj in objects:
            cleanName = get_nameClean(obj.name)
            if cleanName == name: return obj

    return None

def get_multiObject_fromList(objects: list[types.Object], names: list[str], exactMatch = True) -> list[types.Object]:
    """ Find objects by name inside the list provided, returns a list of the same size with the first founds for each name (if any).
        # NOTE:: mainly useful for get_children where the children list from the parent object is only requested once
    """
    found = [ get_object_fromList(objects, n, exactMatch) for n in names ]
    return found

def get_object_fromScene(scene: types.Scene, name: str, exactMatch = True) -> types.Object|None:
    """ Find an object in the scene by name (starts with to avoid limited exact names). Returns the first found. """
    return get_object_fromList(scene.objects, name, exactMatch)

def get_multiObject_fromScene(scene: types.Scene, names: list[str], exactMatch = True) -> list[types.Object]:
    """ Find an object in the scene by name (starts with to avoid limited exact names). Returns a list with the same size, with potentially None elements! """
    return get_multiObject_fromList(scene.objects, names, exactMatch)

def get_child(obj: types.Object, name: str, rec=False, exactMatch = False) -> types.Object|None:
    """ Find child by name (starts with to avoid limited exact names) """
    toSearch = obj.children if not rec else obj.children_recursive
    return get_object_fromList(toSearch, name, exactMatch)

def get_children(obj: types.Object, names: list[str], rec=False, exactMatch = False) -> list[types.Object]:
    """ Find child by name (starts with to avoid limited exact names). Returns a list with the same size, with potentially None elements!  """
    toSearch = obj.children if not rec else obj.children_recursive
    return get_multiObject_fromList(toSearch, names, exactMatch)

#-------------------------------------------------------------------

def select_nothing():
    bpy.ops.object.select_all(action='DESELECT')

def select_unhide(obj: types.Object, context: types.Context, select=True):
    obj.hide_set(False)

    if select:
        obj.select_set(True)
        context.view_layer.objects.active = obj
        #context.view_layer.objects.selected += [obj]   # appended by select_set
        #context.active_object = obj                    # read-only
    else:
        obj.select_set(False)

    #DEV.log_msg(f"{obj.name}: select {select}", {"SELECT"})

def select_unhideRec(obj: types.Object, context: types.Context, select=True, selectChildren=True):
    """ Hide the object and children recursively """
    for child in obj.children_recursive:
        select_unhide(child, context, selectChildren)
    select_unhide(obj, context, select)

def hide_objectRec(obj: types.Object, hide=True):
    """ Hide the object and children recursively """
    for child in obj.children_recursive:
        hide_objectRec(child, hide)
    obj.hide_set(hide)

#-------------------------------------------------------------------

def set_child(child: types.Object, parent: types.Object, keepTrans = True, noInv = False):
    """ Child object with the same options as the viewport, also updates the child world matrix """
    if keepTrans:
        if noInv:
            # Set the child basis matrix relative to the parent direclty
            child_matrix_local = parent.matrix_world.inverted() @ child.matrix_world
            child.parent = parent
            child.matrix_basis = child_matrix_local
        else:
            # Just set the matrix parent inverse
            child.parent = parent
            child.matrix_parent_inverse = parent.matrix_world.inverted()
    else:
        # Parenting directly so the world matrix will be applied as local
        child.parent = parent
        # Update world matrix manually instead of waiting for scene update, no need with keepTrans
        utils_trans.trans_update(child)

def gen_child(
    obj: types.Object, name: str, context: types.Context,
    mesh: types.Mesh = None, keepTrans = True, noInv = False, hide: bool = False
    ):
    """ Generate a new child with the CHILD mw_id.type """
    obj_child = bpy.data.objects.new(name, mesh)
    context.scene.collection.objects.link(obj_child)

    set_child(obj_child, obj, keepTrans, noInv)
    obj_child.hide_set(hide)
    return obj_child

def gen_childClean(
    obj: types.Object, name: str, context: types.Context,
    mesh: types.Mesh = None, keepTrans = True, noInv = False, hide: bool = False
    ):
    """ Generate a new child, delete the previous one if found """
    obj_child = get_child(obj, name)
    if obj_child:
        delete_objectRec(obj_child)
    return gen_child(**utils.get_kwargs())

def gen_childReuse(
    obj: types.Object, name: str, context: types.Context,
    mesh: types.Mesh = None, keepTrans = True, noInv = False, hide: bool = False
    ):
    """ Generate a new child, reuse the previous one if found """
    obj_child = get_child(obj, name)
    if obj_child:
        #  NOTE:: subtitute to unlink and then delete prev data, otherwise deleting it deletes the object?
        if obj_child.data:
            prevMesh = obj_child.data
            obj_child.data = mesh
            delete_data(prevMesh, obj_child.type)

        #set_child(obj_child, obj, keepTrans, noInv)
        obj_child.hide_set(hide)
        return obj_child

    return gen_child(**utils.get_kwargs())

#-------------------------------------------------------------------

def needsSanitize_object(obj):
    """ Check broken reference to bl object """
    if obj is None: return False
    try:
        name_obj = obj.name
        return False
    except ReferenceError:
        return True

def returnSanitized_object(obj):
    """ Change object to none in case of broken bl object """
    if needsSanitize_object(obj):
        return None
    else:
        return obj
