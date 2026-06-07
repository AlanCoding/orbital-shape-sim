"""Procedurally build and render an Earth-Moon L1 diamond stabilizer scene.

This script is intended to run inside Blender 4.x:

    blender --background --python docs/blender_l1_diamond/generate_earth_moon_l1_diamond.py

Conceptual unit convention:
    1 Blender unit == 1 kilometre
"""

from __future__ import annotations

import math
import random
from pathlib import Path

import bpy
from mathutils import Vector


EARTH_RADIUS_KM = 6371.0
MOON_RADIUS_KM = 1737.0
EARTH_MOON_DISTANCE_KM = 384400.0
L1_X_KM = 326400.0
DIAMOND_HALF_SPAN_KM = 141.4

WIDE_RESOLUTION = (2400, 900)
CLOSE_RESOLUTION = (1600, 1000)


def set_input(node, socket_name: str, value, *fallback_names: str) -> None:
    """Set a node input value while tolerating minor Blender socket renames."""

    for candidate in (socket_name, *fallback_names):
        socket = node.inputs.get(candidate)
        if socket is not None:
            socket.default_value = value
            return
    raise KeyError(f"Missing socket {socket_name!r} on node {node.name!r}")


def look_at(obj: bpy.types.Object, target) -> None:
    """Rotate an object so its -Z axis points at ``target``."""

    target_vec = Vector(target)
    direction = target_vec - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def create_uv_sphere(name: str, radius: float, location, material: bpy.types.Material):
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=radius,
        location=location,
        segments=96,
        ring_count=48,
    )
    obj = bpy.context.active_object
    obj.name = name
    if material is not None:
        obj.data.materials.append(material)
    return obj


def create_emissive_sphere(
    name: str,
    radius: float,
    location,
    material: bpy.types.Material,
):
    return create_uv_sphere(name=name, radius=radius, location=location, material=material)


def create_cylinder_between(
    name: str,
    p1,
    p2,
    radius: float,
    material: bpy.types.Material,
):
    p1_vec = Vector(p1)
    p2_vec = Vector(p2)
    delta = p2_vec - p1_vec
    length = delta.length
    midpoint = (p1_vec + p2_vec) * 0.5

    bpy.ops.mesh.primitive_cylinder_add(
        radius=radius,
        depth=length,
        location=midpoint,
        vertices=32,
    )
    obj = bpy.context.active_object
    obj.name = name
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = Vector((0.0, 0.0, 1.0)).rotation_difference(delta.normalized())
    if material is not None:
        obj.data.materials.append(material)
    return obj


def create_camera(name: str, location, target, focal_length: float, clipping):
    camera_data = bpy.data.cameras.new(name)
    camera = bpy.data.objects.new(name, camera_data)
    bpy.context.scene.collection.objects.link(camera)
    camera.location = Vector(location)

    if isinstance(clipping, dict):
        camera_data.clip_start = clipping.get("start", 0.1)
        camera_data.clip_end = clipping.get("end", 5_000_000.0)
        if clipping.get("type") == "ORTHO":
            camera_data.type = "ORTHO"
            camera_data.ortho_scale = clipping.get("ortho_scale", 1000.0)
    else:
        clip_start, clip_end = clipping
        camera_data.clip_start = clip_start
        camera_data.clip_end = clip_end

    if camera_data.type != "ORTHO":
        camera_data.lens = focal_length

    look_at(camera, target)
    return camera


def next_output_dir(base_dir: Path) -> Path:
    index = 1
    while True:
        candidate = base_dir / f"output{index}"
        if not candidate.exists():
            candidate.mkdir(parents=True, exist_ok=False)
            return candidate
        index += 1


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)
    for block in bpy.data.materials:
        if block.users == 0:
            bpy.data.materials.remove(block)
    for block in bpy.data.cameras:
        if block.users == 0:
            bpy.data.cameras.remove(block)
    for block in bpy.data.lights:
        if block.users == 0:
            bpy.data.lights.remove(block)


