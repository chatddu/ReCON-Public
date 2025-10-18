import json

tagbase = "intqoin"
hive = json.load(open("./../../templates/hiverings10.json"))
thisring = hive

for level in range(10,0,-1):
    # save this ring's inner child for next iteration - we assume template is correct
    thisringsinnerchild = thisring['children'][0]
    for i in range(0,(level * 6)):
        tag = tagbase + "." + str(level) + "." + str(i)
        thisring['children'].append({"tag":tag})
    thisring = thisringsinnerchild

s = json.dumps(hive, indent=2)
print(s)