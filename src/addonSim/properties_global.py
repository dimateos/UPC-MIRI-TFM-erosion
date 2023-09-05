import bpy
import bpy.types as types
import bpy.props as props

from . import handlers
from .properties_utils import Prop_inspector

from . import utils_scene
from .utils_dev import DEV


#-------------------------------------------------------------------

class MW_id(types.PropertyGroup):
    """ Property stored in the objects to identify the root and other ID"""

    meta_type: props.EnumProperty(
        name="Type", description="Meta type added to the object to control some logic",
        items=(
            ('NONE', "No fracture", "No fracture generated"),
            ('ROOT', "Root object", "Root object holding the fracture"),
            ('CHILD', "Child object", "Child object part of the fracture"),
        ),
        default={'NONE'},
        options={'ENUM_FLAG'},
    )

    storage_id: props.IntProperty(
        name="Storage id", description="Id to access the pairing global storage data",
        default=-1,
    )

    cell_id: props.IntProperty(
        name="Cell id", description="Id that matches the voronoi cell index",
        default=-1,
    )


#-------------------------------------------------------------------

class MW_id_utils:
    """ MW_id util functions stored outside the class to avoid all the memory footprint inside the objects"""

    @staticmethod
    def isRoot(obj: types.Object) -> bool:
        """ Check if this is a root object, core the fracture (holds most of the config) """
        return "ROOT" in obj.mw_id.meta_type
    @staticmethod
    def isChild(obj: types.Object) -> bool:
        """ Check if this is a child object part of a fracture (but could be either a cell, link, or intermediate object) """
        return "CHILD" in obj.mw_id.meta_type

    @staticmethod
    def hasRoot(obj: types.Object) -> bool:
        """ Check if the object is part of a fracture (default value objects have) """
        #DEV.log_msg(f"hasRoot check: {obj.name} -> {obj.mw_id.meta_type}", {"REC", "CFG"})
        return "NONE" not in obj.mw_id.meta_type

    @staticmethod
    def getRoot(obj: types.Object) -> types.Object | None:
        """ Retrieve the root object holding the config (MW_id forward declared)"""
        #DEV.log_msg(f"getRoot search: {obj.name} -> {obj.mw_id.meta_type}", {"REC", "CFG"})
        if "NONE" in obj.mw_id.meta_type:
            return None

        try:
            obj_chain = obj
            while "CHILD" in obj_chain.mw_id.meta_type:
                obj_chain = obj_chain.parent

            # NOTE:: check the root is actually root: could happen if an object is modified at some step by the obj
            if "ROOT" not in obj_chain.mw_id.meta_type: raise ValueError("Chain ended with no root")
            #DEV.log_msg(f"getRoot chain end: {obj_chain.name}", {"RET", "CFG"})
            return obj_chain

        # the parent was removed
        except AttributeError:
            DEV.log_msg(f"getRoot chain broke: {obj.name} -> no rec parent", {"ERROR", "CFG"})
            return None
        # the parent was not root
        except ValueError:
            DEV.log_msg(f"getRoot chain broke: {obj_chain.name} -> not root ({obj_chain.mw_id.meta_type})", {"ERROR", "CFG"})
            return None

    @staticmethod
    def getSceneRoots(scene: types.Scene) -> list[types.Object]:
        """ Retrieve the root objects in the scene
            # OPT:: could use the global storage instead of iterating the scene
        """
        roots = [ obj for obj in scene.objects if MW_id_utils.isRoot(obj) ]
        return roots

    @staticmethod
    def setMetaType(obj: types.Object, type: set[str], skipParent = False, childrenRec = True):
        """ Set the property to the object and all its children (dictionary ies copied, not referenced)
            # NOTE:: acessing obj children is O(len(bpy.data.objects)), so just call it on the root again
            # OPT:: could avoid using this and just set the children like for cell_id?
        """
        if not skipParent:
            obj.mw_id.meta_type = type.copy()

        toSet = obj.children_recursive if childrenRec else obj.children
        #DEV.log_msg(f"Setting {type} to {len(toSet)} objects", {"CFG"})
        for child in toSet:
            child.mw_id.meta_type = type.copy()

    def resetMetaType(obj: types.Object):
        obj.mw_id.meta_type = {"NONE"}

    #-------------------------------------------------------------------

    storage_uuid = 0
    """ Simple counter as uuid
        # OPT:: should be a read-only property
    """

    @staticmethod
    def genStorageId(obj: types.Object):
        """ Set a new UUID for the storage, usually best to use getStorageId. Does not check the current id beforehand. """
        obj.mw_id.storage_id = MW_id_utils.storage_uuid
        MW_id_utils.storage_uuid += 1

    @staticmethod
    def hasStorageId(obj: types.Object):
        """ Check if the storage_id has been initialized, both the root and cells have it """
        return obj.mw_id.storage_id != -1

    @staticmethod
    def sameStorageId(obj_a: types.Object, obj_b: types.Object):
        """ Check if both objects are part of the same fracture """
        return obj_a.mw_id.storage_id == obj_b.mw_id.storage_id

    @staticmethod
    def getStorageId(obj: types.Object):
        """ Gets the storage id (assigns new uuid when not set yet) """
        if not MW_id_utils.hasStorageId(obj):
            MW_id_utils.genStorageId(obj)
        return obj.mw_id.storage_id

    @staticmethod
    def getStorageId_assert(obj: types.Object):
        """ Gets the storage id (raises an exception if the id is not set yet) """
        if not MW_id_utils.hasStorageId(obj):
            raise ValueError(f"{obj.name}: Invalid storage id (-1)!")
        return obj.mw_id.storage_id

    @staticmethod
    def resetStorageId(obj: types.Object):
        """ Leave storage_id as not initilized """
        obj.mw_id.storage_id = -1

    #-------------------------------------------------------------------

    @staticmethod
    def hasCellId(obj: types.Object):
        """ Check if the cell_id has been initialized, meaning this is a cell object! """
        return obj.mw_id.cell_id != -1

    @staticmethod
    def resetCellId(obj: types.Object):
        """ Leave cell_id as not initilized """
        obj.mw_id.cell_id = -1


