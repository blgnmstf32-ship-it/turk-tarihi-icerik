"""Original schematic skin geometry. Run using Blender's background Python."""
import argparse
from math import radians
from pathlib import Path
import sys

import bpy
from mathutils import Vector


def material(name, color, roughness=.58, metallic=0):
    item = bpy.data.materials.new(name)
    item.diffuse_color = (*color, 1)
    item.use_nodes = True
    shader = item.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1)
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metallic
    return item


def block(name, at, size, color):
    bpy.ops.mesh.primitive_cube_add(size=1, location=at)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bevel = obj.modifiers.new("Soft edge", "BEVEL")
    bevel.width = .085
    bevel.segments = 4
    obj.modifiers.new("Weighted normals", "WEIGHTED_NORMAL")
    obj.data.materials.append(color)


def sphere(name, location, scale, mat):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(mat)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    return obj


def point_at(obj, focus):
    obj.rotation_euler = (Vector(focus) - obj.location).to_track_quat("-Z", "Y").to_euler()


def scene_for(out, frames, size):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    base = material("Mauve plinth", (.12, .075, .18))
    outer = material("Surface schematic", (.80, .36, .28))
    middle = material("Mid-layer schematic", (.68, .20, .30))
    deep = material("Deep layer schematic", (.79, .47, .19))
    hair = material("Follicle concept", (.10, .045, .062), metallic=.15)
    block("Platform", (0, 0, -.96), (5.2, 4.4, .25), base)
    for name, z, thickness, color in (
        ("Surface", .56, .28, outer), ("Middle", .04, .70, middle), ("Supporting tissue", -.58, .53, deep)
    ):
        block(name, (0, 0, z), (4.8, 3.8, thickness), color)
    for x, y in ((-1.05, -1.3), (.50, -1.79), (1.23, -.51)):
        shaft = sphere("Hair concept", (x, y, .77), (.07, .08, .82), hair)
        shaft.rotation_euler.y = radians(14)
        sphere("Root schematic", (x-.16, y, .09), (.16, .12, .31), hair)
    bpy.ops.object.camera_add()
    camera = bpy.context.object
    scene.camera = camera
    for frame, location, lens in ((1, (6.6, -9.2, 5.6), 52), (frames, (4.5, -10.2, 4.4), 59)):
        camera.location = location
        point_at(camera, (0, 0, .12))
        camera.data.lens = lens
        camera.keyframe_insert("location", frame=frame)
        camera.keyframe_insert("rotation_euler", frame=frame)
        camera.data.keyframe_insert("lens", frame=frame)
    for loc, power, color, width in (
        ((-3, -4, 7), 850, (1, .75, .64), 5),
        ((5, 1, 5), 670, (.76, .70, 1), 4),
        ((-3, 5, 2), 450, (1, .46, .43), 3),
    ):
        bpy.ops.object.light_add(type="AREA", location=loc)
        lamp = bpy.context.object
        lamp.data.energy = power
        lamp.data.color = color
        lamp.data.shape = "DISK"
        lamp.data.size = width
        point_at(lamp, (0, 0, 0))
    scene.world = bpy.data.worlds.new("Plum background")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (.047, .022, .064, 1)
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 5
    scene.cycles.use_denoising = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.resolution_x, scene.render.resolution_y = size, round(size * 16/9)
    scene.render.resolution_percentage = 100
    scene.frame_end = frames
    scene.render.fps = 30
    scene.render.filepath = str(out.resolve()) + "/skin-"
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 2
    return scene


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--frames", type=int, default=30)
    parser.add_argument("--width", type=int, default=432)
    args = parser.parse_args(sys.argv[sys.argv.index("--")+1:])
    if not 2 <= args.frames <= 300 or not 216 <= args.width <= 1080:
        parser.error("Invalid animation request size.")
    args.out.mkdir(parents=True, exist_ok=True)
    scene_for(args.out, args.frames, args.width)
    bpy.ops.render.render(animation=True)


if __name__ == "__main__":
    main()
