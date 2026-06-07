# Landis Controller Demonstration

This document reproduces the orbit-raising maneuver described by
Landis & Hrach (1991, *Journal of Guidance, Control, and Dynamics*)
and Landis (1992, *Acta Astronautica*).  These papers are cited in the
project's references and are the closest analogs to the controller
implemented here.

Run the demonstration script with:

```bash
python sims/landis_demo.py
```

The script runs with built-in parameters, disables lunar gravity
(`include_moon=False`), and writes a semimajor-axis history plot to
`docs/landis_demo.png`.

<!-- TODO: insert generated plot -->
![Semimajor axis history](landis_demo.png)

The plot shows the gradual increase in orbital semimajor axis as the
Landis controller trades barbell spin for orbital energy.
