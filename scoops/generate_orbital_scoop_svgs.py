#!/usr/bin/env python3
from __future__ import annotations

import html
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


WIDTH = 1200
HEIGHT = 900
CX = WIDTH / 2
CY = HEIGHT / 2
EARTH_R = 135

BG = "#11161c"
EARTH = "#4d7ea8"
ATMOS_1 = "#8ec9ff"
ATMOS_2 = "#a9dcff"
ORBIT = "#bcc5cf"
COLLECT = "#ff8e42"
COLLECT_HOT = "#ff5d4d"
TRANSFER = "#a8d85f"
RECOVERY = "#6fd0c8"
TETHER = "#d8e4ef"
TEXT = "#e9eef3"
TEXT_SOFT = "#aab7c4"
FIELD = "#7fdcff"
IONO = "#6f89d0"

OUT_DIR = Path("svg_out")


@dataclass(frozen=True)
class Diagram:
    filename: str
    title: str
    blurb: str
    source_html: str
    body: str


def fmt(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def polar(cx: float, cy: float, radius: float, degrees: float) -> tuple[float, float]:
    radians = math.radians(degrees)
    return cx + radius * math.cos(radians), cy + radius * math.sin(radians)


def ellipse_point(
    cx: float, cy: float, rx: float, ry: float, degrees: float
) -> tuple[float, float]:
    radians = math.radians(degrees)
    return cx + rx * math.cos(radians), cy + ry * math.sin(radians)


def arc_path_circle(cx: float, cy: float, radius: float, start_deg: float, end_deg: float) -> str:
    x1, y1 = polar(cx, cy, radius, start_deg)
    x2, y2 = polar(cx, cy, radius, end_deg)
    delta = (end_deg - start_deg) % 360
    large = 1 if delta > 180 else 0
    sweep = 1
    return (
        f"M {fmt(x1)} {fmt(y1)} "
        f"A {fmt(radius)} {fmt(radius)} 0 {large} {sweep} {fmt(x2)} {fmt(y2)}"
    )


def arc_path_ellipse(
    cx: float, cy: float, rx: float, ry: float, start_deg: float, end_deg: float
) -> str:
    x1, y1 = ellipse_point(cx, cy, rx, ry, start_deg)
    x2, y2 = ellipse_point(cx, cy, rx, ry, end_deg)
    delta = (end_deg - start_deg) % 360
    large = 1 if delta > 180 else 0
    sweep = 1
    return (
        f"M {fmt(x1)} {fmt(y1)} "
        f"A {fmt(rx)} {fmt(ry)} 0 {large} {sweep} {fmt(x2)} {fmt(y2)}"
    )


def path_from_points(points: list[tuple[float, float]]) -> str:
    if not points:
        return ""
    start = f"M {fmt(points[0][0])} {fmt(points[0][1])}"
    rest = " ".join(f"L {fmt(x)} {fmt(y)}" for x, y in points[1:])
    return f"{start} {rest}"


def sampled_ellipse_segment(
    cx: float, cy: float, rx: float, ry: float, start_deg: float, end_deg: float, samples: int = 48
) -> str:
    points = []
    for i in range(samples + 1):
        t = i / samples
        deg = start_deg + (end_deg - start_deg) * t
        points.append(ellipse_point(cx, cy, rx, ry, deg))
    return path_from_points(points)


def leader(x1: float, y1: float, x2: float, y2: float, text: str, dx: float = 0, dy: float = 0) -> str:
    tx = x2 + dx
    ty = y2 + dy
    return (
        f'<path d="M {fmt(x1)} {fmt(y1)} L {fmt(x2)} {fmt(y2)}" class="leader"/>'
        f'<text x="{fmt(tx)}" y="{fmt(ty)}" class="label">{html.escape(text)}</text>'
    )


def arrow_line(
    x1: float, y1: float, x2: float, y2: float, klass: str = "arrow", both: bool = False
) -> str:
    marker_end = ' marker-end="url(#arrowhead)"'
    marker_start = ' marker-start="url(#arrowhead)"' if both else ""
    return (
        f'<path d="M {fmt(x1)} {fmt(y1)} L {fmt(x2)} {fmt(y2)}" '
        f'class="{klass}"{marker_start}{marker_end}/>'
    )


def orbit_circle(radius: float, klass: str = "orbit") -> str:
    return (
        f'<circle cx="{fmt(CX)}" cy="{fmt(CY)}" r="{fmt(radius)}" class="{klass}"/>'
    )


def orbit_ellipse(rx: float, ry: float, klass: str = "orbit") -> str:
    return (
        f'<ellipse cx="{fmt(CX)}" cy="{fmt(CY)}" rx="{fmt(rx)}" ry="{fmt(ry)}" class="{klass}"/>'
    )


def orbit_ellipse_at(cx: float, cy: float, rx: float, ry: float, klass: str = "orbit") -> str:
    return (
        f'<ellipse cx="{fmt(cx)}" cy="{fmt(cy)}" rx="{fmt(rx)}" ry="{fmt(ry)}" class="{klass}"/>'
    )


def orbit_arrow_circle(radius: float, angle_deg: float) -> str:
    a1 = angle_deg - 8
    a2 = angle_deg + 6
    x1, y1 = polar(CX, CY, radius, a1)
    x2, y2 = polar(CX, CY, radius, a2)
    return arrow_line(x1, y1, x2, y2)


def orbit_arrow_ellipse(rx: float, ry: float, angle_deg: float) -> str:
    a1 = angle_deg - 10
    a2 = angle_deg + 6
    x1, y1 = ellipse_point(CX, CY, rx, ry, a1)
    x2, y2 = ellipse_point(CX, CY, rx, ry, a2)
    return arrow_line(x1, y1, x2, y2)


def orbit_arrow_ellipse_at(cx: float, cy: float, rx: float, ry: float, angle_deg: float) -> str:
    a1 = angle_deg - 10
    a2 = angle_deg + 6
    x1, y1 = ellipse_point(cx, cy, rx, ry, a1)
    x2, y2 = ellipse_point(cx, cy, rx, ry, a2)
    return arrow_line(x1, y1, x2, y2)


def focused_vertical_orbit(semimajor: float, perigee_radius: float) -> tuple[float, float, float, float]:
    focus_offset = semimajor - perigee_radius
    semiminor = math.sqrt(perigee_radius * (2 * semimajor - perigee_radius))
    center_y = CY - focus_offset
    return CX, center_y, semiminor, semimajor


def focused_transfer_arc(
    perigee_radius: float,
    apogee_radius: float,
    argument_deg: float,
    start_true_deg: float,
    end_true_deg: float,
    samples: int = 80,
) -> str:
    semimajor = (perigee_radius + apogee_radius) / 2
    eccentricity = (apogee_radius - perigee_radius) / (apogee_radius + perigee_radius)
    arg = math.radians(argument_deg)
    start = math.radians(start_true_deg)
    end = math.radians(end_true_deg)
    points: list[tuple[float, float]] = []
    for i in range(samples + 1):
        frac = i / samples
        nu = start + (end - start) * frac
        radius = semimajor * (1 - eccentricity * eccentricity) / (1 + eccentricity * math.cos(nu))
        theta = arg + nu
        points.append((CX + radius * math.cos(theta), CY + radius * math.sin(theta)))
    return path_from_points(points)


def dot(x: float, y: float, radius: float = 7, klass: str = "vehicle") -> str:
    return f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="{fmt(radius)}" class="{klass}"/>'


def ring(x: float, y: float, radius: float = 14) -> str:
    return (
        f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="{fmt(radius)}" class="ring"/>'
    )


def earth_and_atmosphere(extra: str = "") -> str:
    return f"""
    <g>
      <circle cx="{fmt(CX)}" cy="{fmt(CY)}" r="{fmt(EARTH_R + 55)}" fill="url(#atmoGlow)" opacity="0.55"/>
      <circle cx="{fmt(CX)}" cy="{fmt(CY)}" r="{fmt(EARTH_R + 34)}" fill="none" stroke="{ATMOS_1}" stroke-opacity="0.22" stroke-width="26"/>
      <circle cx="{fmt(CX)}" cy="{fmt(CY)}" r="{fmt(EARTH_R + 18)}" fill="none" stroke="{ATMOS_2}" stroke-opacity="0.20" stroke-width="14"/>
      {extra}
      <circle cx="{fmt(CX)}" cy="{fmt(CY)}" r="{fmt(EARTH_R)}" fill="{EARTH}"/>
    </g>
    """


def svg_document(title: str, body: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" width="{WIDTH}" height="{HEIGHT}" role="img" aria-label="{html.escape(title)}">
  <defs>
    <radialGradient id="atmoGlow" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="{ATMOS_1}" stop-opacity="0"/>
      <stop offset="62%" stop-color="{ATMOS_1}" stop-opacity="0"/>
      <stop offset="100%" stop-color="{ATMOS_1}" stop-opacity="0.26"/>
    </radialGradient>
    <marker id="arrowhead" markerWidth="10" markerHeight="8" refX="8" refY="4" orient="auto" markerUnits="strokeWidth">
      <path d="M 0 0 L 10 4 L 0 8 z" fill="{TEXT_SOFT}"/>
    </marker>
    <marker id="arrowheadWarm" markerWidth="10" markerHeight="8" refX="8" refY="4" orient="auto" markerUnits="strokeWidth">
      <path d="M 0 0 L 10 4 L 0 8 z" fill="{COLLECT}"/>
    </marker>
    <marker id="arrowheadGreen" markerWidth="10" markerHeight="8" refX="8" refY="4" orient="auto" markerUnits="strokeWidth">
      <path d="M 0 0 L 10 4 L 0 8 z" fill="{TRANSFER}"/>
    </marker>
    <style>
      .bg {{ fill: {BG}; }}
      .title {{ fill: {TEXT}; font: 600 26px Arial, Helvetica, sans-serif; letter-spacing: 0.2px; }}
      .label {{ fill: {TEXT}; font: 20px Arial, Helvetica, sans-serif; }}
      .soft {{ fill: {TEXT_SOFT}; font: 18px Arial, Helvetica, sans-serif; }}
      .orbit {{ fill: none; stroke: {ORBIT}; stroke-width: 2.5; opacity: 0.95; }}
      .orbit-dashed {{ fill: none; stroke: {TRANSFER}; stroke-width: 2.5; stroke-dasharray: 9 8; opacity: 0.95; }}
      .beam {{ fill: none; stroke: {FIELD}; stroke-width: 2.6; stroke-dasharray: 2 8; opacity: 0.95; }}
      .collect-arc {{ fill: none; stroke: {COLLECT}; stroke-width: 8; stroke-linecap: round; }}
      .collect-hot {{ fill: none; stroke: {COLLECT_HOT}; stroke-width: 10; stroke-linecap: round; }}
      .recovery-arc {{ fill: none; stroke: {RECOVERY}; stroke-width: 6; stroke-linecap: round; opacity: 0.9; }}
      .tether {{ fill: none; stroke: {TETHER}; stroke-width: 4; }}
      .vehicle {{ fill: {TEXT}; stroke: {BG}; stroke-width: 2; }}
      .station {{ fill: {TEXT}; stroke: {BG}; stroke-width: 2; }}
      .ring {{ fill: none; stroke: {TEXT}; stroke-width: 3; opacity: 0.9; }}
      .leader {{ fill: none; stroke: {TEXT_SOFT}; stroke-width: 1.8; }}
      .arrow {{ fill: none; stroke: {TEXT_SOFT}; stroke-width: 2.4; }}
      .arrow-warm {{ fill: none; stroke: {COLLECT}; stroke-width: 2.4; marker-end: url(#arrowheadWarm); }}
      .arrow-green {{ fill: none; stroke: {TRANSFER}; stroke-width: 2.6; marker-end: url(#arrowheadGreen); }}
      .field {{ fill: none; stroke: {FIELD}; stroke-width: 2.2; opacity: 0.5; }}
      .ionosphere {{ fill: none; stroke: {IONO}; stroke-width: 18; opacity: 0.16; }}
      .magnetic {{ fill: none; stroke: {FIELD}; stroke-width: 1.8; opacity: 0.35; }}
    </style>
  </defs>
  <rect class="bg" x="0" y="0" width="{WIDTH}" height="{HEIGHT}"/>
  <text x="48" y="54" class="title">{html.escape(title)}</text>
  {body}
</svg>
"""


def diagram_legend() -> Diagram:
    body = [
        '<circle cx="220" cy="220" r="50" fill="#4d7ea8"/>',
        '<text x="320" y="227" class="label">blue circle = Earth</text>',
        '<circle cx="220" cy="355" r="82" fill="none" stroke="#8ec9ff" stroke-opacity="0.25" stroke-width="18"/>'
        '<circle cx="220" cy="355" r="68" fill="none" stroke="#a9dcff" stroke-opacity="0.22" stroke-width="10"/>',
        '<text x="320" y="362" class="label">pale rings = atmosphere density falloff</text>',
        '<line x1="120" y1="500" x2="310" y2="500" class="orbit"/>',
        '<text x="320" y="507" class="label">gray line = orbit</text>',
        '<path d="M 120 620 A 110 110 0 0 1 294 620" class="collect-arc"/>',
        '<text x="320" y="627" class="label">orange / red arc = collection / heating / drag</text>',
        '<line x1="120" y1="740" x2="310" y2="740" class="orbit-dashed"/>',
        '<text x="320" y="747" class="label">dashed line = transfer path</text>',
        '<line x1="780" y1="210" x2="780" y2="370" class="tether"/>',
        '<text x="840" y="297" class="label">solid line = tether / pipe</text>',
        '<circle cx="760" cy="560" r="7" class="vehicle"/><circle cx="860" cy="560" r="11" class="station"/>',
        '<text x="900" y="567" class="label">dot = spacecraft / station, not to scale</text>',
    ]
    return Diagram(
        "00_legend.svg",
        "Legend",
        "Visual key for the schematic conventions used across the set.",
        "",
        svg_document("Legend", "".join(body)),
    )


def diagram_single_body() -> Diagram:
    orbit_r = EARTH_R + 44
    sx, sy = polar(CX, CY, orbit_r, -18)
    body = f"""
    {earth_and_atmosphere()}
    {orbit_circle(orbit_r)}
    <path d="{arc_path_circle(CX, CY, orbit_r, -145, 175)}" class="collect-arc"/>
    {orbit_arrow_circle(orbit_r, -110)}
    {orbit_arrow_circle(orbit_r, 35)}
    {dot(sx, sy, 8)}
    {leader(sx, sy, sx + 40, sy - 35, "single scoop vehicle", 10, -4)}
    <text x="{fmt(CX - 205)}" y="{fmt(CY - orbit_r - 22)}" class="label">continuous collection + drag compensation</text>
    <path d="M {fmt(sx + 3)} {fmt(sy + 2)} L {fmt(sx - 58)} {fmt(sy + 20)}" class="arrow-warm"/>
    <text x="{fmt(sx - 105)}" y="{fmt(sy + 31)}" class="soft">drag</text>
    <path d="M {fmt(sx - 2)} {fmt(sy - 2)} L {fmt(sx + 62)} {fmt(sy - 18)}" class="arrow-green"/>
    <text x="{fmt(sx + 72)}" y="{fmt(sy - 22)}" class="soft">thrust</text>
    """
    return Diagram(
        "01_single_body_continuous_scoop.svg",
        "Single-body continuous scoop",
        "Baseline PROFAC-style scoopcraft: one low vehicle collects while thrust continuously offsets drag.",
        '<a href="https://www.osti.gov/biblio/4163348" target="_blank" rel="noopener noreferrer">Demetriades PROFAC (1960)</a>; <a href="https://hpepl.ae.gatech.edu/papers/Singh.pdf" target="_blank" rel="noopener noreferrer">VLEO propellant collection feasibility</a>',
        svg_document("Single-body continuous scoop", body),
    )


def diagram_tethered_trawler() -> Diagram:
    low_r = EARTH_R + 48
    high_r = EARTH_R + 205
    low = polar(CX, CY, low_r, -55)
    high = polar(CX, CY, high_r, -55)
    midx = (low[0] + high[0]) / 2
    midy = (low[1] + high[1]) / 2
    body = f"""
    {earth_and_atmosphere()}
    {orbit_circle(low_r)}
    {orbit_circle(high_r)}
    <path d="{arc_path_circle(CX, CY, low_r, -92, -28)}" class="collect-hot"/>
    {dot(low[0], low[1], 7)}
    {dot(high[0], high[1], 11, "station")}
    <path d="M {fmt(low[0])} {fmt(low[1])} Q {fmt(midx + 12)} {fmt(midy - 8)} {fmt(high[0])} {fmt(high[1])}" class="tether"/>
    <path d="M {fmt(low[0])} {fmt(low[1])} Q {fmt(midx + 12)} {fmt(midy - 8)} {fmt(high[0])} {fmt(high[1])}" class="arrow-green"/>
    <text x="{fmt(midx + 24)}" y="{fmt(midy - 70)}" class="soft">gas transfer upward</text>
    {leader(low[0], low[1], low[0] + 34, low[1] + 52, "collector head", 6, 22)}
    {leader(high[0], high[1], high[0] + 36, high[1] - 40, "main station", 8, -4)}
    <text x="{fmt(low[0] - 115)}" y="{fmt(low[1] + 120)}" class="label">collection / heating / drag</text>
    <text x="{fmt(midx - 40)}" y="{fmt(midy - 18)}" class="soft">tether / pipe</text>
    """
    return Diagram(
        "02_two_tier_tethered_trawler.svg",
        "Two-tier tethered trawler",
        "ToughSF’s trawler split: a hot low collector feeds a higher safer main station through a tethered link.",
        '<a href="https://hpepl.ae.gatech.edu/papers/Singh.pdf" target="_blank" rel="noopener noreferrer">VLEO propellant collection feasibility</a>; <a href="https://www.hpepl.ae.gatech.edu/papers/ProgAerospace_Singh_V75_2015_pp15-25.pdf" target="_blank" rel="noopener noreferrer">LEO propellant collection review</a>',
        svg_document("Two-tier tethered trawler", body),
    )


def diagram_elliptical_diver() -> Diagram:
    ex, ey, rx, ry = focused_vertical_orbit(255, 175)
    perigee = ellipse_point(ex, ey, rx, ry, 90)
    body = f"""
    {earth_and_atmosphere()}
    {orbit_ellipse_at(ex, ey, rx, ry)}
    <path d="{arc_path_ellipse(ex, ey, rx, ry, 68, 112)}" class="collect-hot"/>
    <path d="{arc_path_ellipse(ex, ey, rx, ry, 208, 336)}" class="recovery-arc"/>
    {orbit_arrow_ellipse_at(ex, ey, rx, ry, 146)}
    {orbit_arrow_ellipse_at(ex, ey, rx, ry, 296)}
    {dot(perigee[0], perigee[1], 7)}
    {leader(perigee[0], perigee[1], perigee[0] + 28, perigee[1] - 52, "brief collection pass", 6, -4)}
    <text x="{fmt(CX - 116)}" y="{fmt(CY + 194)}" class="label">heating + drag loss</text>
    <text x="{fmt(CX + 150)}" y="{fmt(ey - ry + 68)}" class="label" fill="{RECOVERY}">slow recovery thrust</text>
    <text x="{fmt(CX + 150)}" y="{fmt(ey - ry + 92)}" class="soft">(appears incorrect)</text>
    """
    return Diagram(
        "03_elliptical_diver_single_vehicle.svg",
        "Elliptical diver",
        "ToughSF’s diver shows apogee-side recovery thrust, but thrust that changes the low point of the orbit should be applied near perigee instead.",
        '<a href="https://hpepl.ae.gatech.edu/papers/Singh.pdf" target="_blank" rel="noopener noreferrer">VLEO propellant collection feasibility</a>; <a href="https://www.hpepl.ae.gatech.edu/papers/ProgAerospace_Singh_V75_2015_pp15-25.pdf" target="_blank" rel="noopener noreferrer">LEO propellant collection review</a>',
        svg_document("Elliptical diver", body),
    )


def diagram_diver_mothership() -> Diagram:
    ex, ey, rx, ry = focused_vertical_orbit(250, 178)
    perigee = ellipse_point(ex, ey, rx, ry, 90)
    transfer = ellipse_point(ex, ey, rx, ry, 270)
    moth_r = math.hypot(transfer[0] - CX, transfer[1] - CY)
    moth = polar(CX, CY, moth_r, -38)
    body = f"""
    {earth_and_atmosphere()}
    {orbit_ellipse_at(ex, ey, rx, ry)}
    {orbit_circle(moth_r)}
    <path d="{arc_path_ellipse(ex, ey, rx, ry, 66, 110)}" class="collect-hot"/>
    {dot(perigee[0], perigee[1], 7)}
    {dot(moth[0], moth[1], 11, "station")}
    {ring(transfer[0], transfer[1], 15)}
    {orbit_arrow_ellipse_at(ex, ey, rx, ry, 150)}
    {orbit_arrow_ellipse_at(ex, ey, rx, ry, 304)}
    {leader(perigee[0], perigee[1], perigee[0] + 24, perigee[1] - 48, "diver collects", 8, -4)}
    {leader(moth[0], moth[1], moth[0] + 30, moth[1] - 6, "mothership / depot", 8, -4)}
    {leader(transfer[0], transfer[1], transfer[0] + 44, transfer[1] + 10, "transfer", 8, 16)}
    """
    return Diagram(
        "04_diver_plus_mothership.svg",
        "Diver + mothership",
        "Derived hybrid: a diver makes the hot pass, but its period differs from the mothership unless it waits for later rendezvous or uses aerodynamic control.",
        '<a href="https://www.osti.gov/biblio/4163348" target="_blank" rel="noopener noreferrer">PROFAC precedent</a>; <a href="https://ui.adsabs.harvard.edu/abs/2010aero.conf...13J/abstract" target="_blank" rel="noopener noreferrer">PHARO abstract</a>; <a href="https://www.hpepl.ae.gatech.edu/papers/ProgAerospace_Singh_V75_2015_pp15-25.pdf" target="_blank" rel="noopener noreferrer">LEO propellant collection review</a>',
        svg_document("Diver + mothership", body),
    )


def diagram_collector_depot_cycle() -> Diagram:
    low_r = EARTH_R + 48
    high_r = EARTH_R + 220
    collect_arc_start = -20
    collect_arc_end = 56
    collector = polar(CX, CY, low_r, collect_arc_end)
    depot = polar(CX, CY, high_r, collect_arc_end + 180)
    powered_skim = polar(CX, CY, low_r, collect_arc_end + 180)
    outward_transfer = focused_transfer_arc(low_r, high_r, collect_arc_end, 0, 180)
    return_transfer = focused_transfer_arc(low_r, high_r, collect_arc_end + 180, 0, 180)
    outward_mid = polar(CX, CY, (low_r + high_r) / 2 + 36, 128)
    return_mid = polar(CX, CY, (low_r + high_r) / 2 + 12, -48)
    body = f"""
    {earth_and_atmosphere()}
    {orbit_circle(low_r)}
    {orbit_circle(high_r)}
    <path d="{arc_path_circle(CX, CY, low_r, collect_arc_start, collect_arc_end)}" class="collect-arc"/>
    <path d="{outward_transfer}" class="orbit-dashed"/>
    <path d="{return_transfer}" class="orbit-dashed"/>
    {dot(collector[0], collector[1], 7)}
    {dot(depot[0], depot[1], 11, "station")}
    {dot(powered_skim[0], powered_skim[1], 5)}
    <path d="M {fmt(depot[0])} {fmt(depot[1])} L {fmt(powered_skim[0])} {fmt(powered_skim[1])}" class="beam"/>
    {leader(collector[0], collector[1], collector[0] + 46, collector[1] - 4, "collector", 8, -4)}
    {leader(depot[0], depot[1], depot[0] - 42, depot[1] + 18, "depot", -62, 24)}
    <text x="{fmt(collector[0] - 62)}" y="{fmt(collector[1] + 82)}" class="label">collect</text>
    <text x="{fmt(depot[0] - 18)}" y="{fmt(depot[1] - 46)}" class="label">offload</text>
    <text x="{fmt(outward_mid[0] - 54)}" y="{fmt(outward_mid[1] - 10)}" class="soft">loaded transfer to depot</text>
    <text x="{fmt(return_mid[0] - 34)}" y="{fmt(return_mid[1] + 10)}" class="soft">empty return transfer</text>
    <text x="{fmt((depot[0] + powered_skim[0]) / 2 - 34)}" y="{fmt((depot[1] + powered_skim[1]) / 2 - 18)}" class="soft">beamed power during skim</text>
    """
    return Diagram(
        "05_collector_to_depot_cycle.svg",
        "Collector-to-depot cycle",
        "PHARO-like cycle: collect low, receive power from the high system, transfer loaded to a depot, offload, then return empty.",
        '<a href="https://ui.adsabs.harvard.edu/abs/2010aero.conf...13J/abstract" target="_blank" rel="noopener noreferrer">PHARO abstract (2010)</a>; <a href="https://www.hpepl.ae.gatech.edu/papers/ProgAerospace_Singh_V75_2015_pp15-25.pdf" target="_blank" rel="noopener noreferrer">LEO propellant collection review</a>',
        svg_document("Collector-to-depot cycle", body),
    )


def diagram_profac_split() -> Diagram:
    low_r = EARTH_R + 50
    collect_angle = -38
    collector = polar(CX, CY, low_r, collect_angle)
    mission = polar(CX, CY, low_r + 58, collect_angle - 8)
    transfer = ((collector[0] + mission[0]) / 2, (collector[1] + mission[1]) / 2)
    depart_mid = (mission[0] + 120, mission[1] - 60)
    depart_end = (mission[0] + 330, mission[1] - 165)
    body = f"""
    {earth_and_atmosphere()}
    {orbit_circle(low_r)}
    <path d="{arc_path_circle(CX, CY, low_r, -74, -12)}" class="collect-hot"/>
    {dot(collector[0], collector[1], 7)}
    {dot(mission[0], mission[1], 11, "station")}
    {ring(transfer[0], transfer[1], 14)}
    <path d="M {fmt(transfer[0] + 16)} {fmt(transfer[1] - 4)} L {fmt(mission[0] - 16)} {fmt(mission[1] + 10)}" class="arrow-green"/>
    <path d="M {fmt(mission[0] - 18)} {fmt(mission[1] + 16)} C {fmt(mission[0] + 20)} {fmt(mission[1] - 10)} {fmt(depart_mid[0])} {fmt(depart_mid[1])} {fmt(depart_end[0])} {fmt(depart_end[1])}" class="orbit-dashed"/>
    {leader(collector[0], collector[1], collector[0] + 34, collector[1] + 48, "nuclear collector", 8, 18)}
    {leader(mission[0], mission[1], mission[0] + 28, mission[1] - 34, "space vehicle", 8, -4)}
    {leader(transfer[0], transfer[1], transfer[0] - 24, transfer[1] + 22, "transfer", -52, 28)}
    <text x="{fmt(mission[0] - 8)}" y="{fmt(mission[1] - 72)}" class="soft">passing outbound spacecraft</text>
    <text x="{fmt(depart_end[0] - 96)}" y="{fmt(depart_end[1] - 14)}" class="soft">escape / departure path</text>
    """
    return Diagram(
        "06_profac_split_vehicle.svg",
        "PROFAC-style split",
        "PROFAC split: a low collector transfers propellant to a passing outbound spacecraft rather than to a standing depot orbit.",
        '<a href="https://www.osti.gov/biblio/4163348" target="_blank" rel="noopener noreferrer">Demetriades PROFAC (1960)</a>; <a href="https://ui.adsabs.harvard.edu/abs/2010aero.conf...13J/abstract" target="_blank" rel="noopener noreferrer">PHARO comparison point</a>',
        svg_document("PROFAC-style split", body),
    )


def diagram_ed_tether() -> Diagram:
    orbit_r = EARTH_R + 50
    scoop = polar(CX, CY, orbit_r, -28)
    tether_end = (scoop[0] + 65, scoop[1] - 205)
    magnetic_curves = []
    for radius, shift in [(250, 0), (315, 30), (380, 52)]:
        magnetic_curves.append(
            f'<path d="{arc_path_ellipse(CX, CY, radius * 0.65, radius, 214 + shift, 326 - shift / 2)}" class="magnetic"/>'
        )
        magnetic_curves.append(
            f'<path d="{arc_path_ellipse(CX, CY, radius * 0.65, radius, 34 + shift / 3, 146 - shift / 3)}" class="magnetic"/>'
        )
    body = f"""
    {earth_and_atmosphere()}
    {''.join(magnetic_curves)}
    {orbit_circle(orbit_r)}
    {dot(scoop[0], scoop[1], 7)}
    <path d="M {fmt(scoop[0])} {fmt(scoop[1])} L {fmt(tether_end[0])} {fmt(tether_end[1])}" class="tether"/>
    <text x="{fmt(tether_end[0] + 16)}" y="{fmt(tether_end[1] + 6)}" class="label">electrodynamic tether</text>
    <path d="M {fmt(scoop[0] + 2)} {fmt(scoop[1] - 1)} L {fmt(scoop[0] + 18)} {fmt(scoop[1] + 54)}" class="arrow-warm"/>
    <path d="M {fmt(scoop[0] - 2)} {fmt(scoop[1] + 1)} L {fmt(scoop[0] - 18)} {fmt(scoop[1] - 58)}" class="arrow-green"/>
    <text x="{fmt(scoop[0] + 26)}" y="{fmt(scoop[1] + 70)}" class="soft">drag</text>
    <text x="{fmt(scoop[0] - 108)}" y="{fmt(scoop[1] - 64)}" class="soft">thrust</text>
    {leader(scoop[0], scoop[1], scoop[0] + 28, scoop[1] + 46, "scoop", 6, 20)}
    <text x="{fmt(CX + 185)}" y="{fmt(CY + 250)}" class="label">Lorentz thrust offsets drag</text>
    """
    return Diagram(
        "07_electrodynamic_tether_assist.svg",
        "Electrodynamic tether assist",
        "A tether-assisted scoop uses Lorentz thrust to counter drag instead of spending onboard propellant.",
        '<a href="https://ui.adsabs.harvard.edu/abs/1998sct..conf..147G/abstract" target="_blank" rel="noopener noreferrer">Electrodynamic tether propulsion</a>; <a href="https://deepblue.lib.umich.edu/bitstreams/1400a7e4-f5d3-4821-b732-3b7062709329/download" target="_blank" rel="noopener noreferrer">technical paper</a>; <a href="https://ntrs.nasa.gov/api/citations/20160007056/downloads/20160007056.pdf" target="_blank" rel="noopener noreferrer">TSS lessons learned</a>; <a href="https://aerospaceamerica.aiaa.org/year-in-review/tethers-demonstrate-propellantless-propulsion-in-low-earth-orbit/" target="_blank" rel="noopener noreferrer">Prox-1 demo</a>',
        svg_document("Electrodynamic tether assist", body),
    )


def diagram_beamed_power() -> Diagram:
    low_r = EARTH_R + 48
    high_r = EARTH_R + 235
    beam_angle = -32
    collector = polar(CX, CY, low_r, beam_angle)
    power = polar(CX, CY, high_r, beam_angle)
    body = f"""
    {earth_and_atmosphere()}
    {orbit_circle(low_r)}
    {orbit_circle(high_r)}
    <path d="{arc_path_circle(CX, CY, low_r, -62, -8)}" class="collect-arc"/>
    {dot(collector[0], collector[1], 7)}
    {dot(power[0], power[1], 11, "station")}
    <path d="M {fmt(power[0])} {fmt(power[1])} L {fmt(collector[0])} {fmt(collector[1])}" class="beam"/>
    {leader(collector[0], collector[1], collector[0] + 36, collector[1] + 46, "collector", 8, 20)}
    {leader(power[0], power[1], power[0] + 28, power[1] - 30, "power station", 8, -4)}
    <text x="{fmt((power[0] + collector[0]) / 2 + 18)}" y="{fmt((power[1] + collector[1]) / 2 - 8)}" class="soft">power beam</text>
    <text x="{fmt(CX + 142)}" y="{fmt(CY + 250)}" class="label">large power source stays high</text>
    <text x="{fmt(collector[0] - 130)}" y="{fmt(collector[1] + 108)}" class="soft">collection / drag</text>
    """
    return Diagram(
        "08_beamed_power_scoop.svg",
        "Beamed-power scoop",
        "Derived remote-power variant: a high station beams energy to a low draggy collector.",
        '<a href="https://ui.adsabs.harvard.edu/abs/2010aero.conf...13J/abstract" target="_blank" rel="noopener noreferrer">PHARO abstract</a>',
        svg_document("Beamed-power scoop", body),
    )


def diagram_high_altitude_electric() -> Diagram:
    orbit_r = EARTH_R + 140
    collector = polar(CX, CY, orbit_r, -34)
    body = [
        earth_and_atmosphere(
            f'<circle cx="{fmt(CX)}" cy="{fmt(CY)}" r="{fmt(EARTH_R + 135)}" class="ionosphere"/>'
        ),
        orbit_circle(orbit_r),
        dot(collector[0], collector[1], 7),
        f'<ellipse cx="{fmt(collector[0])}" cy="{fmt(collector[1])}" rx="82" ry="58" class="field"/>',
        f'<ellipse cx="{fmt(collector[0])}" cy="{fmt(collector[1])}" rx="98" ry="72" class="field" opacity="0.25"/>',
        f'<text x="{fmt(CX - 46)}" y="{fmt(CY - EARTH_R - 150)}" class="soft">ionosphere</text>',
        leader(collector[0], collector[1], collector[0] + 32, collector[1] + 52, "collector", 8, 22),
        f'<text x="{fmt(collector[0] + 112)}" y="{fmt(collector[1] - 4)}" class="label">field capture area</text>',
    ]
    particle_specs = [
        (collector[0] + 160, collector[1] - 90, collector[0] + 96, collector[1] - 44),
        (collector[0] + 180, collector[1] - 18, collector[0] + 106, collector[1] - 4),
        (collector[0] + 140, collector[1] + 70, collector[0] + 92, collector[1] + 34),
        (collector[0] - 140, collector[1] - 72, collector[0] - 94, collector[1] - 34),
    ]
    for x1, y1, x2, y2 in particle_specs:
        body.append(f'<circle cx="{fmt(x1)}" cy="{fmt(y1)}" r="3" fill="{FIELD}" opacity="0.7"/>')
        body.append(f'<path d="M {fmt(x1)} {fmt(y1)} L {fmt(x2)} {fmt(y2)}" class="arrow"/>')
    return Diagram(
        "09_high_altitude_electric_scoop.svg",
        "High-altitude electric scoop",
        "An electric scoop gathers ionospheric particles with a large electromagnetic capture area rather than a big funnel.",
        '<a href="https://www.iris.sssup.it/retrieve/ea75eb42-2e80-462b-be1e-588ed43871e3/Andreussi%20et.al.%202022.pdf" target="_blank" rel="noopener noreferrer">Andreussi et al. ABEP review</a>; <a href="https://www.sciencedirect.com/science/article/abs/pii/S0094576521003301" target="_blank" rel="noopener noreferrer">ABEP intake / RF helicon thruster intake</a>; <a href="https://www.esa.int/Enabling_Support/Space_Engineering_Technology/World-first_firing_of_air-breathing_electric_thruster" target="_blank" rel="noopener noreferrer">ESA ABEP demo</a>',
        svg_document("High-altitude electric scoop", "".join(body)),
    )


def diagram_distributed_collectors() -> Diagram:
    low_r = EARTH_R + 54
    high_r = EARTH_R + 235
    depot_angle = -88
    depot = polar(CX, CY, high_r, depot_angle)
    collector_angles = [-18, 34, 118, 214, 302]
    parts = [
        earth_and_atmosphere(),
        orbit_circle(low_r),
        orbit_circle(high_r),
        dot(depot[0], depot[1], 11, "station"),
        leader(depot[0], depot[1], depot[0] + 32, depot[1] - 36, "central depot", 6, -4),
        f'<text x="{fmt(CX - 130)}" y="{fmt(CY + low_r + 34)}" class="label">distributed collection</text>',
        f'<text x="{fmt(CX + 170)}" y="{fmt(CY - 16)}" class="soft">rendezvous + offload</text>',
    ]
    for angle in collector_angles:
        cxp, cyp = polar(CX, CY, low_r, angle)
        parts.append(dot(cxp, cyp, 6))
        parts.append(f'<path d="{focused_transfer_arc(low_r, high_r, angle, 0, 180)}" class="orbit-dashed"/>')
    parts.append(ring(depot[0], depot[1], 16))
    return Diagram(
        "10_distributed_collectors_central_depot.svg",
        "Distributed collectors + central depot",
        "Derived depot network: many small collectors transfer to one shared higher depot.",
        '<a href="https://ui.adsabs.harvard.edu/abs/2010aero.conf...13J/abstract" target="_blank" rel="noopener noreferrer">PHARO abstract</a>; <a href="https://www.hpepl.ae.gatech.edu/papers/ProgAerospace_Singh_V75_2015_pp15-25.pdf" target="_blank" rel="noopener noreferrer">LEO propellant collection review</a>',
        svg_document("Distributed collectors + central depot", "".join(parts)),
    )


def diagram_deep_nitrogen() -> Diagram:
    nested = (
        f'<circle cx="{fmt(CX)}" cy="{fmt(CY)}" r="{fmt(EARTH_R + 12)}" fill="none" stroke="{ATMOS_2}" stroke-opacity="0.22" stroke-width="18"/>'
        f'<circle cx="{fmt(CX)}" cy="{fmt(CY)}" r="{fmt(EARTH_R + 28)}" fill="none" stroke="{ATMOS_1}" stroke-opacity="0.18" stroke-width="18"/>'
        f'<circle cx="{fmt(CX)}" cy="{fmt(CY)}" r="{fmt(EARTH_R + 48)}" fill="none" stroke="{ATMOS_1}" stroke-opacity="0.13" stroke-width="20"/>'
    )
    ex, ey, rx, ry = focused_vertical_orbit(260, 155)
    collector = ellipse_point(ex, ey, rx, ry, 90)
    apogee = ellipse_point(ex, ey, rx, ry, 270)
    station_r = EARTH_R + 280
    station = polar(CX, CY, station_r, -32)
    body = f"""
    {earth_and_atmosphere(nested)}
    {orbit_ellipse_at(ex, ey, rx, ry)}
    <path d="{arc_path_ellipse(ex, ey, rx, ry, 76, 104)}" class="collect-hot"/>
    <path d="{sampled_ellipse_segment(ex, ey, rx, ry, 156, 384)}" class="recovery-arc"/>
    <path d="{arc_path_ellipse(ex, ey, rx, ry, 126, 156)}" class="collect-arc"/>
    <path d="{arc_path_ellipse(ex, ey, rx, ry, 24, 54)}" class="collect-arc"/>
    {dot(collector[0], collector[1], 7)}
    {dot(station[0], station[1], 11, "station")}
    {leader(collector[0], collector[1], collector[0] + 22, collector[1] - 52, "deep collector", 8, -4)}
    {leader(station[0], station[1], station[0] + 34, station[1] - 36, "courier craft", 8, -4)}
    <text x="{fmt(CX - 154)}" y="{fmt(CY + 176)}" class="label">nitrogen-rich / severe heating</text>
    <text x="{fmt(apogee[0] - 100)}" y="{fmt(apogee[1] - 40)}" class="label" fill="{RECOVERY}">gas liquefaction</text>
    <path d="M {fmt(CX + 40)} {fmt(CY + 20)} L {fmt(CX - 80)} {fmt(CY + 57.5)}" class="leader"/>
    <path d="M {fmt(CX + 46)} {fmt(CY + 22)} L {fmt(CX + 148)} {fmt(CY + 91)}" class="leader"/>
    <text x="{fmt(CX + 50)}" y="{fmt(CY + 18)}" class="soft">ion thrusters fire close to perigee</text>
    <text x="{fmt(CX + 98)}" y="{fmt(CY + 40)}" class="soft">when outside deep atmosphere</text>
    <text x="{fmt(station[0] + 38)}" y="{fmt(station[1] - 16)}" class="soft">own thrusters</text>
    """
    return Diagram(
        "11_deep_nitrogen_split_scoop.svg",
        "Deep nitrogen split-scoop",
        "Original nitrogen-driven variant: a deeper hotter collector pass is split from the higher storage infrastructure.",
        '<a href="https://www.hpepl.ae.gatech.edu/papers/ProgAerospace_Singh_V75_2015_pp15-25.pdf" target="_blank" rel="noopener noreferrer">LEO propellant collection review</a>; <a href="https://hpepl.ae.gatech.edu/papers/Singh.pdf" target="_blank" rel="noopener noreferrer">VLEO propellant collection feasibility</a>; <a href="https://www.osti.gov/biblio/4163348" target="_blank" rel="noopener noreferrer">PROFAC precedent</a>',
        svg_document("Deep nitrogen split-scoop", body),
    )


def diagram_jousters() -> Diagram:
    ex, ey, rx, ry = focused_vertical_orbit(255, 178)
    perigee = ellipse_point(ex, ey, rx, ry, 90)
    apogee = ellipse_point(ex, ey, rx, ry, 270)
    left_mid = ellipse_point(ex, ey, rx, ry, 160)
    right_mid = ellipse_point(ex, ey, rx, ry, 20)
    body = f"""
    {earth_and_atmosphere()}
    {orbit_ellipse_at(ex, ey, rx, ry)}
    {orbit_arrow_ellipse_at(ex, ey, rx, ry, 145)}
    {dot(left_mid[0], left_mid[1], 7)}
    {dot(right_mid[0], right_mid[1], 7)}
    {dot(perigee[0] - 10, perigee[1], 6)}
    {dot(perigee[0] + 10, perigee[1], 6)}
    {dot(apogee[0] - 10, apogee[1], 6)}
    {dot(apogee[0] + 10, apogee[1], 6)}
    {ring(perigee[0], perigee[1], 16)}
    {ring(apogee[0], apogee[1], 16)}
    <path d="M {fmt(perigee[0] - 34)} {fmt(perigee[1])} L {fmt(perigee[0] - 4)} {fmt(perigee[1])}" class="arrow-green"/>
    <path d="M {fmt(perigee[0] + 34)} {fmt(perigee[1])} L {fmt(perigee[0] + 4)} {fmt(perigee[1])}" class="arrow-green"/>
    <path d="M {fmt(apogee[0] - 34)} {fmt(apogee[1])} L {fmt(apogee[0] - 4)} {fmt(apogee[1])}" class="arrow-warm"/>
    <path d="M {fmt(apogee[0] + 34)} {fmt(apogee[1])} L {fmt(apogee[0] + 4)} {fmt(apogee[1])}" class="arrow-warm"/>
    {leader(left_mid[0], left_mid[1], left_mid[0] - 48, left_mid[1] - 22, "craft A", -56, -4)}
    {leader(right_mid[0], right_mid[1], right_mid[0] + 40, right_mid[1] + 24, "craft B", 8, 20)}
    <text x="{fmt(perigee[0] - 120)}" y="{fmt(perigee[1] + 52)}" class="label">perigee push-off boost</text>
    <text x="{fmt(apogee[0] - 90)}" y="{fmt(apogee[1] - 38)}" class="label">apogee control push</text>
    <text x="{fmt(CX + 168)}" y="{fmt(CY + 246)}" class="soft">reverse travel on same ellipse</text>
    """
    return Diagram(
        "12_jousters.svg",
        "Jousters",
        "Original concept: two craft run the same ellipse in opposite directions and exchange push-off impulses at perigee and apogee.",
        "",
        svg_document("Jousters", body),
    )


def all_diagrams() -> list[Diagram]:
    return [
        diagram_legend(),
        diagram_single_body(),
        diagram_tethered_trawler(),
        diagram_elliptical_diver(),
        diagram_diver_mothership(),
        diagram_collector_depot_cycle(),
        diagram_profac_split(),
        diagram_ed_tether(),
        diagram_beamed_power(),
        diagram_high_altitude_electric(),
        diagram_distributed_collectors(),
        diagram_deep_nitrogen(),
        diagram_jousters(),
    ]


def build_index(diagrams: Iterable[Diagram]) -> str:
    originals = {"11_deep_nitrogen_split_scoop.svg", "12_jousters.svg"}

    def render_card(item: Diagram) -> str:
        return (
            f"""
            <article class="card">
              <h2>{html.escape(item.title)}</h2>
              <a class="frame" href="{html.escape(item.filename)}" target="_blank" rel="noopener noreferrer" title="Open full-size SVG">
                <img src="{html.escape(item.filename)}" alt="{html.escape(item.title)}" />
              </a>
              <p class="caption">{html.escape(item.blurb)}</p>
              {f'<p class="source"><span>Source:</span> {item.source_html}</p>' if item.source_html else '<p class="source"><span>Source:</span> original legend / no external source</p>'}
              <p class="meta">{html.escape(item.filename)}</p>
            </article>
            """
        )
    reference_cards = []
    original_cards = []
    for item in diagrams:
        if item.filename in originals:
            original_cards.append(render_card(item))
        else:
            reference_cards.append(render_card(item))
    comparison = """
    <section class="notes">
      <h2>Acronyms And Architecture</h2>
      <p><strong>PROFAC</strong> means <em>Propulsive Fluid Accumulator</em>: the older Demetriades concept in which a low atmospheric collector acts more like a self-filling orbital fuel station and can directly support a separate mission vehicle.</p>
      <p><strong>PHARO</strong> means <em>Propellant Harvesting of Atmospheric Resources in Orbit</em>: the later depot-oriented concept in which collector craft harvest low, then transfer propellant into a higher logistics and storage system.</p>
      <p><strong>Orbital design difference:</strong> PROFAC is closer to a low collector or collector-plus-space-vehicle arrangement, while PHARO is closer to a collector fleet plus higher depot architecture with externalized power and logistics.</p>
      <p><strong>Power difference:</strong> PROFAC is historically tied to onboard nuclear or plasma-power assumptions, while PHARO shifts the burden toward orbital infrastructure such as beamed power and distributed depot operations.</p>
    </section>
    """
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Orbital Scoop SVGs</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #0f1419;
      --panel: #182028;
      --panel-border: #273341;
      --text: #e8edf2;
      --muted: #9eb0c2;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      padding: 28px;
      background: var(--bg);
      color: var(--text);
      font: 16px/1.4 Arial, Helvetica, sans-serif;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 28px;
    }}
    p.lead {{
      margin: 0 0 24px;
      color: var(--muted);
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 20px;
    }}
    .card {{
      background: var(--panel);
      border: 1px solid var(--panel-border);
      border-radius: 12px;
      padding: 16px;
    }}
    .card h2 {{
      margin: 0 0 10px;
      font-size: 18px;
    }}
    .frame {{
      display: block;
      background: #0c1116;
      border-radius: 8px;
      overflow: hidden;
      border: 1px solid #202a35;
      transition: border-color 120ms ease, transform 120ms ease;
    }}
    .frame:hover {{
      border-color: #4d7ea8;
      transform: translateY(-1px);
    }}
    img {{
      display: block;
      width: 100%;
      height: auto;
    }}
    .card p {{
      margin: 10px 0 0;
    }}
    .caption {{
      color: var(--text);
      font-size: 14px;
      line-height: 1.45;
    }}
    .meta {{
      margin: 10px 0 0;
      color: var(--muted);
      font-size: 14px;
    }}
    .source {{
      margin: 8px 0 0;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
    }}
    .source span {{
      color: var(--text);
    }}
    .source a {{
      color: #9fd1ff;
      text-decoration: none;
    }}
    .source a:hover {{
      text-decoration: underline;
    }}
    .section-title {{
      margin: 0 0 16px;
      font-size: 22px;
    }}
    .section-block {{
      margin-top: 18px;
    }}
    .notes {{
      margin-top: 28px;
      padding: 18px 20px;
      background: var(--panel);
      border: 1px solid var(--panel-border);
      border-radius: 12px;
    }}
    .notes h2 {{
      margin: 0 0 12px;
      font-size: 20px;
    }}
    .notes p {{
      margin: 10px 0 0;
      color: var(--muted);
      line-height: 1.5;
    }}
    .notes strong {{
      color: var(--text);
    }}
  </style>
</head>
<body>
  <h1>Orbital Scoop SVG Set</h1>
  <p class="lead">Standalone schematic SVG diagrams generated for atmospheric scoop architecture concepts.</p>
  <section class="section-block">
    <h2 class="section-title">ToughSF References</h2>
    <section class="grid">
      {''.join(reference_cards)}
    </section>
  </section>
  {comparison}
  <section class="section-block">
    <h2 class="section-title">Original Designs</h2>
    <section class="grid">
      {''.join(original_cards)}
    </section>
  </section>
</body>
</html>
"""


def main() -> None:
    diagrams = all_diagrams()
    OUT_DIR.mkdir(exist_ok=True)
    for diagram in diagrams:
      (OUT_DIR / diagram.filename).write_text(diagram.body, encoding="utf-8")
    (OUT_DIR / "index.html").write_text(build_index(diagrams), encoding="utf-8")
    for diagram in diagrams:
        print(diagram.filename)
    print("index.html")


if __name__ == "__main__":
    main()
