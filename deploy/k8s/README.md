# Kubernetes (optional)

Minimal template for the same `microduck-rl-tutorial:rocm714-py312` image used by Docker Compose.

**Prerequisites**

- AMD GPU node with ROCm driver
- `/dev/kfd` and `/dev/dri` visible on the node (template uses hostPath + privileged)
- Adjust `amd.com/gpu` resource name to match your device plugin (may differ by cluster)

**Apply**

```bash
# Build/load the image on the node or push to your registry and update the image field.
kubectl apply -f lab-deployment.yaml
kubectl port-forward svc/microduck-rl-tutorial 8888:8888
```

Open Jupyter at `http://localhost:8888` (token printed in pod logs).

Training output persists on PVC `microduck-runs` at `/workspace/runs`.
