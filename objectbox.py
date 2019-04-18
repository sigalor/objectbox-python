from ctypes import *
import flatbuffers

OBXPropertyType_Bool = 1
OBXPropertyType_Byte = 2
OBXPropertyType_Short = 3
OBXPropertyType_Char = 4
OBXPropertyType_Int = 5
OBXPropertyType_Long = 6
OBXPropertyType_Float = 7
OBXPropertyType_Double = 8
OBXPropertyType_String = 9
OBXPropertyType_Date = 10
OBXPropertyType_Relation = 11
OBXPropertyType_ByteVector = 23
OBXPropertyType_StringVector = 30

OBXPropertyFlags_ID = 1
OBXPropertyFlags_NON_PRIMITIVE_TYPE = 2
OBXPropertyFlags_NOT_NULL = 4
OBXPropertyFlags_INDEXED = 8
OBXPropertyFlags_RESERVED = 16
OBXPropertyFlags_UNIQUE = 32
OBXPropertyFlags_ID_MONOTONIC_SEQUENCE = 64
OBXPropertyFlags_ID_SELF_ASSIGNABLE = 128
OBXPropertyFlags_INDEX_PARTIAL_SKIP_NULL = 256
OBXPropertyFlags_INDEX_PARTIAL_SKIP_ZERO = 512
OBXPropertyFlags_VIRTUAL = 1024
OBXPropertyFlags_INDEX_HASH = 2048
OBXPropertyFlags_INDEX_HASH64 = 4096
OBXPropertyFlags_UNSIGNED = 8192



def OBXError(obx, desc):
    return ValueError(desc + ": " + c_char_p(obx.obx_last_error_message()).value.decode("utf8"))

def OBXCheckZero(obx, desc, ret):
    if ret != 0:
        raise OBXError(obx, desc)
    return ret

def OBXCheckNotZero(obx, desc, ret):
    if ret == 0:
        raise OBXError(obx, desc)
    return ret



class EntityModelBase:
    def __init__(self, obx):
        self.obx = obx

    def getGlobalPropertyId(self, i):
        return 100000000 + 10000 * self.entityId + i
    
    def addToOBXModel(self, model):
        self.obx.obx_model_entity(model, bytes(self.entityName, "utf8"), self.entityId, 10000 + self.entityId)
        i = 0
        for k, t, _ in self.attributes:
            i += 1
            self.obx.obx_model_property(model, bytes(k, "utf8"), t, i, self.getGlobalPropertyId(i))
            if k == "id":
                self.obx.obx_model_property_flags(model, OBXPropertyFlags_ID)
        self.obx.obx_model_entity_last_property_id(model, i, self.getGlobalPropertyId(i))
    
    def generateFlatbuffers(self, obj):
        builder = flatbuffers.Builder(1024)
        fb_strings = {}
        for k, t, _ in self.attributes:
            if k in obj and t == OBXPropertyType_String:
                fb_strings[k] = builder.CreateString(obj[k])

        self.startFn(builder)
        for k, t, addFn in self.attributes:
            if k not in obj:
                continue
            if t == OBXPropertyType_String:
                val = fb_strings[k]
            else:
                val = obj[k]
            addFn(builder, val)
        entity = self.endFn(builder)
        builder.Finish(entity)
        return builder.Output()



class ObjectBoxTransaction:
    def __init__(self, ob):
        self.obx = ob.obx
        self.txn = OBXCheckNotZero(self.obx, "begin transaction", self.obx.obx_txn_begin(ob.store))
    
    def commit(self):
        OBXCheckZero(self.obx, "commit transaction", self.obx.obx_txn_commit(self.txn))

    def destroy(self):
        OBXCheckZero(self.obx, "close transaction", self.obx.obx_txn_close(self.txn))



class ObjectBoxCursor:
    def __init__(self, ob, txn, entityStr):
        self.obx = ob.obx
        self.model_inst = ob.model.getEntityModelInstance(entityStr)
        self.cursor = OBXCheckNotZero(self.obx, "create cursor", self.obx.obx_cursor_create(txn.txn, self.model_inst.entityId))
    
    def generateIdForPut(self):
        return self.obx.obx_cursor_id_for_put(self.cursor, 0)
    
    def put(self, id, entry_bytes):
        OBXCheckZero(self.obx, "put into cursor", self.obx.obx_cursor_put(self.cursor, id, bytes(entry_bytes), len(entry_bytes), 0))

    def putObj(self, obj):
        obj["id"] = self.generateIdForPut();
        return self.put(obj["id"], self.model_inst.generateFlatbuffers(obj))
    
    def count(self):
        num_entries = c_uint64()
        self.obx.obx_cursor_count(self.cursor, byref(num_entries))
        return num_entries.value

    def destroy(self):
        OBXCheckZero(self.obx, "close cursor", self.obx.obx_cursor_close(self.cursor))



class ObjectBox:
    def __init__(self, model, so_path = "libobjectbox.so"):
        self.obx = CDLL(so_path)
        self.model = model(self.obx)
        self.store = OBXCheckNotZero(self.obx, "create store", self.obx.obx_store_open(self.model.getOBXModel(), 0))
    
    def __del__(self):
        OBXCheckZero(self.obx, "await async completion of store", self.obx.obx_store_await_async_completion(self.store))
        OBXCheckZero(self.obx, "close store", self.obx.obx_store_close(self.store))

    def put(self, entityStr, obj):
        txn = ObjectBoxTransaction(self)
        cursor = ObjectBoxCursor(self, txn, entityStr)
        cursor.putObj(obj)
        cursor.destroy()
        txn.commit()
        txn.destroy()

    def count(self, entityStr):
        txn = ObjectBoxTransaction(self)
        cursor = ObjectBoxCursor(self, txn, entityStr)
        num_items = cursor.count()
        cursor.destroy()
        txn.destroy()
        return num_items
