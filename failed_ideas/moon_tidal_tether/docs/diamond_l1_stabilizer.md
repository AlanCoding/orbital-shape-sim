# Diamond L1 Stabilizer

The diamond L1 stabilizer controller suppresses the unstable mode of the
Earth–Moon L1 equilibrium point by deforming the kite-shaped craft. The
controller projects the hub state into the rotating Earth–Moon frame and
measures displacement and velocity along the linearized unstable eigenvector
of the circular restricted three-body problem. A proportional–derivative law
produces a commanded stretch of the X-axis tethers: the X± masses are driven
outward while the Y± masses are pulled inward by the same amount. This oblate
quadrupole biases the combined gravitational acceleration back toward L1 and
keeps the craft from diverging along the Earth–Moon line.

Secondary trims are not yet implemented. The intended roadmap is to bias the
Y-axis masses in response to lateral hub velocity (providing gentle tangential
damping) and to modulate the diagonal linkages to counter residual torques.
Those trims will be incorporated in future work once the primary unstable-axis
loop is fully characterized.
