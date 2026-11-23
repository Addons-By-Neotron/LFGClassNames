import bpy, bmesh, math, sys
from mathutils import Vector

OUT = sys.argv[sys.argv.index("--") + 1]

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

def mat(name, rgb, metal=0.0, rough=0.4, emit=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Metallic"].default_value = metal
    b.inputs["Roughness"].default_value = rough
    if emit:
        b.inputs["Emission Color"].default_value = (*rgb, 1)
        b.inputs["Emission Strength"].default_value = emit
    return m

def srgb(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)

def bevel(obj, width, segs=4):
    mod = obj.modifiers.new("bevel", "BEVEL")
    mod.width, mod.segments = width, segs
    mod.limit_method = "ANGLE"
    obj.data.polygons.foreach_set("use_smooth", [True] * len(obj.data.polygons))

def slab(name, loc, size, material, bev):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = (size[0] / 2, size[1] / 2, size[2] / 2)
    bpy.ops.object.transform_apply(scale=True)
    bevel(o, bev, 6)
    o.data.materials.append(material)
    return o

def prism(name, points, loc, depth, material, bev=0.03):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    verts = [bm.verts.new((x, y, 0)) for x, y in points]
    face = bm.faces.new(verts)
    ext = bmesh.ops.extrude_face_region(bm, geom=[face])
    for v in ext["geom"]:
        if isinstance(v, bmesh.types.BMVert):
            v.co.z += depth
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    scene.collection.objects.link(o)
    o.location = loc
    bevel(o, bev, 4)
    o.data.materials.append(material)
    return o

def circle_pts(r, n, rot=0.0):
    return [(r * math.cos(rot + 2 * math.pi * i / n), r * math.sin(rot + 2 * math.pi * i / n)) for i in range(n)]

def star_pts(r1, r2, n=5):
    pts = []
    for i in range(2 * n):
        r = r1 if i % 2 == 0 else r2
        a = math.pi / 2 + math.pi * i / n
        pts.append((r * math.cos(a), r * math.sin(a)))
    return pts

def plus_pts(a, b):
    return [(-b, a), (b, a), (b, b), (a, b), (a, -b), (b, -b), (b, -a), (-b, -a), (-b, -b), (-a, -b), (-a, b), (-b, b)]


def shield_pts(w=0.27, top=0.3, side=0.02, tip=-0.34, n=14):
    pts = [(-w, top), (w, top)]
    # down the right side, then round to the point and back up the left
    for i in range(n + 1):
        t = i / n
        a = t * math.pi / 2
        pts.append((w * math.cos(a), side + (tip - side) * math.sin(a)))
    for i in range(1, n + 1):
        t = i / n
        a = math.pi / 2 - t * math.pi / 2
        pts.append((-w * math.cos(a), side + (tip - side) * math.sin(a)))
    return pts[:2] + pts[2:-1]  # (the last point is the top left's side again)

def sword_pts(angle=math.radians(-45)):
    b, g, h, p = 0.055, 0.2, 0.035, 0.065
    raw = [(0, 0.4), (b, 0.3), (b, -0.02), (g, -0.02), (g, -0.08), (h, -0.08), (h, -0.26), (p, -0.26),
           (p, -0.33), (-p, -0.33), (-p, -0.26), (-h, -0.26), (-h, -0.08), (-g, -0.08), (-g, -0.02), (-b, -0.02),
           (-b, 0.3)]
    c, s_ = math.cos(angle), math.sin(angle)
    mid = (0.4 - 0.33) / 2  # (centred between the tip and the pommel)
    return [(x * c - (y - mid) * s_, x * s_ + (y - mid) * c) for x, y in raw]

def flame_pts(r=0.2, n=28):
    # a teardrop: round at the bottom, a curled point at the top
    pts = []
    for i in range(n + 1):
        a = -math.pi / 6 + (math.pi * 4 / 3) * i / n
        pts.append((r * math.cos(a + math.pi), -0.08 + r * math.sin(a + math.pi)))
    pts = [(x, y) for x, y in pts]
    pts.append((-0.06, 0.2))
    pts.append((0.04, 0.38))
    return pts

# a tooltip: dark, rounded, with a thin silver border
border = mat("border", srgb("#8d939e"), metal=1.0, rough=0.35)
dark = mat("panel", srgb("#0c111c"), rough=0.6)
slab("border", (0, 0, -0.06), (3.6, 2.9, 0.12), border, 0.16)
slab("panel", (0, 0, 0.0), (3.46, 2.76, 0.1), dark, 0.12)

white = mat("white", srgb("#f6f6f6"), rough=0.3)
text = mat("text", srgb("#e8e8e8"), rough=0.5, emit=0.3)
ROLE = {
    "healer": ("#2f9a3a", plus_pts(0.1, 0.035)),
    "tank": ("#2c63c8", [(x * 0.36, y * 0.36) for x, y in shield_pts()]),
    "dps": ("#b3262e", [(x * 0.32, y * 0.32) for x, y in sword_pts(math.radians(-45))]),
}
rows = [  # class colour, name length, class length, role
    ("#f4f4f4", 0.95, 0.65, "healer"),
    ("#c69b6d", 1.1, 0.75, "tank"),
    ("#3fc7eb", 0.85, 0.5, "dps"),
    ("#8788ee", 1.0, 0.75, "dps"),
]
for i, (color, name_len, class_len, role) in enumerate(rows):
    y = 0.93 - i * 0.62
    cm = mat("c%d" % i, srgb(color), rough=0.35, emit=0.35)
    # the class icon, a disc in its colour with a dark ring
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=0.17, depth=0.08, location=(-1.38, y, 0.08))
    o = bpy.context.object; bevel(o, 0.03, 4); o.data.materials.append(border)
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=0.13, depth=0.1, location=(-1.38, y, 0.09))
    o = bpy.context.object; bevel(o, 0.03, 4); o.data.materials.append(cm)
    # the name, in the class colour, then the class name
    x = -1.1
    slab("name%d" % i, (x + name_len / 2, y, 0.07), (name_len, 0.17, 0.05), cm, 0.08)
    x += name_len + 0.12
    slab("class%d" % i, (x + class_len / 2, y, 0.07), (class_len, 0.17, 0.05), text, 0.08)
    # the role, a round badge with its symbol
    rc, *symbols = ROLE[role]
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=0.21, depth=0.1, location=(1.38, y, 0.08))
    o = bpy.context.object; bevel(o, 0.04, 4); o.data.materials.append(border)
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=0.17, depth=0.12, location=(1.38, y, 0.09))
    o = bpy.context.object; bevel(o, 0.04, 4); o.data.materials.append(mat("r%d" % i, srgb(rc), rough=0.35))
    for k, pts in enumerate(symbols):
        prism("sym%d_%d" % (i, k), pts, (1.38, y, 0.15 + 0.01 * k), 0.06, white, 0.006)

