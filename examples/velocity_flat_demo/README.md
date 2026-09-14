# Velocity flat demo (2048 × 500) — Phase 2 baseline

| Field | Value |
|---|---|
| Config | 2048 env × 500 iter (upstream default) |
| Checkpoint | `model_499.pt` |
| MI210 wall time | ~10 min |
| Final mean reward | ~94 |
| Mean episode length | ~888 |

**Phase 2 eval:**

```bash
cd /opt/microduck_rl_unilab
microduck-eval --algo ppo --task microduck_velocity_flat --sim mujoco \
  --load-run /workspace/microduck_rl_lab/examples/velocity_flat_demo \
  training.play_steps=200 training.log_root=/workspace/runs
```

**Optional appendix — continue +500 iter:**

```bash
microduck-train --algo ppo --task microduck_velocity_flat --sim mujoco \
  algo.num_envs=2048 algo.max_iterations=500 algo.save_interval=100 \
  algo.load_run=/workspace/microduck_rl_lab/examples/velocity_flat_demo \
  training.no_play=true training.logger=tensorboard training.log_root=/workspace/runs
```
