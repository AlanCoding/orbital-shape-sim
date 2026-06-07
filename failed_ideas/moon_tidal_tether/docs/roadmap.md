# Roadmap

## Past Development
- Earth central plus lunar tidal environment
- Dual counter-rotating barbell model with quadrupole mapping
- Bang–bang controller and baseline simulation script
- Logging and quicklook plotting utilities

## TODO
- Integrate four-point "kite" structure dynamics
- Consolidate controller-owned initial conditions across craft types
- Validate simulation against higher fidelity models
- Implement full tension constraints
- Implement `tidal_jet_third_deriv` and tensor contraction; run baseline energy-gain simulation
- Add attitude alignment loop and verify torque-free condition
- Implement phase-locked controller with gradient tuning
- Sweep boom extent to verify $(\ell/a)^2$ scaling
- Add drag, J2, and SRP toggles to test robustness
- Add safety checks for tension and structural load margins
- Package result plots and memo in `docs/`