# background
world = bpy.data.worlds.new("w")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (*srgb("#1b2233"), 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6

# lights
key = bpy.data.lights.new("key", "AREA")
key.energy, key.size = 900, 4
ko = bpy.data.objects.new("key", key)
ko.location = (-3, -3, 6)
ko.rotation_euler = (math.radians(40), 0, math.radians(-45))
scene.collection.objects.link(ko)
fill = bpy.data.lights.new("fill", "AREA")
fill.energy, fill.size = 300, 6
fo = bpy.data.objects.new("fill", fill)
fo.location = (4, 2, 5)
fo.rotation_euler = (math.radians(-30), math.radians(35), 0)
scene.collection.objects.link(fo)

# camera: slightly tilted, orthographic
cam = bpy.data.cameras.new("cam")
cam.type = "ORTHO"
cam.ortho_scale = 4.0
co = bpy.data.objects.new("cam", cam)
scene.collection.objects.link(co)
co.location = (0, -1.2, 6)
co.rotation_euler = (math.atan2(1.2, 6), 0, 0)  # (tilted back a little, no roll)
scene.camera = co

scene.render.engine = "CYCLES"
scene.cycles.samples = 256
scene.render.film_transparent = True
scene.cycles.use_denoising = True
prefs = bpy.context.preferences.addons["cycles"].preferences
for kind in ("OPTIX", "CUDA"):
    try:
        prefs.compute_device_type = kind
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        scene.cycles.device = "GPU"
        break
    except Exception:
        pass
scene.view_settings.view_transform = "AgX"
scene.view_settings.look = "AgX - Punchy"
scene.render.resolution_x = scene.render.resolution_y = 400
scene.render.filepath = OUT
scene.render.image_settings.file_format = "PNG"
bpy.ops.render.render(write_still=True)
