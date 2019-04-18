#!/usr/bin/env python3
import sys
import os
import re
import json
import subprocess
import objectbox

OBXPropertyTypeMappings = {
    "bool": "OBXPropertyType_Bool",
    "byte": "OBXPropertyType_Char",
    "ubyte": "OBXPropertyType_Char",
    "short": "OBXPropertyType_Short",
    "ushort": "OBXPropertyType_Short",
    "int": "OBXPropertyType_Int",
    "uint": "OBXPropertyType_Int",
    "float": "OBXPropertyType_Float",
    "long": "OBXPropertyType_Long",
    "ulong": "OBXPropertyType_Long",
    "double": "OBXPropertyType_Double",
    "int8": "OBXPropertyType_Char",
    "uint8": "OBXPropertyType_Char",
    "int16": "OBXPropertyType_Short",
    "uint16": "OBXPropertyType_Short",
    "int32": "OBXPropertyType_Int",
    "uint32": "OBXPropertyType_Int",
    "int64": "OBXPropertyType_Long",
    "uint64": "OBXPropertyType_Long",
    "float32": "OBXPropertyType_Float",
    "float64": "OBXPropertyType_Double",
    "string": "OBXPropertyType_String",
    #"[ubyte]": "OBXPropertyType_ByteVector",
    #"[byte]": "OBXPropertyType_ByteVector",
    #"[string]": "OBXPropertyType_StringVector"
}

def parse_flatbuffers_tables(input):
    table_name_regex = re.compile(r'^\s*table\s+(\w+)\s*{\s*')
    attr_regex = re.compile(r'^(\w+):\s*(\w+);\s*')
    table_finalize_regex = re.compile(r'^}\s*')

    # TODO: check that table and attribute names are unique
    tables = []
    table_names = []
    while True:
        res = table_name_regex.match(input)
        if res == None:
            break
        groups = res.groups()
        assert(len(groups) == 1)
        table_name = groups[0]
        if table_name in table_names:
            raise ValueError("duplicate table name: " + table_name)
        input = input[res.span()[1]:]

        attrs = []
        attr_names = []
        while True:
            res = attr_regex.match(input)
            if res == None:
                break
            groups = res.groups()
            assert(len(groups) == 2)
            if groups[0] in attr_names:
                raise ValueError("duplicate attribute in table '" + table_name + "': " + groups[0])
            if groups[1] not in OBXPropertyTypeMappings:
                raise ValueError("unknown type of '" + groups[0] + "' attribute of table '" + table_name + "': " + groups[1])
            if groups[0] == "id" and groups[1] != "ulong":
                raise ValueError("expected type of 'id' attribute of table '" + table_name + "' to be ulong, not " + groups[1])
            attrs.append((groups[0], OBXPropertyTypeMappings[groups[1]]))
            attr_names.append(groups[0])
            input = input[res.span()[1]:]
        
        attrs_dict = dict(attrs)
        if "id" not in attrs_dict:
            raise ValueError("table " + table_name + " has no 'id' attribute")
        tables.append((table_name, attrs))
        table_names.append(table_name)

        res = table_finalize_regex.match(input)
        assert(res != None)
        input = input[res.span()[1]:]
    
    if len(tables) == 0:
        raise ValueError("no valid tables found")
    return tables

def get_entities_py(input):
    with open(sys.argv[1], "rb") as f:
        elf_magic = f.read(4)
        if elf_magic != b'\x7fELF':
            raise ValueError("provided flatc is not executable")
    return subprocess.getoutput("bash -c '" + sys.argv[1] + " -o /tmp/flatc-output -p entities.fbs; cat /tmp/flatc-output/*.py; rm -rf /tmp/flatc-output/'")

def main():
    if len(sys.argv) != 3:
        print("usage: " + sys.argv[0] + " [path to flatc] [filename.fbs]")
        sys.exit(0)
    
    with open(sys.argv[2], "r") as f:
        input = f.read()
    tables = parse_flatbuffers_tables(input)
    entities_py = get_entities_py(input)
    
    model_source = "from objectbox import *\n\n"
    table_idx = 1
    for name, attrs in tables:
        model_source += "class " + name + "Model(EntityModelBase):\n" +         \
            "    def __init__(self, obx):\n" +                                  \
            "        super().__init__(obx)\n" +                                 \
            "        self.entityId = " + str(table_idx) + "\n" +                \
            "        self.entityName = \"" + name + "\"\n" +                    \
            "        self.attributes = [" + ", ".join(map(lambda x: "(\"" + x[0] + "\", " + x[1] + ", " + name + "Add" + x[0][0].upper() + x[0][1:] + ")", attrs)) + "]\n" + \
            "        self.startFn = " + name + "Start\n" +                      \
            "        self.endFn = " + name + "End\n\n"
        table_idx += 1
    
    model_source += "class MainModel:\n" +                                      \
        "    def __init__(self, obx):\n" +                                      \
        "        self.obx = obx\n" +                                            \
        "        self.entityModels = [" + ", ".join(map(lambda x: x[0] + "Model(self.obx)", tables)) + "]\n" + \
        "        self.entityModelsDict = {"
    
    table_idx = 0
    for name, _ in tables:
        model_source += "\"" + name + "\": self.entityModels[" + str(table_idx) + "]"
        if table_idx != len(tables) - 1:
            model_source += ", "
        table_idx += 1
    
    model_source += "}\n\n    def getOBXModel(self):\n" + \
        "        model = self.obx.obx_model_create()\n" + \
        "        for m in self.entityModels:\n" + \
        "            m.addToOBXModel(model)\n" + \
        "        self.obx.obx_model_last_entity_id(model, len(self.entityModels), 10000 + len(self.entityModels))\n" + \
        "        return model\n\n" + \
        "    def getEntityModelInstance(self, entityStr):\n" + \
        "        if entityStr not in self.entityModelsDict:\n" + \
        "            raise ValueError(\"unknown entity: \" + entityStr)\n" + \
        "        return self.entityModelsDict[entityStr]"

    with open("models.py", "w") as f:
        f.write(entities_py + "\n\n\n\n" + model_source)



if __name__ == "__main__":
    main()
