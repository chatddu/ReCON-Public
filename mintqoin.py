import math
import json
import logging # https://realpython.com/python-logging/
import configargparse # https://pypi.org/project/ConfigArgParse/
import numpy
import cv2
import random
import glob
import os
import pathlib
import re
import csv
import time
import copy
import sys
from PIL import Image
from ast import literal_eval as make_tuple
from datetime import datetime
from slugify import slugify

class cfg:
    name = ''
    jfiles = ''

    r = 400
    margin = 20
    chan_width = 11
    # as of June 2023 - portrait carousel size on LinkedIn
    pgwidth = 2000
    pgheight = 2000
    r_eye_scale = 1/20
    includelevel = 0
    clickdepth = 32767
    maxlevel = 32767
    fully_renderable = True
    flatten = False

    parentnode_line_thickness = 1
    leafnode_line_thickness = 1
    leafnode_line_color = (200,200,200)
    parentnode_line_color = (200,200,200)
    min_r_to_render = 10
    n_frames = 120
    n_frames_max = 360
    fps = 24
    dmf = 18
    xoffset = 0 # needs to be computed after config init, as it depends on pgwidth and r
    # TODO: develop a more robust calculation for this
    child_render_threshold = chan_width * 5 # if child's crowded radius < this value, then child not rendered
    tagpath_sep = '.'
    replace = False
    noflood = False
    floodFill_loDiff = (5, 5, 5, 5)
    floodFill_hiDiff = (5, 5, 5, 5)
    colorspecs_dir = "../colorspecs_dir"
    profiles_dir = "../profiles_dir"
    colorspecs = {}
    colorspecs["default"] = {"name": "greyscale", "type": "list", "colors": "(222,222,222),(22,22,22)", "tuplist": [(222,222,222), (22,22,22)]}
    profiles = {}
    # TODO: add colors_random versions of these
    colorlistname = "random025225"
    profilename = "bigorg"
    profilecolorlistname = "winwincoeff"
    attrpropiters = 0
    colormodes = ["discontinuous", "smooth_loop", "smooth_outandback", "original", "random"]
    stickycolors = False
    nocolorburst = False
    tags = False
    hiddentags = False
    randcolorstart = True
    colormode = "discontinuous"
    closure = False
    eyecolor = (0,0,0)
    actual_min_r = min_r_to_render
    actual_max_r = 0
    medallions = False
    medallionsdir = "../medallions"
    medallionname = "we.png"
    minflatchildren = 5
    maxchilddepth = 32767
    # needs to be False for certain cases:
    # (a) only one element, e.g., single-celled.json
    # (b) TBD - certain geometries fail, not sure why yet
    fill_body_only = False
    maxpodsize = 13
    randomcolororlists = False
    dumpjson = False

    @staticmethod
    def set_config():

        p = configargparse.ArgParser(default_config_files=["yye_config.txt","..\yye_config.txt"])
        p.add("-c", "--yye-config", is_config_file=True, help="config file path")

        p.add("--name", default=datetime.today().strftime("%Y-%m-%d-%H%M%S"), help="the identifier (slugified by yye) to use as part of generated file/folder names")

        p.add("--jfiles", default="", help="pattern for json input files (use single quotes)")
        p.add("--dumpjson", default=False, action="store_true", help="dump resultant json file to the console")

        p.add("--r", type=int, default=500, help="radius of primary (outer) circle (excluding margin)")
        p.add("--margin", type=int, default=20, help="width between outermost circle edge and canvas edge")
        p.add("--cw", type=int, default=11, help="channel width")
        p.add("--pgwidth", type=int, default=1080, help="page width in pixels")     
        p.add("--pgheight", type=int, default=1350, help="page height in pixels")     
        p.add("--pupilscale", type=float, default=1/20, help="pupil scaling factor (multiple of radius, default = 0.05")
        p.add("--center", default=False, action="store_true", help="center the yin/yang on the page")
        p.add("--includesdepth", type=int, default=0, help="the number of include levels to process")
        p.add("--clickdepth", type=int, default=32767, help="the number of levels to render for each subtree")
        p.add("--render_fully", default=False, action="store_true", help="fully render the results, or, advise on canvas size scale-up required")
        p.add("--noflood", default=False, action="store_true", help="render wire frame(s) only")
        p.add("--medallions", default=False, action="store_true", help="render with medallions instead of yin/yangs")
        p.add("--medallionsdir", default="../medallions", help="path of dir containing medallion images")
        p.add("--medallionname", default="default.png", help="medallion name")
        p.add("--flatten", default=False, action="store_true", help="generate flattened version")

        p.add("--parentnode_line_thickness", type=int, default=1, help="parent line thickness (except outermost)")
        p.add("--leafnode_line_thickness", type=int, default=1, help="outermost and leaf line thickness")
        p.add("--parentnode_line_color", default="(200,200,200)", help="parent line colors (except outermost)")
        p.add("--leafnode_line_color", default="(200,200,200)", help="outermost and leaf line color")

        p.add("--frames", type=int, default=60, help="number of frames for one revolution")
        p.add("--framesfirm", default=False, action="store_true", help="# of frames specified is firm, do not adjust per color list lengths")
        p.add("--fps", type=int, default=5, help="frame per second")
        p.add("--dmf", type=int, default=18, help="dynamic medallion frames")
        p.add("--closure", default=False, action="store_true", help="last frame orientation = first (0 degrees)")

        p.add("--fill_body_only", default=False, action="store_true", help="fill body only (no vanguards or governors)")

        p.add("--colorspecs_dir", default="../colorspecs_dir", help="directory containing colorspecs_*.json files")
        p.add("--profiles_dir", default="../profiles_dir", help="directory containing profile_*.json files")
        p.add('--randcolorstart', default=False, action='store_true', help="randomly select an element's initial color from color list, start with first color on list")
        p.add('--colorlistname', default='random025225', help='color list name')
        p.add('--profilename', default='bigorg', help='profile name')
        p.add('--profilecolorlistname', default='winwincoeff', help='profile color list name')
        p.add('--attrpropiters', default=0, help="iterations to propogate profile attribute (e.g., winwincoeff)")
        p.add('--colormode', default='discontinuous', help='color transition smoothness mode')
        p.add('--stickycolors', default=False, action='store_true', help='use only one color for each node')
        p.add('--nocolorburst', default=False, action='store_true', help='globally disable colorburst option')
        p.add('--randomcolorlists', default=False, action='store_true', help='assign color lists randomly where non are specified')

        p.add('--pupilcolor', default='(0,0,0)', help='pupil color')

        p.add('--tags', default=False, action='store_true', help='show tags (without leading hyphens)')
        p.add('--hiddentags', default=False, action='store_true', help='show hidden tags (with leading hyphens)')

        p.add('-v', help='verbose', action='store_true')

        options = p.parse_args()

        cfg.r = options.r if options.r != None else cfg.r
        cfg.margin = options.margin
        cfg.n_frames = min(abs(options.frames), cfg.n_frames_max)
        if options.frames != None:
            cfg.framesfirm = options.framesfirm
        cfg.parentnode_line_thickness = options.parentnode_line_thickness
        cfg.leafnode_line_thickness = options.leafnode_line_thickness
        cfg.fps = min(abs(options.fps), 30)
        cfg.dmf = options.dmf
        cfg.noflood = options.noflood
        cfg.chan_width = options.cw
        cfg.colorspecs_dir = options.colorspecs_dir
        cfg.profiless_dir = options.profiles_dir
        if options.parentnode_line_color != None:
            tf, cfg.parentnode_line_color, msg = make_rgb_tuple(options.parentnode_line_color)
        tf, cfg.leafnode_line_color, msg = make_rgb_tuple(options.leafnode_line_color)
        cfg.name = slugify(options.name if options.name != None else datetime.today().strftime('%Y-%m-%d-%H%M%S'))
        cfg.tags = options.tags
        cfg.hiddentags = options.hiddentags
        cfg.randcolorstart = options.randcolorstart
        cfg.colorlistname = options.colorlistname
        cfg.profilecolorlistname = options.profilecolorlistname
        cfg.attrpropiters = int(options.attrpropiters)
        cfg.colormode = options.colormode
        cfg.stickycolors = options.stickycolors
        cfg.nocolorburst = options.nocolorburst
        cfg.randomcolorlists = options.randomcolorlists
        cfg.pgwidth = options.pgwidth if options.pgwidth != None else cfg.pgwidth
        cfg.pgwidth = max(cfg.pgwidth, (cfg.r + cfg.margin) * 2)
        cfg.pgheight = options.pgheight if options.pgheight != None else cfg.pgheight
        cfg.pgheight = max(cfg.pgheight, (cfg.r + cfg.margin) * 2)
        cfg.closure = options.closure
        cfg.r_eye_scale = options.pupilscale
        tf, cfg.eyecolor, msg = make_rgb_tuple(options.pupilcolor)
        cfg.center = options.center
        cfg.includesdepth = options.includesdepth
        cfg.clickdepth = options.clickdepth
        cfg.jfiles = options.jfiles
        cfg.dumpjson = options.dumpjson
        cfg.render_fully = options.render_fully
        cfg.medallions = options.medallions
        cfg.medallionsdir = options.medallionsdir
        cfg.medallionname = options.medallionname
        cfg.flatten = options.flatten

        # we want an odd-numbered channel width in order to have an exact middle, which
        # eases downstream rendering considerations
        if cfg.chan_width > 0 and cfg.chan_width % 2 == 0:
            cfg.chan_width += 1

        # load all of the colorspecs files from the specified (or default) dir
        jglob = glob.glob(cfg.colorspecs_dir + '/*.json')
        for filename in jglob:
            add_colorspec(json.load(open(filename)), filename)
        normalize_colorlists()

        # load all of the profile files from the specified (or default) dir
        jglob = glob.glob(cfg.profiles_dir + '/*.json')
        for filename in jglob:
            add_profile(json.load(open(filename)), filename)

        errors = 0
        for profile in cfg.profiles:
            cfg.profiles[profile]['sums'] = {}
            for lvl in cfg.profiles[profile]['weights']:
                cumulative = 0
                cfg.profiles[profile]['sums'][lvl] = [0] * 7 
                for i in range(0, 7):
                    cumulative = cumulative + cfg.profiles[profile]['weights'][lvl][i]
                    cfg.profiles[profile]['sums'][lvl][i] = cumulative
                if cumulative != 100:
                    print("Profile " + cfg.profiles[profile]['name'] + " values do not sum to 100")
                    errors += 1
        if errors > 0:
            quit()

