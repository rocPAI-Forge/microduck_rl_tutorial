# Velocity flat reference demo

This pre-trained asset is the stable baseline used by
`notebooks/02_interactive_teleop.ipynb`. Students do not need to train it.

- Checkpoint: `model_950.pt`
- Training scale: 2,048 parallel environments
- Selection: 32 trials × 10 seconds for each of six fixed body-frame commands
- Linear result: forward, backward, left, and right all passed the automated gate
- Yaw result at `±0.8 rad/s`: both mean responses have the requested sign and all
  seed-123 trials survived; cross-seed right-turn accuracy remains weaker than
  linear tracking and is documented rather than hidden
- Hardware note: training performance was measured on AMD Instinct MI210, but the
  checkpoint is not tied to MI210

See `cardinal_eval.json` for the complete measurements and `run_summary.json` for
the staged fine-tuning recipe.

## Evaluate

```bash
cd /opt/microduck_rl_unilab
microduck-eval --algo ppo --task microduck_velocity_flat --sim mujoco \
  --load-run /workspace/microduck_rl_lab/examples/velocity_flat_demo \
  training.play_steps=200 training.log_root=/workspace/runs
```

## Re-run the six-direction gate

```bash
python3 /workspace/microduck_rl_lab/scripts/evaluate_cardinal.py \
  /workspace/microduck_rl_lab/examples/velocity_flat_demo/model_950.pt \
  --num-envs 32 --steps 500 --yaw-rate 0.8
```
