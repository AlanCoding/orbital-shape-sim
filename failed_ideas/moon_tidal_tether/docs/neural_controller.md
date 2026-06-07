# Neural-Net Controller Guide

This guide describes how to train the neural-network controller, inspect its Figure of Merit (FOM), and run simulations using the trained weights.

## Train the controller

Run the training script with a base simulation config:

```bash
PYTHONPATH=src python sims/train_nn_controller.py --iterations 50 --output nn_controller_weights.npy
```

- `--config` selects the YAML config (default `configs/leo_100km.yaml`).
- `--output` chooses where to save the best weights. The file is created relative to the current directory unless an absolute path is given.
- Each iteration prints the candidate and best FOM values so you can monitor progress:

```
iter 0: FOM=123.4, best=123.4
iter 1: FOM=120.0, best=123.4
...
Saved best parameters to nn_controller_weights.npy
```

## Use the trained weights

Create a controller configuration that points to the saved weight file:

```yaml
controller:
  type: neural_net
  max_accel: 0.01      # should match the training config
  weights: nn_controller_weights.npy
```

You can place this in a new YAML file (e.g., `configs/leo_nn.yaml`) or override fields from the command line.

Run a simulation:

```bash
PYTHONPATH=src python sims/run_leo_100km.py --config configs/leo_nn.yaml
```

To directly evaluate the FOM of the trained controller:

```bash
PYTHONPATH=src python sims/run_fom_scenarios.py --controller neural_net --override controller.weights=nn_controller_weights.npy
```

This prints the FOM achieved by the neural controller.