def make_gradient_values_list(c1, c2, n):
    l = list()
    delta = c2 - c1
    inc = delta / (n + 1)
    for i in range(1, n+1):
        l.append(round(c1 + (inc * i)))
    return l

def make_gradient_tuples_list(t1, t2, n):
    reds = make_gradient_values_list(t1[0], t2[0], n)
    greens = make_gradient_values_list(t1[1], t2[1], n)
    blues = make_gradient_values_list(t1[2], t2[2], n)
    # build the tuples in bgr order for opencv
    return [(blues[i], greens[i], reds[i]) for i in range(0, len(reds))]

# we build both distcontinuous and continuous (gradientized) lists, which
# will allow the option for one or the other at rendering time
def normalize_colorlists():

    for k in cfg.colorspecs:

        spec = cfg.colorspecs[k]

        if spec['type'] == 'list':

            l_spec = len(spec['tuplist'])
            # l_space is the number of frames between colors on the list mapped
            # to the number of frames, e.g., if we have 360 frames and 36 colors,
            # then l_space will be 9, which we will use later on to generate the
            # gradient between the specified colors
            l_space = int(cfg.n_frames / l_spec)

            # flip the list's GBR values to RGB to make a straight list
            newl = list()
            for i in range(len(spec['tuplist'])):
                c = spec['tuplist'][i]
                newl.append((c[2], c[1], c[0]))
            spec['original'] = newl

            # generate the discontinuous list
            newl = list()
            i_spec = 0
            i_space = 0
            for i_disc in range(cfg.n_frames):
                # important: build out our tuples in bgr order as needed by opencv
                c = spec['tuplist'][i_spec]
                newl.append((c[2], c[1], c[0]))
                # l_space would be zero for n_frames == 1, so we need to avoid modulo 0 case
                if l_space != 0:
                    i_space = (i_space + 1) % l_space
                    if i_space == 0:
                        i_spec = (i_spec + 1) % l_spec
            spec['discontinuous'] = newl

            # now the continuous one in "loop" format
            newl = list()
            l = len(spec['tuplist'])
            for i in range(l):
                # important: build out our tuples in bgr order as needed by opencv
                c = spec['tuplist'][i]
                newl.append((c[2], c[1], c[0]))
                newl.extend(make_gradient_tuples_list(spec['tuplist'][i], spec['tuplist'][(i+1)%l], l_space))
            while len(newl) < cfg.n_frames:
                i_random = random.randint(0,len(newl)-1)
                newl.insert(i_random, newl[i_random])
            while len(newl) > cfg.n_frames:
                i_random = random.randint(0,len(newl)-1)
                newl.pop(i_random)
            spec['smooth_loop'] = newl

            # and now out-and-back format
            newl = list()
            l = len(spec['tuplist'])
            for i in range(l-1):
                # important: build out our tuples in bgr order as needed by opencv
                c = spec['tuplist'][i]
                newl.append((c[2], c[1], c[0]))
                newl.extend(make_gradient_tuples_list(spec['tuplist'][i], spec['tuplist'][i+1], int(l_space/2)))
            # pop the last color spec onto the tuple list - that is our turn-back point
            c = spec['tuplist'][l-1]
            newl.append((c[2], c[1], c[0]))
            newl_copy = newl.copy()
            newl_copy.reverse()
            newl.extend(newl_copy)
            while len(newl) < cfg.n_frames:
                i_random = random.randint(0,len(newl)-1)
                newl.insert(i_random, newl[i_random])
            while len(newl) > cfg.n_frames:
                i_random = random.randint(0,len(newl)-1)
                newl.pop(i_random)
            spec['smooth_outandback'] = newl

        elif spec['type'] == 'gen':
            for n in cfg.colormodes:
                spec[n] = spec['tuplist']