#-------------------------------------------------------------------

class MW_global_storage:
    """  Blender properties are quite limited, ok for editting in the UI but for just data use python classes.
        # NOTE:: atm this storage is lost on file or module reload... could store in a .json as part of the .blend
    """

    id_fracts       = dict() # id:int -> MW_fract
    id_fracts_obj   = dict() # id:int -> Object

    @classmethod
    def addFract(cls, fract, obj):
        id = MW_id_utils.getStorageId(obj)
        DEV.log_msg(f"Add: {obj.name} ({id})...", {"GLOBAL", "STORAGE"})

        # add the fract and the obj to the storage
        if id in cls.id_fracts:
            DEV.log_msg(f"Replacing found fract", {"GLOBAL", "STORAGE", "ERROR"})
        cls.id_fracts[id] = fract
        cls.id_fracts_obj[id] = obj
        return id

    @classmethod
    def getFract_fromID(cls, id):
        #DEV.log_msg(f"Get: {id}", {"GLOBAL", "STORAGE"})
        try:
            return cls.id_fracts[id]
        except KeyError:
            DEV.log_msg(f"Not found {id}: probably reloaded the module?", {"GLOBAL", "STORAGE", "ERROR"})

    @classmethod
    def getFract(cls, obj):
        id = MW_id_utils.getStorageId_assert(obj)
        return cls.getFract_fromID(id)

    @classmethod
    def hasFract(cls, obj):
        id = MW_id_utils.getStorageId_assert(obj)
        return id in cls.id_fracts

    @classmethod
    def freeFract_fromID(cls, id):
        DEV.log_msg(f"Free: {id}", {"GLOBAL", "STORAGE"})
        try:
            # delete the fract and only pop the obj
            fract = cls.id_fracts.pop(id)
            del fract.cont
            del fract.links
            del fract.sim
            del fract
            obj = cls.id_fracts_obj.pop(id)
        except KeyError:
            DEV.log_msg(f"Not found {id}: probably reloaded the module?", {"GLOBAL", "STORAGE", "ERROR"})

    @classmethod
    def freeFract(cls, obj):
        id = MW_id_utils.getStorageId_assert(obj)
        return cls.freeFract_fromID(id)

    @classmethod
    def freeFract(cls, obj):
        id = MW_id_utils.getStorageId_assert(obj)
        return cls.freeFract_fromID(id)

    @classmethod
    def freeFract_attempt(cls, obj):
        if MW_id_utils.hasStorageId(obj):
            id = obj.mw_id.storage_id
            if id in cls.id_fracts:
                cls.freeFract_fromID(id)

    # callback triggers
    enable_autoPurge_default = False
    enable_autoPurge = enable_autoPurge_default

    @classmethod
    def purgeFracts(cls):
        """ Remove fracts of deleted scene objects (that could appear again with UNDO etc)"""
        toPurge = []

        # detect broken object references
        for id,obj in cls.id_fracts_obj.items():
            if utils_scene.needsSanitize_object(obj):
                toPurge.append(id)

        DEV.log_msg(f"Purging {len(toPurge)}: {toPurge}", {"GLOBAL", "STORAGE"})
        for id in toPurge:
            cls.freeFract_fromID(id)

    @classmethod
    def sanitizeFracts(cls):
        """ Check references to other objects inside the fracts parts are not broken (mainly cont)"""
        toSanitize = []

        # detect NON-broken object references
        for id,obj in cls.id_fracts_obj.items():
            if not utils_scene.needsSanitize_object(obj):
                toSanitize.append(id)

        DEV.log_msg(f"Sanitizing {len(toSanitize)} fracts /{len(cls.id_fracts_obj)}", {"SANITIZE", "FRACT"})
        for id in toSanitize:
            cls.id_fracts[id].sanitize()

    @classmethod
    def purgeFracts_callback(cls, _scene_=None, _undo_name_=None):
        cls.sanitizeFracts()
        if cls.enable_autoPurge:
            cls.purgeFracts()


#-------------------------------------------------------------------

