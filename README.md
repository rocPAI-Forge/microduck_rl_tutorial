# microduck_rl_lab

Beginner-friendly Jupyter lab for MicroDuck omnidirectional velocity RL on AMD ROCm.

## Three-phase course (v2.4)

The notebook starts from RL/MDP fundamentals, explains why PPO is used, maps the
reward and domain-randomization design to MicroDuck, and shows how ROCm,
PyTorch, UniLab, `microduck_rl_unilab`, and this teaching repository fit
together.

| Phase | Config | Activity |
|---|---|---|
| **Smoke** | **4 × 2 iter** | Validate the full stack and inspect raw training logs |
| **1** | **500 × 300 iter** (~5 min GPU) | Student trains from scratch |
| **2** | **2048 × 500 iter** (bundled demo) | Student evals pretrained checkpoint |
| **3** | Compare | reward, episode length, video, curriculum |
| *Optional* | demo + **500 iter** continue | Appendix homework (~10 min) |

Phase 1 keeps notebook output throttled to one status refresh every 10
iterations, writes the complete log to `runs/logs/phase1_500x300.log`, and
renders a 10-second (500 control-step) evaluation video.

Demo checkpoint: [`examples/velocity_flat_demo/`](examples/velocity_flat_demo/) (`model_499.pt`, ~4.7 MB).

## Quick start

```bash
docker compose build && docker compose up
```

Open [`notebooks/01_velocity_lab.ipynb`](notebooks/01_velocity_lab.ipynb).

## Demo metrics (2048×500, MI210)

~10 min train · final reward ~94 · episode length ~888/1000

## Related

- [microduck_rl_unilab](https://github.com/unilabsim/microduck_rl_unilab)
- [UniLab](https://github.com/unilabsim/UniLab)