def set_scene_defaults() -> None:
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "KILOMETERS"
    scene.unit_settings.scale_length = 1000.0

    scene.render.engine = "CYCLES"
    scene.cycles.samples = 128
    scene.cycles.preview_samples = 32
    scene.cycles.use_adaptive_sampling = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False

    for look_name in ("AgX - Medium High Contrast", "Filmic - High Contrast", "None"):
        try:
            scene.view_settings.look = look_name
            break
        except Exception:
            continue
    scene.view_settings.exposure = -0.2
    scene.display_settings.display_device = "sRGB"

    world = scene.world or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()

    background = nodes.new("ShaderNodeBackground")
    background.inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0)
    background.inputs["Strength"].default_value = 0.012

    output = nodes.new("ShaderNodeOutputWorld")
    links.new(background.outputs["Background"], output.inputs["Surface"])


def make_principled_material(
    name: str,
    base_color,
    metallic: float = 0.0,
    roughness: float = 0.5,
    emission_color=None,
    emission_strength: float = 0.0,
):
    material = bpy.data.materials.new(name=name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    bsdf = nodes["Principled BSDF"]
    set_input(bsdf, "Base Color", base_color)
    set_input(bsdf, "Metallic", metallic)
    set_input(bsdf, "Roughness", roughness)
    if emission_color is not None:
        set_input(bsdf, "Emission Color", emission_color, "Emission")
        set_input(bsdf, "Emission Strength", emission_strength)
    return material


def make_earth_material():
    material = bpy.data.materials.new(name="EarthMaterial")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    noise = nodes.new("ShaderNodeTexNoise")
    bump = nodes.new("ShaderNodeBump")
    ramp = nodes.new("ShaderNodeValToRGB")
    coord = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")

    noise.inputs["Scale"].default_value = 4.5
    noise.inputs["Detail"].default_value = 10.0
    noise.inputs["Roughness"].default_value = 0.55
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[0].color = (0.03, 0.10, 0.24, 1.0)
    ramp.color_ramp.elements[1].position = 0.78
    ramp.color_ramp.elements[1].color = (0.10, 0.43, 0.72, 1.0)
    bump.inputs["Strength"].default_value = 0.03
    set_input(bsdf, "Roughness", 0.45)
    set_input(bsdf, "Specular IOR Level", 0.55, "Specular")

    links.new(coord.outputs["Object"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    return material


def make_cloud_material():
    material = bpy.data.materials.new(name="CloudMaterial")
    material.use_nodes = True
    material.blend_method = "BLEND"
    if hasattr(material, "shadow_method"):
        material.shadow_method = "HASHED"

    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    mix = nodes.new("ShaderNodeMixShader")
    transparent = nodes.new("ShaderNodeBsdfTransparent")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    noise = nodes.new("ShaderNodeTexNoise")
    ramp = nodes.new("ShaderNodeValToRGB")
    coord = nodes.new("ShaderNodeTexCoord")

    noise.inputs["Scale"].default_value = 8.0
    noise.inputs["Detail"].default_value = 12.0
    noise.inputs["Roughness"].default_value = 0.7
    ramp.color_ramp.elements[0].position = 0.55
    ramp.color_ramp.elements[1].position = 0.72
    ramp.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    ramp.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)

    set_input(bsdf, "Base Color", (0.95, 0.97, 1.0, 1.0))
    set_input(bsdf, "Roughness", 0.9)
    set_input(bsdf, "Alpha", 0.35)

    links.new(coord.outputs["Object"], noise.inputs["Vector"])
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], mix.inputs["Fac"])
    links.new(transparent.outputs["BSDF"], mix.inputs[1])
    links.new(bsdf.outputs["BSDF"], mix.inputs[2])
    links.new(mix.outputs["Shader"], output.inputs["Surface"])
    return material


