# Earth-Moon L1 Diamond Blender Scene

This folder contains a procedural Blender generator for an Earth-Moon L1
diamond stabilizer concept render set.

Run it with Blender in background mode:

```bash
blender --background --python docs/blender_l1_diamond/generate_earth_moon_l1_diamond.py
```

Each run creates the next available output folder:

- `output1/`
- `output2/`
- `output3/`

Inside each folder the script writes:

- `earth_moon_l1_diamond.blend`
- `wide_side_earth_moon.png`
- `diamond_with_earth_background.png`
- `diamond_with_moon_background.png`
- `earth_side_node_detail.png`
- `moon_side_node_detail.png`