def make_rgb_tuple(tupstr):

    try:
        tup = make_tuple(tupstr)
        if len(tup) != 3:
            return False, None, '"' + tupstr + '" does not have exactly three values'
        if not all(isinstance(v, int) for v in tup):
            return False, None, '"' + tupstr + '" contains non-integer values'
        if not all((0 <= v <= 255) for v in tup):
            return False, None, '"' + cstr + '" contains values out of the range 0 to 255'
    except BaseException:
        return False, None, '"' + tupstr + '" is incorrectly formatted - expecting "(int,int,int)"'

    return True, tup, ''

def add_colorspec(spec, filename):

    if 'name' not in spec:
        print('colorspec file ' + filename + ': colorspec name missing')
        return

    name = spec['name']

    if name in cfg.colorspecs:
        print('colorspec file ' + filename + ': colorspec with name "' + name + '" already defined')
        return

    if 'type' in spec:
        spectype = spec['type']
        if spectype != 'list' and spectype != 'gen':
            print('colorspec file ' + f + ': colorspec type "' + spectype + '" is not a valid type')
            return
    else:
        print('colorspec file ' + f + ': colorspec type missing, should be ''list'' or ''gen''')
        return

    if spectype == 'list':
        if not 'colors' in spec:
            print('colorspec with name "' + name + '" is missing a color list')
            return
        if not isinstance(spec['colors'], list):
            print('colorspec with name "' + name + '" is not a proprely formatted list')
            return
        if len(spec['colors']) > cfg.n_frames_max:
            print('colorspec with name "' + name + '" has too many colors (max allowed = ' + str(cfg.n_frames_max) + ')')
            return
        if len(spec['colors']) <= 0:
            print('colorspec with name "' + name + '" must have between 1 and ' + str(cfg.n_frames_max) + ' colors')
            return
        badc = 0
        tuplist = list()
        for cstr in spec['colors']:
            isgoodtup, tup, msg = make_rgb_tuple(cstr)
            if not isgoodtup:
                print('colorspec with name "' + name + '": invalid format in "' + cstr + '"')
                badc += 1
            else:
                tuplist.append(tup)
        if badc > 0:
            return
        spec['tuplist'] = tuplist

    if spectype == 'gen':
        lowstr = '(0,0,0)' if not 'lowrgb' in spec else spec['lowrgb']
        highstr = '(255,255,255)' if not 'highrgb' in spec else spec['highrgb']
        isgoodtup, lowtup, msg = make_rgb_tuple(lowstr)
        if not isgoodtup:
            print('colorspec with name "' + name + '": invalid format for lowrgb')
            return;
        isgoodtup, hightup, msg = make_rgb_tuple(highstr)
        if not isgoodtup:
            print('colorspec with name "' + name + '": invalid format for highrgb')
            return;
        tuplist = list()
        try:
            listlen = int(spec['listlen'])
        except:
            listlen = 16
        for n in range(listlen):
            tup = (random.randint(lowtup[0], hightup[0]), \
                           random.randint(lowtup[1], hightup[1]), \
                           random.randint(lowtup[2], hightup[2]))
            tuplist.append(tup)
        spec['tuplist'] = tuplist

    cfg.colorspecs[name] = spec

def add_profile(spec, filename):

    if 'name' not in spec:
        print('profile file ' + f + ': profile name missing')
        return

    name = spec['name']

    if name in cfg.profiles:
        print('profile file ' + f + ': profile with name "' + name + '" already defined')
        return

    cfg.profiles[name] = spec

def get_profile_value(profilename, level):
    if level > 7:
        level = 7
    if profilename not in cfg.profiles:
        print("profile " + profilename + " not found")
        return -1
    v = random.randint(1, 100)
    for i in range(0,7):
        if v <= cfg.profiles[profilename]['sums'][str(level)][i]:
            return i
    # SHOULD NEVER GET HERE
    print("failed to get profile value for profile " + cfg.profiles[profilename]['name'])
    return 3

def gen_profile_values(jtree, profilename, attrname):
    fam = [jtree]
    while len(fam) > 0:
        node = fam.pop()
        node[attrname] = get_profile_value(profilename, node['level'])
        fam += node.get('children', [])

def propogate_profile_values(jtree, profilename, attrname, attrpropiters):
    for i in range(0,attrpropiters):
        fam = [jtree]
        while len(fam) > 0:
            node = fam.pop()
            if (node['parent'] != None) and ('children' in node):
                parentv = node['parent'][attrname]
                for c in node['children']:
                    if (c[attrname] < parentv) and (parentv >= 4):
                        c[attrname] += 1
                    elif (c[attrname] > parentv) and (parentv <= 2):
                        c[attrname] -= 1 
            fam += node.get('children', [])

# here we override the specified (or default) number of frames if it is less than
# the explicit (not interpolated/gradientized) length of the longest colorspec;
# the exception is if n_frames is preset to 1, which suggests the caller is interested
# in only a single frame for the purposes of generating a static file set for navigation
def set_normalized_n_frames():
    if cfg.n_frames == 1 or cfg.framesfirm:
        return
    n = 0
    for k in cfg.colorspecs:
        spec = cfg.colorspecs[k]
        if 'tuplist' in spec and len(spec['tuplist']) > n:
            n = len(spec['tuplist'])
    cfg.n_frames = max(n, cfg.n_frames)

# calculate and store the distances from a parent's center to the child's
# outer radius, for a circle of r = 1; then when needed for a particular
# family, get_r_crowded scales up the tether value
class Tethers:

    min_children = 1
    max_children = 10000 # perhaps this is the licensing basis :-)

    t_values = [None] * (max_children + 1)
    for n in range(min_children, max_children + 1):
        deg = (((n-2)*180)/n)/2
        cos = math.cos(math.radians(deg))
        t_values[n] = ((1 - cos) / (cos + 1))
    # rigorously speaking, the tether for a single child goes inward
    t_values[1] = -1

    @staticmethod
    def get_tether(n, outerr=1):
        t = Tethers.t_values[n] * outerr
        childr = ((outerr - t) / 2)
        return t, childr

def get_r_crowded (r_snug):
    return int(r_snug + (((cfg.chan_width + 3) / 2) if cfg.chan_width > 0 else 0))

