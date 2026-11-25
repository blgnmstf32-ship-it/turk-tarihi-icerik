"""Original schematic skin geometry. Run using Blender's background Python."""
import argparse
from math import sin
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
    return obj


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
    base = material("Mauve plinth", (.103, .053, .127))
    outer = material("Intercellular lipid matrix", (.50, .23, .27), .52)
    middle = material("Living epidermis schematic", (.56, .209, .26))
    deep = material("Supporting tissue schematic", (.61, .31, .26))
    tiles = [material(f"Corneocyte {i}", color, .40) for i, color in enumerate((
        (.85, .50, .38), (.76, .40, .34), (.94, .58, .45), (.81, .43, .37),
    ))]
    droplet = material("Surface water", (.34, .65, .78), .19, .32)
    block("Platform", (0, 0, -.76), (4.75, 3.58, .14), base)
    for name, z, thickness, color in (
        ("Dermis", -.50, .39, deep), ("Epidermis", -.12, .39, middle),
        ("Lipid matrix", .22, .28, outer),
    ):
        block(name, (0, 0, z), (4.5, 3.34, thickness), color)
    # Offset the flattened cells within the matrix to show the brick-and-mortar arrangement.
    for layer in range(3):
        for row in range(5):
            for col in range(6):
                x = -.10 + (col - 2.5) * .70 + (.19 if (row+layer) % 2 else 0)
                y = (row-2)*.63
                cell = block("Corneocyte", (x, y, .15 + layer*.10),
                             (.67, .59, .092), tiles[(col + 2*row + layer) % len(tiles)])
                cell.rotation_euler.z = .052*sin(col*2.9 + row + layer)
    for i, (x, y) in enumerate(((-1.45, .7), (-.65, -.65), (.10, .92), (.86, -.27), (1.57, .51))):
        drop = sphere("Surface moisture", (x, y, .46), (.090, .075, .081), droplet)
        drop.keyframe_insert("scale", frame=1)
        drop.scale = (.16 + i*.007, .11 + i*.006, .040)
        drop.keyframe_insert("scale", frame=frames)
    bpy.ops.object.camera_add()
    camera = bpy.context.object
    scene.camera = camera
    for frame, location, lens in ((1, (7.7, -10.2, 6.7), 34), (frames, (3.7, -9.9, 4.2), 40)):
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
    scene.cycles.samples = 7
    scene.cycles.use_denoising = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.resolution_x, scene.render.resolution_y = size, round(size * 16/9)
    scene.render.resolution_percentage = 100
    scene.frame_end = frames
    scene.render.fps = 30
    scene.render.filepath = str(out.resolve()) + "/skin-"
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 4
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
