"""Integrity and numerical checks for the single-orbit communication bundle."""
import hashlib
import importlib.util
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

import numpy as np
import pytest


ROOT=Path(__file__).resolve().parents[1]/'docs/aerocycler_27day'


@pytest.fixture(scope='module')
def bundle():
    spec=importlib.util.spec_from_file_location('single_orbit_reproduce',ROOT/'reproduce.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    inputs=json.loads((ROOT/'data/initial_conditions.json').read_text())
    return module,inputs,module.simulate(inputs)


def test_standalone_fixed_state_closes_and_bank_is_passive(bundle):
    module,inputs,(r,t,y,bank,ta)=bundle
    assert r['position_closure_m']<.001
    assert r['velocity_closure_m_s']<1e-6
    assert abs(r['period_days']-27.441335638)<1e-7
    assert r['all_bank_segments_positive_drag']
    assert 25.68<r['maximum_local_LD']<25.69
    np.testing.assert_allclose(y[0],inputs['initial_state_primary_centered_rotating'],rtol=0,atol=1e-14)
    assert np.min(np.linalg.norm(y[:,:3],axis=1))*inputs['separation_km']>=inputs['primary_solid_radius_km']+99.999
    for key in ['initial_osculating','pre_bank_osculating','post_bank_osculating']:
        assert abs(r[key]['inclination_deg']-90)<1.3


def test_flow_relative_forces_and_energy_budget(bundle):
    module,inputs,(r,t,y,bank,ta)=bundle
    np.testing.assert_allclose(np.array(r['drag_impulse_ENR_m_s'])+r['lift_impulse_ENR_m_s'],r['impulse_ENR_m_s'],atol=1e-6)
    assert r['drag_impulse_ENR_m_s'][1]<-18
    assert r['lift_impulse_ENR_m_s'][1]>19
    assert 0<r['impulse_ENR_m_s'][1]<.3
    assert abs(r['impulse_ENR_m_s'][2])<1e-6
    energy=r['energy_J_kg']
    assert energy['atmosphere_relative_work']<0<energy['orbital_gain']
    assert abs(energy['orbital_gain']-energy['rotation_work']-energy['atmosphere_relative_work'])<1e-6


def test_exported_samples_and_frame_transforms(bundle):
    module,inputs,(r,t,y,bank,ta)=bundle
    table=np.loadtxt(ROOT/'data/trajectory.csv',delimiter=',',skiprows=1)
    assert len(table)==len(t)
    np.testing.assert_allclose(table[:,0],t,atol=1e-11)
    np.testing.assert_allclose(table[:,2:8],y,atol=1e-9)
    length=inputs['separation_km'];unit=r['units']['velocity_m_s']/1000
    np.testing.assert_allclose(table[:,8:11],module.rotate(y[:,:3],t)*length,atol=1e-5)
    np.testing.assert_allclose(table[:,11:14],module.rotate(module.inertial_velocity(y),t)*unit,atol=1e-8)
    qb=y[:,:3]-[inputs['mu'],0,0]
    np.testing.assert_allclose(table[:,14:17],module.rotate(qb,t)*length,atol=1e-5)
    np.testing.assert_allclose(table[:,17:20],module.rotate(y[:,3:]+np.cross([0,0,1],qb),t)*unit,atol=1e-8)
    stored=json.loads((ROOT/'data/verification.json').read_text())
    np.testing.assert_allclose(table[-1,2:8],stored['pre_bank_state'],atol=1e-12)
    assert np.linalg.norm(table[-1,8:11]-table[0,8:11])>100 # No false inertial closure.


def test_data_fingerprints_and_viewer_input():
    manifest=json.loads((ROOT/'data/sha256.json').read_text())
    for name,expected in manifest.items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected,name
    js=(ROOT/'orbit-data.js').read_text()
    payload=json.loads(js.split('window.ORBIT_DATA = ',1)[1].removesuffix(';\n'))
    initial=json.loads((ROOT/'data/initial_conditions.json').read_text())
    assert payload['inputs']==initial
    assert payload['samples'][0][1:]==initial['initial_state_primary_centered_rotating']
    assert len(payload['samples'])>6000


def test_local_page_has_no_missing_assets_or_external_dependencies():
    class Links(HTMLParser):
        paths=[]
        def handle_starttag(self,tag,attrs):
            for key,value in attrs:
                if key in ['src','href'] and value and not value.startswith('#'):
                    self.paths.append(value)
    parser=Links();parser.feed((ROOT/'index.html').read_text())
    for link in parser.paths:
        url=urlsplit(link)
        assert not url.scheme,link
        assert (ROOT/url.path).is_file(),link