def make_moon_material():
    material = bpy.data.materials.new(name="MoonMaterial")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    noise_a = nodes.new("ShaderNodeTexNoise")
    noise_b = nodes.new("ShaderNodeTexNoise")
    bump = nodes.new("ShaderNodeBump")
    ramp = nodes.new("ShaderNodeValToRGB")
    coord = nodes.new("ShaderNodeTexCoord")
    add = nodes.new("ShaderNodeMath")

    noise_a.inputs["Scale"].default_value = 7.0
    noise_a.inputs["Detail"].default_value = 14.0
    noise_a.inputs["Roughness"].default_value = 0.65
    noise_b.inputs["Scale"].default_value = 35.0
    noise_b.inputs["Detail"].default_value = 2.0
    noise_b.inputs["Roughness"].default_value = 0.25
    ramp.color_ramp.elements[0].color = (0.22, 0.22, 0.22, 1.0)
    ramp.color_ramp.elements[1].color = (0.68, 0.68, 0.68, 1.0)
    add.operation = "ADD"
    bump.inputs["Strength"].default_value = 0.06
    set_input(bsdf, "Roughness", 0.92)

    links.new(coord.outputs["Object"], noise_a.inputs["Vector"])
    links.new(coord.outputs["Object"], noise_b.inputs["Vector"])
    links.new(noise_a.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(noise_a.outputs["Fac"], add.inputs[0])
    links.new(noise_b.outputs["Fac"], add.inputs[1])
    links.new(add.outputs["Value"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    return material


def add_starfield(center_x: float) -> None:
    rng = random.Random(42)
    star_material = bpy.data.materials.new(name="StarMaterial")
    star_material.use_nodes = True
    nodes = star_material.node_tree.nodes
    bsdf = nodes["Principled BSDF"]
    set_input(bsdf, "Base Color", (1.0, 0.98, 0.92, 1.0))
    set_input(bsdf, "Emission Color", (1.0, 0.98, 0.94, 1.0), "Emission")
    set_input(bsdf, "Emission Strength", 10.0)
    set_input(bsdf, "Roughness", 0.0)

    center = Vector((center_x, 0.0, 0.0))
    shell_radius = 1_250_000.0
    for idx in range(600):
        theta = rng.uniform(0.0, 2.0 * math.pi)
        phi = math.acos(rng.uniform(-0.98, 0.98))
        jitter = rng.uniform(-35_000.0, 35_000.0)
        radius = shell_radius + jitter
        location = Vector(
            (
                center.x + radius * math.sin(phi) * math.cos(theta),
                center.y + radius * math.sin(phi) * math.sin(theta),
                center.z + radius * math.cos(phi),
            )
        )
        bpy.ops.mesh.primitive_ico_sphere_add(
            subdivisions=1,
            radius=rng.uniform(60.0, 180.0),
            location=location,
        )
        star = bpy.context.active_object
        star.name = f"Star_{idx:03d}"
        star.data.materials.append(star_material)


def add_sun_light() -> None:
    light_data = bpy.data.lights.new(name="Sun", type="SUN")
    light_data.energy = 3.5
    light = bpy.data.objects.new(name="Sun", object_data=light_data)
    bpy.context.scene.collection.objects.link(light)
    light.location = (-120_000.0, -240_000.0, 180_000.0)
    look_at(light, (200_000.0, 0.0, -10_000.0))

    fill_data = bpy.data.lights.new(name="FillArea", type="AREA")
    fill_data.energy = 80_000.0
    fill_data.shape = "RECTANGLE"
    fill_data.size = 120_000.0
    fill_data.size_y = 60_000.0
    fill = bpy.data.objects.new(name="FillArea", object_data=fill_data)
    bpy.context.scene.collection.objects.link(fill)
    fill.location = (270_000.0, -75_000.0, 40_000.0)
    look_at(fill, (326_400.0, 0.0, 0.0))


def add_axis_dashes(
    start_x: float,
    end_x: float,
    radius: float,
    dash_length: float,
    gap_length: float,
    material: bpy.types.Material,
) -> None:
    cursor = start_x
    dash_index = 0
    while cursor < end_x:
        dash_end = min(cursor + dash_length, end_x)
        create_cylinder_between(
            name=f"AxisDash_{dash_index:03d}",
            p1=(cursor, 0.0, 0.0),
            p2=(dash_end, 0.0, 0.0),
            radius=radius,
            material=material,
        )
        cursor = dash_end + gap_length
        dash_index += 1


def render_camera(camera_name: str, filepath: Path, resolution: tuple[int, int]) -> None:
    scene = bpy.context.scene
    scene.camera = bpy.data.objects[camera_name]
    scene.render.filepath = str(filepath)
    scene.render.resolution_x = resolution[0]
    scene.render.resolution_y = resolution[1]
    bpy.ops.render.render(write_still=True)


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    output_dir = next_output_dir(script_dir)
    blend_path = output_dir / "earth_moon_l1_diamond.blend"

    clear_scene()
    set_scene_defaults()

    earth_material = make_earth_material()
    cloud_material = make_cloud_material()
    moon_material = make_moon_material()
    strut_material = make_principled_material(
        "StrutMaterial",
        base_color=(0.64, 0.74, 0.82, 1.0),
        metallic=0.65,
        roughness=0.22,
    )
    tether_material = make_principled_material(
        "TetherMaterial",
        base_color=(0.55, 0.80, 0.96, 1.0),
        metallic=0.1,
        roughness=0.35,
        emission_color=(0.18, 0.48, 0.82, 1.0),
        emission_strength=0.3,
    )
    node_material = make_principled_material(
        "NodeMaterial",
        base_color=(0.85, 0.95, 1.0, 1.0),
        metallic=0.0,
        roughness=0.15,
        emission_color=(0.55, 0.88, 1.0, 1.0),
        emission_strength=8.0,
    )
    hub_material = make_principled_material(
        "HubMaterial",
        base_color=(0.80, 0.93, 1.0, 1.0),
        metallic=0.2,
        roughness=0.2,
        emission_color=(0.35, 0.72, 1.0, 1.0),
        emission_strength=4.0,
    )
    axis_material = make_principled_material(
        "AxisGuideMaterial",
        base_color=(0.4, 0.55, 0.72, 1.0),
        metallic=0.0,
        roughness=0.5,
        emission_color=(0.15, 0.24, 0.35, 1.0),
        emission_strength=0.25,
    )

    earth = create_uv_sphere(
        "Earth",
        radius=EARTH_RADIUS_KM,
        location=(0.0, 0.0, 0.0),
        material=earth_material,
    )
    clouds = create_uv_sphere(
        "EarthClouds",
        radius=EARTH_RADIUS_KM * 1.012,
        location=(0.0, 0.0, 0.0),
        material=cloud_material,
    )
    clouds.rotation_euler = (0.15, 0.0, 0.35)

    moon = create_uv_sphere(
        "Moon",
        radius=MOON_RADIUS_KM,
        location=(EARTH_MOON_DISTANCE_KM, 0.0, 0.0),
        material=moon_material,
    )
    moon.rotation_euler = (0.0, 0.4, 0.2)

    center = Vector((L1_X_KM, 0.0, 0.0))
    nodes = {
        "left": center + Vector((-DIAMOND_HALF_SPAN_KM, 0.0, 0.0)),
        "right": center + Vector((DIAMOND_HALF_SPAN_KM, 0.0, 0.0)),
        "top": center + Vector((0.0, DIAMOND_HALF_SPAN_KM, 0.0)),
        "bottom": center + Vector((0.0, -DIAMOND_HALF_SPAN_KM, 0.0)),
    }

    main_radius = 6.0
    tether_radius = 2.2
    axis_radius = 7.0
    node_radius = 15.0
    hub_radius = 24.0

    edge_pairs = [
        ("left", "top"),
        ("top", "right"),
        ("right", "bottom"),
        ("bottom", "left"),
    ]
    internal_pairs = [
        ("left", "right"),
        ("top", "bottom"),
    ]

    for idx, (a_name, b_name) in enumerate(edge_pairs):
        create_cylinder_between(
            name=f"DiamondEdge_{idx}",
            p1=nodes[a_name],
            p2=nodes[b_name],
            radius=main_radius,
            material=strut_material,
        )

    for idx, (a_name, b_name) in enumerate(internal_pairs):
        create_cylinder_between(
            name=f"DiamondInternal_{idx}",
            p1=nodes[a_name],
            p2=nodes[b_name],
            radius=axis_radius if a_name == "left" else tether_radius,
            material=tether_material if a_name == "top" else strut_material,
        )

    for idx, (node_name, position) in enumerate(nodes.items()):
        create_cylinder_between(
            name=f"HubSpoke_{idx}",
            p1=center,
            p2=position,
            radius=tether_radius,
            material=tether_material,
        )

    create_cylinder_between(
        name="CenterLongitudinalAxis",
        p1=(nodes["left"].x - 18.0, 0.0, 0.0),
        p2=(nodes["right"].x + 18.0, 0.0, 0.0),
        radius=axis_radius,
        material=strut_material,
    )

    for node_name, position in nodes.items():
        create_emissive_sphere(
            name=f"Node_{node_name}",
            radius=node_radius,
            location=position,
            material=node_material,
        )

    create_emissive_sphere(
        name="DiamondHub",
        radius=hub_radius,
        location=center,
        material=hub_material,
    )
    create_uv_sphere(
        "DiamondHubCore",
        radius=12.0,
        location=center,
        material=strut_material,
    )

    add_starfield(center_x=EARTH_MOON_DISTANCE_KM * 0.5)
    add_sun_light()

    wide_target = (EARTH_MOON_DISTANCE_KM * 0.5, 0.0, 0.0)
    create_camera(
        "wide_side_earth_moon",
        location=(192_200.0, -45_000.0, 900_000.0),
        target=wide_target,
        focal_length=85.0,
        clipping={
            "start": 10.0,
            "end": 3_000_000.0,
            "type": "ORTHO",
            "ortho_scale": 410_000.0,
        },
    )
    create_camera(
        "diamond_with_earth_background",
        location=(329_800.0, -180.0, 650.0),
        target=(240_000.0, 0.0, 0.0),
        focal_length=50.0,
        clipping={"start": 1.0, "end": 3_000_000.0},
    )
    create_camera(
        "diamond_with_moon_background",
        location=(323_000.0, -180.0, 650.0),
        target=(360_000.0, 0.0, 0.0),
        focal_length=50.0,
        clipping={"start": 1.0, "end": 3_000_000.0},
    )
    create_camera(
        "earth_side_node_detail",
        location=(332_000.0, -260.0, 1_400.0),
        target=nodes["left"],
        focal_length=55.0,
        clipping={"start": 1.0, "end": 3_000_000.0},
    )
    create_camera(
        "moon_side_node_detail",
        location=(321_000.0, -260.0, 1_400.0),
        target=nodes["right"],
        focal_length=55.0,
        clipping={"start": 1.0, "end": 3_000_000.0},
    )

    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    render_camera(
        "wide_side_earth_moon",
        output_dir / "wide_side_earth_moon.png",
        WIDE_RESOLUTION,
    )
    render_camera(
        "diamond_with_earth_background",
        output_dir / "diamond_with_earth_background.png",
        CLOSE_RESOLUTION,
    )
    render_camera(
        "diamond_with_moon_background",
        output_dir / "diamond_with_moon_background.png",
        CLOSE_RESOLUTION,
    )
    render_camera(
        "earth_side_node_detail",
        output_dir / "earth_side_node_detail.png",
        CLOSE_RESOLUTION,
    )
    render_camera(
        "moon_side_node_detail",
        output_dir / "moon_side_node_detail.png",
        CLOSE_RESOLUTION,
    )

    bpy.ops.wm.save_mainfile()
    print(f"Output directory: {output_dir}")


if __name__ == "__main__":
    main()
