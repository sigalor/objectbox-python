#!/usr/bin/env python3
import sys
import os
import time
from objectbox import ObjectBox
from models import MainModel as DroneDBModel

def main():
    if len(sys.argv) != 3:
        print("usage: " + sys.argv[0] + " [integer] [string]")
        sys.exit(0)
    
    obx = ObjectBox(DroneDBModel)
    print("before:", obx.count("TestEntity"))
    obx.put("TestEntity", {
        "simpleInt": int(sys.argv[1]),
        "simpleString": sys.argv[2],
        "createdAt": int(time.time() * 1000000)
    })
    print("after:", obx.count("TestEntity"))

if __name__ == "__main__":
    main()