def place_children(punit, radial_offset, curchilddepth):

    if curchilddepth > cfg.maxchilddepth:
        return

    # change the angle of the root
    if punit['parent'] == None:
        punit['angle'] = radial_offset

    if 'angle' not in punit:
        punit['angle'] = radial_offset

    fam = punit.get('children', [])
    n_uncentered_children = punit['n_uncentered_children']

    if n_uncentered_children == 0:
        return

    if n_uncentered_children > Tethers.max_children:
        print('too many children [' + str(n_uncentered_children) + '] specified - max is ' + str(Tethers.max_children) + ' (excluding a centered child, if any)')

    punit['tether_snug'], punit['r_child_snug'] = Tethers.get_tether(n_uncentered_children, punit['r_snug'])
    punit['orbit_snug'] = punit['tether_snug'] + punit['r_child_snug']
    punit['r_child_crowded'] = get_r_crowded (punit['r_child_snug'])
    punit['tether_crowded'] = punit['r'] - (punit['r_child_crowded'] * 2)
    punit['orbit_crowded'] = punit['r_child_crowded'] + punit['tether_crowded']

    # we alternately reverse the rotational direction based on level, so adjacent levels
    # rotate counter to each other, but only if we're generating multiple frames
    if cfg.n_frames > 1:
        child_radial_offset = (abs(radial_offset) * (1 if punit['level'] % 2 == 1 else -1) * (punit['level'] + 1))
    else:
        child_radial_offset = radial_offset

    if punit['centered_i'] != -1:
        # set up this central child's x,y, then (per conditions above) we treat it as a parent
        # and subject to this very routine
        # note that in subsequent iterations on the main parent's children, we need to exclude
        # the central child (which is also a parent) from the iteration's effect
        # other than that, the objective here is to prep the centered child as a parent and
        # recurse on this function that we are presently within
        cchild = fam[punit['centered_i']]
        cchild['x'] = punit['x']
        cchild['y'] = punit['y']
        cchild['r_snug'] = punit['tether_snug']
        cchild['r'] = get_r_crowded(cchild['r_snug'])
        cchild['r_body'] = cchild['r'] - cfg.chan_width
        cchild['r_eye'] = int(cchild['r'] * cfg.r_eye_scale)
        cchild['renderable'] = renderable(cchild)
        # note that we still place the children even if our radius is too small (or even negative)
        # for now, we'll let the render functions sort it out (2023-04-03: this may bite us, at which
        # point we'll take a different approach)
        place_children(cchild, child_radial_offset, curchilddepth)

    # use radians
    theta = (2 * math.pi) / n_uncentered_children

    # all angles, given n children
    angles = [(i * theta) + radial_offset for i in range(n_uncentered_children)]

    l = len(fam)
    nrendered = 0

    for i in range(l):

        child = fam[i]

        # check for the special case here of child position:central
        if child['position'] == 'center':
            continue

        angle = angles[nrendered]
        child['angle'] = angle

        # calculate two different sets of (r, (x,y)):
        # - one for the "snug" configuration - do we need it downstream?
        # - one for the "crowded" configuration, which is what we will render
        # Note that in the special case of chan_width = 0, the snug and
        # crowded values for r are identical, since it is the accounting for
        # the channel width that shifts the rendering r from a snug position
        # to the crowded position closer to the parent's center; in other words
        # rendering the snug configuration is the same as rendering the r_crowded
        # configuration with channel width = 0; because of this, we simplify the
        # naming of the crowded-related keys to simply r, x, y rather than
        # r_crowded, etc.

        child['r_snug'] = punit['r_child_snug']
        child['x_snug'] = (punit['orbit_snug'] * math.cos(angle)) + punit['x']
        child['y_snug'] = (punit['orbit_snug'] * math.sin(angle)) + punit['y']
        child['r'] = punit['r_child_crowded']
        child['x'] = (punit['orbit_crowded'] * math.cos(angle)) + punit['x']
        child['y'] = (punit['orbit_crowded'] * math.sin(angle)) + punit['y']
        child['r_body'] = child['r'] - cfg.chan_width
        child['renderable'] = renderable(child)

        if not cfg.fill_body_only:
            child['x_fill_vanguard'] = ((punit['r_body'] - child['line_thickness'] - 5) * math.cos(angle-(theta/2))) + punit['x']
            child['y_fill_vanguard'] = ((punit['r_body'] - child['line_thickness'] - 5) * math.sin(angle-(theta/2))) + punit['y']
            cvdist = calculate_distance ((child['x'], child['y']), (child['x_fill_vanguard'], child['y_fill_vanguard']))
            # note there is no "governor" if channel  - parentnode_line_thickness <= 0 - in which case we still compute
            # but set a flag to indicate governor absence 
            child['has_gov'] = cfg.chan_width - child['line_thickness'] >= 1
            child['x_fill_gov'] = child['x'] + (child['x_fill_vanguard'] - child['x']) * ((child['r_body'] + child['line_thickness'] + 1) / cvdist)
            child['y_fill_gov'] = child['y'] + (child['y_fill_vanguard'] - child['y']) * ((child['r_body'] + child['line_thickness'] + 1) / cvdist)

        place_children(child, child_radial_offset, curchilddepth+1)

        # we defer calcuation of this child's eye radius until its children have been placed
        # so that we can limit this child's eye radius to be within its own tether_crowded range,
        # otherwise this child's eye would overlap its children's halos
        child['r_eye'] = int(child['r'] * cfg.r_eye_scale)
        if child['r_eye'] < 5:
            child['r_eye'] = min(5, int(child['r']/2))

        nrendered += 1

    return punit

def get_tagpath(jnode):
    tagpath = ''
    ptr = jnode
    while ptr != None:
        tag = ptr['tag'] if 'tag' in ptr else 'untagged'
        tagpath = tag + (cfg.tagpath_sep + tagpath if tagpath != '' else '')
        ptr = ptr['parent']
    return tagpath