class MW_global_selected:
    """  Keep a reference to the selected root with a callback on selection change """
    # OPT:: store the data in the scene/file to avoid losing it on reload? Still issues with global storage anyway
    #class MW_global_selected(types.PropertyGroup): + register the class etc
    #my_object: bpy.props.PointerProperty(type=bpy.types.Object)

    # root fracture object
    root            : types.Object = None
    fract                          = None
    prevalid_root   : types.Object = None
    prevalid_fract                 = None
    """ prevalid are the previous ones and always valid (not at the start) """

    # common selection
    selection       : types.Object = None
    current         : types.Object = None
    prevalid_last   : types.Object = None

    @classmethod
    def setSelected(cls, new_selection):
        """ Update global selection status and query fract root
            # NOTE:: new_selection lists objects alphabetically not by order of selection
            # OPT:: multi-root selection? work with current active instead of last new active?
        """
        rootChange = False

        if new_selection:
            if cls.current:
                cls.prevalid_last = cls.current
            cls.selection = new_selection.copy() if isinstance(new_selection, list) else [new_selection]
            #cls.current = cls.selection[-1]

            # will differ later if the active_object is changed to one among already selected
            cls.current = bpy.context.active_object

            newRoot = MW_id_utils.getRoot(cls.current)
            if newRoot:
                if cls.root:
                    cls.prevalid_root  = cls.root
                    cls.prevalid_fract = cls.fract
                else:
                    # going from none to something triggers the callback
                    rootChange = True

                cls.root  = newRoot
                cls.fract = MW_global_storage.getFract(newRoot)

                # new root selected callback
                if cls.root != cls.prevalid_root:
                    rootChange = True

            else:
                cls.root = None
                cls.fract = None

        else:
            cls.reset()

        cls.prevalid_sanitize()
        cls.logSelected()
        if rootChange:
            DEV.log_msg(f"Selection ROOT change: {cls.root.name}", {"CALLBACK", "SELECTION", "ROOT"})
            cls.callback_rootChange_actions.dispatch([cls.root])

    @classmethod
    def recheckSelected(cls):
        cls.setSelected(cls.selection)

    @classmethod
    def logSelected(cls):
        DEV.log_msg(f"root: {cls.root.name if cls.root else '...'} | last: {cls.current.name if cls.current else '...'}"
                    f" | selection: {len(cls.selection) if cls.selection else '...'}", {"GLOBAL", "SELECTED"})

    @classmethod
    def reset(cls):
        """ Reset all to None but keep sanitized references to prevalid """
        cls.selection = None
        cls.current      = None
        cls.root      = None
        cls.fract     = None
        cls.prevalid_sanitize()

    @classmethod
    def sanitize(cls):
        """ Potentially sanitize objects no longer on the scene """
        if utils_scene.needsSanitize_object(cls.current):
            cls.reset()
        else:
            cls.prevalid_sanitize()

    @classmethod
    def prevalid_sanitize(cls):
        cls.prevalid_last = utils_scene.returnSanitized_object(cls.prevalid_last)
        cls.prevalid_root = utils_scene.returnSanitized_object(cls.prevalid_root)
        if cls.prevalid_root is None:
            cls.prevalid_fract = None

    # callback triggers
    @classmethod
    def setSelected_callback(cls, _scene_=None, _selected_=None):
        cls.setSelected(_selected_)

    @classmethod
    def sanitizeSelected_callback(cls, _scene_=None, _name_selected_=None):
        cls.sanitize()
        cls.prevalid_sanitize()

    # callback serviced
    callback_rootChange_actions = handlers.Actions()


#-------------------------------------------------------------------
# Blender events

classes = [
    Prop_inspector,
    MW_id,
]
_name = f"{__name__[14:]}" #\t(...{__file__[-32:]})"

def register():
    DEV.log_msg(f"{_name}", {"ADDON", "INIT", "REG"})

    # sanitize in case of reload module
    MW_global_selected.sanitize()

    # callbaks
    handlers.callback_selectionChange_actions.append(MW_global_selected.setSelected_callback)
    handlers.callback_loadFile_actions.append(MW_global_selected.sanitizeSelected_callback)
    handlers.callback_undo_actions.append(MW_global_storage.purgeFracts_callback)
    handlers.callback_loadFile_actions.append(MW_global_storage.purgeFracts_callback)

    for cls in classes:
        bpy.utils.register_class(cls)

    # appear as part of default object props
    bpy.types.Object.mw_id = props.PointerProperty(
        type=MW_id,
        name="MW_id", description="MW fracture ids")

def unregister():
    DEV.log_msg(f"{_name}", {"ADDON", "INIT", "UN-REG"})

    # callbacks (might end up set or not, use check)
    handlers.callback_selectionChange_actions.remove(MW_global_selected.setSelected_callback)
    handlers.callback_loadFile_actions.remove(MW_global_selected.sanitizeSelected_callback)
    handlers.callback_undo_actions.removeCheck(MW_global_storage.purgeFracts_callback)
    handlers.callback_loadFile_actions.remove(MW_global_storage.purgeFracts_callback)

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

DEV.log_msg(f"{_name}", {"ADDON", "PARSED"})