def calculate_distance(p1, p2):
    return ((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2) ** 0.5

def set_parent_refs(punit, setToNone=False):
    fam = punit.get('children', [])
    for child in fam:
        # note: parent needs to be null when writing to json file, otherwise it gets traversed!
        if setToNone:
            child['parent'] = None
        else:
            child['parent'] = punit
        child['level'] = punit['level'] + 1
        set_parent_refs(child, setToNone)

def set_tag_slugs(punit):
    punit['slug'] = re.sub('[\W_]+', '', punit['tag'])
    fam = punit.get('children', [])
    for child in fam:
        child['slug'] = re.sub('[\W_]+', '', child['tag'])
        set_tag_slugs(child)

def expand_colorbursts(punit):

    if cfg.nocolorburst:
        return

    # easier if it is already in the structurem even if not in the source
    if 'options' not in punit:
        punit['options'] = []

    # we do not burst any node that has existing children, even if "colorburst" option is present
    if len(punit.get('children', [])) > 0:
        fam = punit.get('children', [])
        for child in fam:
            expand_colorbursts(child)
        return
    if 'colorburst' not in punit['options']:
        return

    # initialize the "children" list and add a dict for each child (each color)
    punit['children'] = []
    for i in range(len(punit['colorlist'])):
        # TODO the createion of the child's dict has gotten out of hand here and needs
        #      to be encapsulated
        punit['children'].append({'tag': punit['tag'] + str(i), 'slug': punit['slug'] + str(i),
                                  'colorlist': punit['colorlist'], 'level': punit['level'] + 1,
                                  'parent': punit, 'bgr_index': i})

# traverse the tree from the top down, ensuring that we have processed a child's
# parent's colorlistname setting before checking/setting the child's, making
# inheritance simple
def propagate_colordeets(punit):

    if 'options' not in punit:
        punit['options'] = []

    # make sure we have a valid colorlistname for this node, as it can be inherited
    if 'colorlistname' not in punit:
        if cfg.randomcolorlists:
            cln = "braintish"
            while 'norandom' in cfg.colorspecs[cln]:
                cln = random.choice(list(cfg.colorspecs))
            punit['colorlistname'] = cln
        elif punit['level'] == 0:
            punit['colorlistname'] = cfg.colorlistname
        else:
            # safe to do because we hit each node from the top down
            punit['colorlistname'] = punit['parent']['colorlistname']
    if punit['colorlistname'] == "<tag>":
        punit['colorlistname'] = punit['tag']
    if punit['colorlistname'] not in cfg.colorspecs:
        punit['colorlistname'] = 'default'

    # make sure we have a valid colormode for this node, as it can be inherited
    if 'colormode' not in punit:
        if punit['level'] == 0:
            if 'colormode' not in punit:
                punit['colormode'] = cfg.colormode
        else:
            # safe to do because we hit each node from the top down
            punit['colormode'] = punit['parent']['colormode']

    if punit['colormode'] not in cfg.colormodes:
        punit['colormode'] = cfg.colormode

    # assume all available color lists have a variation for each color mode
    punit['colorlist'] = cfg.colorspecs[punit['colorlistname']][punit['colormode']]

    # propagate foundry_eyecolor
    if 'foundry_eye_color' not in punit and 'parent' in punit and punit['parent'] != None and 'foundry_eye_color' in punit['parent']:
        punit['foundry_eye_color'] = punit['parent']['foundry_eye_color']

    fam = punit.get('children', [])
    for child in fam:
        propagate_colordeets(child)

def set_line_attributes(punit):

    fam = punit.get('children', [])
    l = len(fam)    

    if 'line_thickness' not in punit:
        if punit['level'] == 0 or l == 0:
            punit['line_thickness'] = cfg.leafnode_line_thickness
        else:
            punit['line_thickness'] = cfg.parentnode_line_thickness

    if 'line_color' not in punit:
        if punit['level'] == 0 or l == 0:
            punit['line_color'] = cfg.leafnode_line_color
        else:
            punit['line_color'] = cfg.parentnode_line_color
    
    for child in fam:
        set_line_attributes(child)

# during this traverse, we attribute to each node its number of children, but
# in two parts: (i) the number of children in orbit (the default placement), and
# (ii) the index of the centered child, if any
def set_children_counts(punit):
    if 'options' not in punit:
        punit['options'] = []
    fam = punit.get('children', [])
    punit['n_uncentered_children'] = 0
    punit['centered_i'] = -1
    if len(fam) == 0:
        return
    for i in range(len(fam)):
        child = fam[i]
        if 'position' in child:
            if child['position'] == 'center':
                if punit['centered_i'] == -1:
                    punit['centered_i'] = i
                else:
                    print(child['tag'] + ' is vying for central position already occupied by ' + fam[punit['centered_i']]['tag'])
        else:
            # do this so that subsequently we can assume and not have to test for presence of 'position' key
            child['position'] = 'normal'
        if child['position'] == 'normal':
            punit['n_uncentered_children'] += 1
        set_children_counts(child)

def renderable(node):
    return True
    if 'hidden' in node['options'] or node['r'] < cfg.min_r_to_render:
        if node['r'] < cfg.min_r_to_render:
            if node['r'] < cfg.actual_min_r:
                cfg.actual_min_r = node['r']
            cfg.fully_renderable = False
        return False
    if node['r'] > cfg.actual_max_r:
        cfg.actual_max_r = node['r']
    return True

# order of traversal is important, since child areas will overlap their parent areas,
# and per spec, the overlapped area that is first specified in the image map takes
# precedence, therefore process the tree from the bottom up
def gen_imagemapdeets(node, map):
    fam = node.get('children', [])
    nchildren = len(fam)
    for i in range(nchildren):
        gen_imagemapdeets(fam[i], map)
    if 'href' not in node:
        node['href'] = node['slug'] + '.html'
    node['imagemaparea'] = \
        '<area alt="' + node['tag'] + '" title="' + node['tag'] + '" href="' + node['href'] + \
        '" coords="' + str(node['x']) + ',' + str(node['y']) + ',' + str(node['r'] - cfg.chan_width) + ' " shape="circle"/>'
    if node['parent'] != None:
        parent = node['parent']
        node['imagemaparea'] += \
            '<area alt="' + parent['tag'] + '" title="' + parent['tag'] + '" href="' + parent['slug'] + ".html" + \
            '" coords="' + str(node['x']) + ',' + str(node['y']) + ',' + str(node['r']) + ' " shape="circle"/>'
    map.append(node['imagemaparea'])

def gen_imagemap(jnode, imgname):
    map = []
    mapname = imgname + '-map'
    map.append('<img src="' + imgname + '" usemap="#' + mapname + '">')
    map.append('<map name="' + mapname + '">')
    gen_imagemapdeets(jnode, map)
    map.append('</map>')
    map.append('</img>')
    return map

def write_imagemap(node, render_dir, radial_offset_str):
    if node['level'] >= cfg.maxlevel:
        return
    # in order to generate a complete set of htmls with their respective image maps,
    # all within a closed set, we need to do so for each node
    # TODO: each node's html / image map will need a link to return to its parent
    imgmap_file = render_dir + '/' + node['slug'] + '.html'
    with open(imgmap_file, 'w') as f_imgmap:
        f_imgmap.write(' '.join(gen_imagemap(node, 'flooded_' + node['slug'] + '_' + radial_offset_str + '.png')))

def render_body(img, node):
    if node['level'] >= cfg.maxlevel:
        return
    try:
        seed = (int(node['x']), int(node['y']))
        cv2.circle(img, seed, int(node['r']), node['line_color'], node['line_thickness'])
        cv2.circle(img, seed, int(node['r_body']), node['line_color'], node['line_thickness'])
    except:
        pass

def render_medallion(mainimg, node, medallionname, medallionsdir, radius_adjust=0, angle_adjust=0, rate_adjust=1.0):
    #if 'children' in node:
    #    return
    t = node['tag']
    if '.7.' in t or '.8.' in t or '.9.' in t or '.10.' in t:
        return
    r = node['r_body'] + radius_adjust
    medallionimg = cv2.imread(cfg.medallionsdir + "/" + medallionname, cv2.IMREAD_UNCHANGED)
    if medallionimg is None:
        medallionimg = cv2.imread(cfg.medallionsdir + "/default.png", cv2.IMREAD_UNCHANGED)
    
    resized = cv2.resize(medallionimg, (r*2, r*2), interpolation=cv2.INTER_AREA)
    rot_mat = cv2.getRotationMatrix2D((r, r), (rate_adjust * math.degrees(node['angle'])) + angle_adjust, 1.0)
    rotated = cv2.warpAffine(resized, rot_mat, resized.shape[1::-1], flags=cv2.INTER_LINEAR)
    overlay_rgb = rotated[:, :, 0:3]
    alpha_channel = rotated[:, :, 3] / 255.0
    topleft_x = int(node['x']) - r
    topleft_y = int(node['y']) - r
    overlay_height, overlay_width = r*2, r*2
    # Extract the region of interest (ROI) from the background
    roi = mainimg[topleft_y:topleft_y + overlay_height, topleft_x:topleft_x + overlay_width]
    # Blend the overlay with the background using the alpha channel
    for c in range(0, 3):
        roi[:, :, c] = (alpha_channel * overlay_rgb[:, :, c] + (1 - alpha_channel) * roi[:, :, c])
    # Update the background with the modified ROI
    mainimg[topleft_y:topleft_y + overlay_height, topleft_x:topleft_x + overlay_width] = roi

def render_eyes_cv2(img, node):
    if node['level'] >= cfg.maxlevel:
        return
    if not renderable(node):
        return;
    if (('children' not in node) or (('children' in node) and (len(node['children']) == 0))):
        seed = (int(node['x']), int(node['y']))
        cv2.circle(img, seed, int(node['r_eye']), node['line_color'], node['line_thickness'])
        # NOTICE: THIS IS REQUIRED AS A FACTOR IN intqoin UNIQUENESS
        if 'foundry_eye_color' in node:
            isgoodtup, eyecolor, msg = make_rgb_tuple(node['foundry_eye_color'])
        else:
            eyecolor = cfg.eyecolor
        cv2.floodFill(img, None, seedPoint=seed, newVal=eyecolor, loDiff=cfg.floodFill_loDiff, upDiff=cfg.floodFill_hiDiff)

# determine the child whose governor (flood point) is closed to the parent's
# governor, so that we can match the parent's color to the nearest child's (awwww)
def determine_cradled_child(parent):
    if cfg.fill_body_only:
        return
    d = parent['r'] * 5 # exaggerated initial value to guarantee hit on at least the first child
    cradled_child = None
    for child in parent['children']:
        child_d = calculate_distance((parent['x_fill_gov'], parent['y_fill_gov']), (child['x'], child['y']))
        if child_d < d:
            d = child_d
            cradled_child = child
    return cradled_child

def apply_body_colors(img, node, thisframe=-1):

    # if we've already set a color for this node in another frame,
    # and if stickycolors is not True, simply
    # bump the node's index into its colorlist, otherwise select a random
    # index
    if 'bgr_index' in node:
        # this is a hot fix and needs to be addressed differently; within the generation of
        # one SET of related HTML files, we want a node to always have the same color so that
        # it is consistent when zooming in/out; for now, we will impose this condition when
        # cfg.frames = 1; for other cases (i.e., in which rotating GIFs are of interest),
        # we need to restructure how we track where we are at within the file / subtree / iteration
        # loops
        if cfg.n_frames > 1 and not cfg.stickycolors:
            node['bgr_index'] = (node['bgr_index'] + 1) % len(node['colorlist'])
    elif cfg.randcolorstart:
        node['bgr_index'] = random.randint(0,len(node['colorlist'])-1)
    else:
        node['bgr_index'] = 0

    bgr = node['colorlist'][node['bgr_index']]
    node['bgr'] = bgr

    if 'winwincoeff' in node and node['winwincoeff'] < 3:
        bgr = cfg.colorspecs['winwincoeff']['original'][node['winwincoeff']]

    fam = node.get('children', [])

    # below we check if a node is renderable, but even if not, we calculate it's family's colors
    if len(fam) > 0:
        for child in fam:
            apply_body_colors(img, child, thisframe)

    if not renderable(node):
        return

    if node['level'] >= cfg.maxlevel:
        return

    # if this node has children, we only flood its vanguard

    if len(fam) > 0:
        # flood the governor with the current cradled child's color
        if node['level'] > 0 and 'x_fill_vanguard' in node and not cfg.fill_body_only:
            seed = (int(node['x_fill_vanguard']), int(node['y_fill_vanguard']))
            cradled_child = determine_cradled_child(node)
            if cradled_child != None:
                bgr = cradled_child['bgr']
                cv2.floodFill(img, None, seedPoint=seed, newVal=bgr, loDiff=cfg.floodFill_loDiff, upDiff=cfg.floodFill_hiDiff)
    else:
        seed = (int(node['x'] + (cfg.chan_width/2)), int(node['y'] + (cfg.chan_width/2)))
        cv2.floodFill(img, None, seedPoint=seed, newVal=bgr, loDiff=cfg.floodFill_loDiff, upDiff=cfg.floodFill_hiDiff)
        if (not cfg.fill_body_only) and (node['parent'] != None) and (len(node['parent']['children']) > 1):
            seed = (int(node['x_fill_gov']), int(node['y_fill_gov']))
            cv2.floodFill(img, None, seedPoint=seed, newVal=bgr, loDiff=cfg.floodFill_loDiff, upDiff=cfg.floodFill_hiDiff)
            seed = (int(node['x_fill_vanguard']), int(node['y_fill_vanguard']))
            cv2.floodFill(img, None, seedPoint=seed, newVal=bgr, loDiff=cfg.floodFill_loDiff, upDiff=cfg.floodFill_hiDiff)

def do_dynamic(img, node, root, thisframe):
    if 'isdynamiccandidate' not in node:
        return
    waittime = random.randint(1, cfg.dmf)
    # first time through?  wait a random number of frames
    if 'timer' not in node:
        node['timer'] = waittime
        node['elected'] = False
        return
    # not the first time through; first decrement our counter
    node['timer'] -= 1
    # are we in a waiting loop and still counting?  then not yet ...
    if node['timer'] > 0 and not node['elected']:
        return
    # are we at the end of the wait loop and ready for nomination?
    if node['timer'] == 0 and not node['elected']:
        # do we "win" the vote?
        if random.random() > root['foundry_dynamic_medallion_probability']:
            # A: No
            node['timer'] = waittime
            return
        else:
            # A: Yes - reset our counter, note the victory, and fall through
            node['timer'] = cfg.dmf
            node['elected'] = True
            if 'angle_adjust' in node:
                del node['angle_adjust']
    elif node['timer'] == 0 and node['elected']:
        # term limit reached
        node['elected'] = False
        node['timer'] = waittime
        if 'angle_adjust' in node:
            del node['angle_adjust']
        return
    
    if thisframe + cfg.dmf >= cfg.n_frames:
        # not enough frames left to render the medallion's full lifecycle, so simply return
        return
    
    # conclusion: we are in an elected state and our term has not run the clock, so show our face
    if 'angle_adjust' not in node:
        node['angle_adjust'] = random.randint(0, 180)
    medname = root['foundry_dynamic_medallion_name'] + ("000"+str(node['timer']))[-2:] + ".png"
    render_medallion(img, node, medname, cfg.medallionsdir, angle_adjust = node['angle_adjust'], rate_adjust=-0.67)

def render_tags(img, node):

    if node['level'] >= cfg.maxlevel:
        return

    fam = node.get('children', [])

    if len(fam) > 0:
        for child in fam:
            render_tags(img, child)
        return

    if not renderable(node):
        return

    if (node['tag'][0:1] == '-' and (not cfg.hiddentags)):
        return

    TEXT_FACE = cv2.FONT_HERSHEY_DUPLEX
    #TEXT_SCALE = 1.5 * (cfg.r / 400)
    TEXT_SCALE = 0.5
    TEXT_THICKNESS = 1
    TEXT = node['tag']

    text_size, _ = cv2.getTextSize(TEXT, TEXT_FACE, TEXT_SCALE, TEXT_THICKNESS)
    text_origin = (int(node['x'] - text_size[0] / 2), int(node['y'] - (node['r_eye'] * 3)))

    cv2.putText(img, TEXT, text_origin, TEXT_FACE, TEXT_SCALE, (32,32,32), TEXT_THICKNESS, cv2.LINE_AA)

# TODO: maybe buffer all of the png files rather than writing them and rereading them
def make_gif(path):
    gif_frames = []
    imgs = glob.glob(path + '*.png')
    for i in imgs:
        new_frame = Image.open(i)
        gif_frames.append(new_frame)
    # Save into a GIF file that loops forever
    gif_frames[0].save(path +'.gif', format='GIF', append_images=gif_frames[1:], save_all=True, duration=int(1000 / cfg.fps), loop=0)

# return a list of the dicts within the given tree whose "tag" attribute matches
# the given search tag
def findtag(jtree, searchtag, taglist):
    if "tag" in jtree and jtree["tag"] == searchtag:
        taglist.append(jtree)
    if "children" in jtree:
        for c in jtree["children"]:
            findtag(c, searchtag, taglist)

def load_recursive(jf, curlvl, maxlvl):

    try:
        jtree = json.load(open(jf))
    except Exception as e:
        print("failed to load file " + jf + ": "+ str(e))
        return None
    
    return jtree

def render_subtree(subtree):

    subtree['r_snug'] = cfg.r #############if not 'r' in subtree else subtree['r']
    # note that while the 'r' config parameter indicates the radius in the center of the channel,
    # within the code we use 'r' consistently throughout to mean the most interesting 'r', which is that
    # of the outer radius of overlapping (crowded) circles (earlier code versions named this "r_halo")
    subtree['r'] = get_r_crowded(subtree['r_snug'])
    if cfg.center:
        subtree['x'] = int(cfg.pgwidth / 2)
        subtree['y'] = int(cfg.pgheight / 2)
    else:
        subtree['x'] = cfg.margin + subtree['r']
        subtree['y'] = subtree['x']
    subtree['x0'] = subtree['x']
    subtree['r_body'] = subtree['r'] - cfg.chan_width
    subtree['r_eye'] = int(subtree['r'] * cfg.r_eye_scale)
    subtree['colorlistname'] = cfg.colorlistname
    subtree['angle'] = 0.0

    leaf_base = subtree['slug']
    wireframe_leaf_base_path = cfg.run_dir + '/' + cfg.name + '/' + leaf_base
    flooded_leaf_base_path = cfg.run_dir + '/' + cfg.name + '/flooded_' + leaf_base
    imgmap_iter = random.randint(0,cfg.n_frames-1)

    thisframe = 0

    for radial_offset in cfg.radial_offset_list:

        radial_offset_str = str(int(radial_offset*100)).zfill(3)
        wireframe_leaf_base_path_radial = wireframe_leaf_base_path + '_' + radial_offset_str
        flooded_leaf_base_path_radial = flooded_leaf_base_path + '_' + radial_offset_str

        place_children(subtree, radial_offset, 1)

        # it's effin 2025, i've been trying to get to this for months, and so right now I will accept the apparent laziness underneath
        # which is a sense of expediency. plus my coding brain is rusty. ugh.  if the user asks for a fully renderable result, the code
        # should scale up the entire structure and proceed, however, for now, we are just barfing out a message when full renderability
        # is requested but not achieved, and give the user guidance on how to scale up the canvas size
        # and even that guidance is insufficient ... :-O
        if cfg.render_fully and not cfg.fully_renderable:
            print("not renderable as requested, smallest r = " + str(cfg.actual_min_r) + ", subtree[r] = " + str(subtree['r']) + ", rerun with R > " + str(subtree['r'] * (cfg.min_r_to_render / cfg.actual_min_r)))
            quit()

        # Creating a image with 3 channels RGB and unsigned int datatype
        img = numpy.full((cfg.pgheight, cfg.pgwidth, 4), 0, dtype = "uint8")

        fam = [subtree]
        while len(fam) > 0:
            jnode = fam.pop()
            if cfg.medallions:
                render_body(img, jnode)
                # TODO need to abstract medallionname out of CFG for more dynamic specification
                render_medallion(img, jnode, cfg.medallionname, cfg.medallionsdir)
            else:
                render_body(img, jnode)
            fam += jnode.get('children', [])

        # at this point wireframe rendering is completed, so save it
        png_path = wireframe_leaf_base_path_radial + '.png'
        if not cv2.imwrite(png_path, img):
            print("IMAGE WRITE FAILED - QUITTING")
            quit()

        if not cfg.medallions:

            # starting here we add color for various reasons

            img = cv2.imread(png_path)

            # color the elements per the color specs
            # TODO: find out why we are writing then rereading - does writing
            #       make the img object unusable for futher modification?

            if not cfg.noflood:
                apply_body_colors(img, subtree)
            if cfg.tags:
                render_tags(img, subtree)

            fam = [subtree]
            while len(fam) > 0:
                jnode = fam.pop()
                render_eyes_cv2(img, jnode)
                do_dynamic(img, jnode, subtree, thisframe)
                fam += jnode.get('children', [])

        # stamp this baby
        render_medallion(img, subtree, subtree['foundry_medallion_name'], cfg.medallionsdir, subtree['foundry_medallion_frame_thickness'], rate_adjust=-2.0)

        png_path = flooded_leaf_base_path_radial + '.png'
        cv2.imwrite(png_path, img)

        if thisframe == imgmap_iter:
            write_imagemap(subtree, cfg.render_dir, radial_offset_str)

        thisframe += 1

    # Create the frames
    make_gif(wireframe_leaf_base_path)
    #if not cfg.medallions:
    make_gif(flooded_leaf_base_path)

def render_all_subtrees(jtree):
    cfg.maxlevel = jtree['level'] + cfg.clickdepth
    render_subtree(jtree)

def copynode(n):
    p = n['parent']
    if 'children' in n:
        c = n['children']
        del n['children']
    else:
        c = None
    n['parent'] = None
    newn = copy.deepcopy(n)
    n['parent'] = p
    #newn['parent'] = p
    if c != None:
        n['children'] = c
    #    newn['children'] = c
    return newn

def fan_out_leafs(lists, maxrix):
    addlpodsperlvl = 6
    podsize = 1
    b = maxrix * addlpodsperlvl * podsize
    nb = 1
    t = len(lists[maxrix])
    while (b * nb) + ((((nb - 1) * (nb)) / 2) * addlpodsperlvl * podsize) < t:
        nb += 1
    nx = (nb * (nb - 1)) / 2
    bp = b / t
    x = math.ceil((t - (nb * b)) / nx)
    xp = x / t
    sizes = [0] * nb 
    for r in range(0,nb):
        rp = (bp + (xp * r))
        sizes[r] = int(rp * t)
    sizes[nb-1] = t - sum(sizes[0:nb-1])
    newlists = [None] * nb
    base = 0
    for r in range(0,nb):
        newlists[r] = lists[maxrix][base:(base + sizes[r])]
        base += len(newlists[r])
    del lists[maxrix]
    for r in range(0, nb):
        lists[maxrix+r] = newlists[r]
    return lists, maxrix - 1 + nb

def flatten(jtree):
    
    # -- initialize dictionary of lists - each member list will contain all nodes at the same level
    #    regardless of parentage; the exception will be that all leaf nodes
    #    will be on the same list and rendered together at the "edge"
    # -- initialize lists['edge'] to empty list
    # -- walk the tree and COPY each member to "lists[node['level']]", except if
    #    a node has no children, add it to "lists['edge']"
    # -- this is a good point at which to round up the length of each list to
    #    the min number of children for presentation, by adding invisible children (eggs?)
    # -- "rename" lists['edge'] to lists['<max-level-plus-1>'] to simplify iteration
    # -- initialize the flattened tree dict and set curptr to it
    # -- iterate from highest to lowest level:
    #    - add "tag":lvl to curptr
    #    - add lists[lvl] as children to curptr
    #    - set "position":"inner"
    #    - set each child's parent to curptr
    #    - set each child's 
    #    - bump curptr to the new tag
    # -- return the new tree

    lists = {}
    lists['edge'] = []
    maxrix = -1
    
    nodes = [jtree]
    while len(nodes) > 0:
        node = nodes.pop()
        lvl = node['level']
        if lvl not in lists:
            lists[lvl] = []
        if 'children' not in node:
            if node['level'] > 3:
                lists['edge'].append(copynode(node))
            else:
                lists[lvl].append(copynode(node))
        else:
            if ('position' not in node) or (node['position'] != "center"):
                lists[lvl].append(copynode(node))
                if lvl > maxrix:
                    maxrix = lvl
            children = node.get('children', [])
            if len(children) > 0:
                nodes += children
    maxrix += 1
    lists[maxrix] = lists['edge']
    del lists['edge']

    # now build the new hierarchical structure, which is a recursively nested set of lists
    # of children; remember from above that we have our own copy of all of the nodes
    ftree = {}
    ftree['parent'] = None
    ftree['level'] = 0
    rings = []
    thisring = ftree
    spacercount = 0

    for rix in range(maxrix, -1, -1):
        thisring['tag'] = "ring" + str(rix)
        thisring['position'] = "center"
        thisring['children'] = lists[rix]
        # round up to min layout children, except for the innermost, which stands alone;
        # this should impact only the several innermost rings, i.e., top-level mgmt
        if rix > 32767:
            for j in range(len(lists[rix]) + 1, cfg.minflatchildren + 1):
                thisring['children'].append({
                    "tag": "spacer" + str(spacercount),
                    "level": rix
                })
                spacercount += 1
        for child in thisring['children']:
            child['parent'] = thisring
            child['level'] = rix
        # track the tether, as we will need it when determining flattened's R
        thisring['tether'] = Tethers.get_tether(len(thisring['children']))
        # create the container for the next innermost set of nodes
        # unless we're at origin
        if rix > 0:
            thisring['children'].append({})
            # get the pointer to the just-created container
            newring = thisring['children'][-1]
            newring['parent'] = thisring
            newring['level'] = rix
            if rix == 22:
                newring['line_thickness'] = 5
            rings.insert(0, thisring)
            thisring = newring

    rings[0]['r'] = cfg.min_r_to_render
    ftree['geometry'] = "flattened"

    # now size from the inside-out; we seeded origin's r above so we can assume
    for i in range(1, maxrix):
        rings[i]['r'] = rings[i-1]['r'] + cfg.min_r_to_render
        tether, childr = Tethers.get_tether(len(rings[i]['children']), rings[i]['r'])
        if tether > rings[i-1]['r']:
            childr = rings[i-1]['r'] / tether
            rings[i-1]['r'] = tether
        rings[i]['r'] = rings[i-1]['r'] + childr

    return ftree, rings, lists

def do_variant(tree):
    set_tag_slugs(tree)
    propagate_colordeets(tree)
    set_line_attributes(tree)
    expand_colorbursts(tree)
    set_children_counts(tree)
    if cfg.attrpropiters > 0:
        gen_profile_values(tree, 'bigorg', 'winwincoeff')
        propogate_profile_values(tree, 'bigorg', 'winwincoeff', cfg.attrpropiters)
    render_all_subtrees(tree)

#==========================================================================================
#==========================================================================================
#==========================================================================================

cfg.set_config()

if cfg.jfiles == '':
    print("specify input files with: --jfiles '<pattern>'")
    quit()

cfg.run_dir = str(pathlib.Path().resolve())

jfglob = glob.glob(cfg.jfiles)
if len(jfglob) == 0:
    print("no files matched the given jfiles pattern '" + cfg.jfiles + "'")
    quit()

cfg.render_dir = cfg.run_dir + '/' + cfg.name + '/'
os.mkdir(cfg.render_dir)

# if the build is for static pages rather than gifs, let's randomize the radial offset
# so that the result is not always aligned to zero
cfg.radial_offset_list = []
if cfg.n_frames == 1:
    cfg.radial_offset_list.append((random.randint(0,int(2*math.pi*100)-1))/100)
else:
    cfg.radial_offset_list = [num / 100 for num in list(range(0,int(2*math.pi*100),int(2*math.pi*100/cfg.n_frames)))]
    cfg.n_frames = len(cfg.radial_offset_list)
    if cfg.closure:
        cfg.radial_offset_list.append(628)

cfg.radialrestart = 0
if cfg.radialrestart > 0:
    cfg.radial_offset_list[:] = [x for x in cfg.radial_offset_list if x > cfg.radialrestart]

# process all json files in the current directory
for jf in jfglob:

    jtree = load_recursive(jf, 0, cfg.maxlevel)

    jtree['parent'] = None
    jtree['level'] = 0

    set_parent_refs(jtree)
    # TODO see comments at def
    for i in range(0,cfg.includesdepth):
        expand_includes(jtree)
        set_parent_refs(jtree)
    jtree['geometry'] = "normal"
    do_variant(jtree)
    if cfg.dumpjson:
        s = json.dumps(jtree, indent=2)
        print(s)
    if cfg.flatten:
        ftree, rings, lists = flatten(jtree)
        set_parent_refs(ftree)
        do_variant(ftree)
