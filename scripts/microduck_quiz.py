#!/usr/bin/env python3
"""Five-question lesson check for the MicroDuck hands-on lab.

Questions follow the commands students actually run in
``notebooks/{zh,en}/01_velocity_lab.ipynb`` and ``02_interactive_teleop.ipynb``.
Order is fixed: no sampling, no choice shuffling.

Used from the notebooks through :func:`launch`. Also runs standalone:
``python3 scripts/microduck_quiz.py --lang zh``.
"""
from __future__ import annotations

import argparse
from typing import Any

LETTERS = "ABCD"

QUESTIONS: dict[str, list[dict[str, Any]]] = {
    "zh": [
        {
            "topic": "冒烟测试",
            "prompt": "你先跑了 `algo.num_envs=4 algo.max_iterations=2` 的冒烟测试。这一步的目的是什么？",
            "choices": [
                "训练出一个可以正常行走的策略",
                "验证 ROCm、任务注册、MuJoCo、采样和 checkpoint 写入这条链路能跑通",
                "把机器人的 14 个关节标定到零位",
                "生成阶段二要用的 model_950.pt",
            ],
            "answer": 1,
            "why": "2 个 iteration 不可能学会走路。这一步只确认整条链路不报错，同时让你第一次看到完整训练日志的字段（Learning iteration、Mean reward、Mean episode length 等）。",
            "ref": "01 · F 冒烟测试",
        },
        {
            "topic": "训练参数",
            "prompt": "阶段一的命令里有 `algo.num_envs=500 algo.max_iterations=300`。这两个数分别表示什么？",
            "choices": [
                "机器人有 500 个关节，训练 300 秒",
                "每个 episode 500 步，视频 300 帧",
                "500 个并行仿真环境；重复 300 次“采样 + 更新网络”",
                "reward 上限 500，episode length 上限 300",
            ],
            "answer": 2,
            "why": "`num_envs` 是同时运行的独立 MicroDuck 仿真数量，决定每轮能收集多少数据；`max_iterations` 是“采样 24 步 → 更新网络”这个循环重复的次数。",
            "ref": "01 · 阶段一参数表 / D3",
        },
        {
            "topic": "Eval 回放",
            "prompt": "阶段一 eval 用了 `training.play_steps=500`，策略控制频率是 50 Hz。生成的视频大约多长？",
            "choices": [
                "500 秒",
                "50 秒",
                "取决于机器人摔倒的时间，无法计算",
                "10 秒",
            ],
            "answer": 3,
            "why": "50 Hz 表示每步 0.02 秒，所以 500 × 0.02 s = 10 秒。注意这是整段视频长度，不是每个 episode 的存活时间——机器人可能在这 10 秒里多次摔倒并 reset。",
            "ref": "01 · 阶段一 Eval",
        },
        {
            "topic": "参考 Demo",
            "prompt": "阶段二直接加载仓库自带的 `examples/velocity_flat_demo/model_950.pt`。为什么不让学员自己训出这个模型？",
            "choices": [
                "因为它是 2048 环境长时间训练并经过方向验收的参考资产，课堂时间不够重新训练",
                "因为这个模型只能在 MI210 上加载",
                "因为自己训练出来的模型不能用于 eval",
                "因为 950 这个数字是 PPO 要求的固定 iteration 数",
            ],
            "answer": 0,
            "why": "它用 2048 个并行环境定向微调，并用六方向固定命令自动评测选出，用来和你自己的 300-iter 结果做对比。课堂上重训要花很久，所以直接提供。模型本身不绑定 MI210。",
            "ref": "01 · 阶段二",
        },
        {
            "topic": "键盘遥操作",
            "prompt": "在 02 的遥操作窗口里按下 `↑` 键，机器人实际收到的是什么？",
            "choices": [
                "14 个关节角度的直接指令",
                "让 MuJoCo 相机向前移动的指令",
                "一条向前的速度命令 (vx=+0.2, vy=0, yaw=0)，再由 PPO Actor 算出关节动作",
                "提高 max_iterations 继续训练的指令",
            ],
            "answer": 2,
            "why": "键盘设置的是机体坐标系下的期望速度，不是关节角。闭环是：速度命令 → 61 维观测 → PPO Actor → 14 维关节目标 → BAM 执行器 → MuJoCo。",
            "ref": "02 · 第 2 节 键盘控制",
        },
    ],
    "en": [
        {
            "topic": "Smoke test",
            "prompt": "You first ran the smoke test with `algo.num_envs=4 algo.max_iterations=2`. What is that step for?",
            "choices": [
                "To train a policy that can already walk properly",
                "To verify the whole chain runs: ROCm, task registration, MuJoCo, sampling, and checkpoint writing",
                "To calibrate the robot's 14 joints to zero position",
                "To generate the model_950.pt used in phase 2",
            ],
            "answer": 1,
            "why": "Two iterations cannot learn to walk. This step only confirms nothing errors out, and it shows you the full training log fields for the first time (Learning iteration, Mean reward, Mean episode length).",
            "ref": "01 · F smoke test",
        },
        {
            "topic": "Training parameters",
            "prompt": "The phase 1 command contains `algo.num_envs=500 algo.max_iterations=300`. What do those two numbers mean?",
            "choices": [
                "The robot has 500 joints and trains for 300 seconds",
                "500 steps per episode and 300 frames of video",
                "500 parallel simulated environments; repeat 300 times of \"sample, then update the network\"",
                "A reward cap of 500 and an episode-length cap of 300",
            ],
            "answer": 2,
            "why": "`num_envs` is how many independent MicroDuck simulations run at once, which sets how much data each round collects. `max_iterations` is how many times the \"sample 24 steps, then update\" loop repeats.",
            "ref": "01 · phase 1 parameter table / D3",
        },
        {
            "topic": "Eval replay",
            "prompt": "Phase 1 eval uses `training.play_steps=500`, and the control rate is 50 Hz. Roughly how long is the video?",
            "choices": [
                "500 seconds",
                "50 seconds",
                "It depends on when the robot falls and cannot be computed",
                "10 seconds",
            ],
            "answer": 3,
            "why": "50 Hz means 0.02 s per step, so 500 x 0.02 s = 10 seconds. Note this is the clip length, not each episode's lifetime; the robot may fall and reset several times within it.",
            "ref": "01 · phase 1 eval",
        },
        {
            "topic": "Reference demo",
            "prompt": "Phase 2 loads the bundled `examples/velocity_flat_demo/model_950.pt` directly. Why not have students train it themselves?",
            "choices": [
                "Because it is a 2048-env, direction-tuned reference asset and class time is too short to retrain it",
                "Because that checkpoint only loads on MI210",
                "Because self-trained models cannot be used for eval",
                "Because 950 is a fixed iteration count required by PPO",
            ],
            "answer": 0,
            "why": "It was fine-tuned with 2048 parallel envs and selected by an automatic six-direction fixed-command gate, so you can compare it against your own 300-iter result. Retraining it in class would take far too long. The checkpoint is not MI210-specific.",
            "ref": "01 · phase 2",
        },
        {
            "topic": "Keyboard teleop",
            "prompt": "In the notebook 02 teleop window you press the `Up` arrow. What does the robot actually receive?",
            "choices": [
                "Direct target angles for all 14 joints",
                "A command that moves the MuJoCo camera forward",
                "A forward velocity command (vx=+0.2, vy=0, yaw=0), which the PPO actor turns into joint actions",
                "A command that raises max_iterations and resumes training",
            ],
            "answer": 2,
            "why": "The keyboard sets a desired velocity in the robot body frame, not joint angles. The loop is velocity command, 61-D observation, PPO actor, 14-D joint targets, BAM actuator, MuJoCo.",
            "ref": "02 · section 2 keyboard control",
        },
    ],
}

UI: dict[str, dict[str, str]] = {
    "zh": {
        "start": "开始答题",
        "restart": "重做",
        "submit": "提交",
        "intro": "共 {n} 道单选题，全部来自你在本课实际运行过的步骤。点击下面的按钮开始。",
        "drawn": "请逐题选择，选完后点“提交”。",
        "unanswered": "还有未作答的题目：",
        "score": "得分：{score} / {total}",
        "correct": "正确",
        "wrong": "错误",
        "your_pick": "你的选择",
        "answer": "正确答案",
        "why": "解析",
        "ref": "对应章节",
        "full": "全部正确。你已经把命令参数、eval 时长和推理闭环对应起来了。",
        "most": "大部分正确。请按解析里的章节回看答错的那几题。",
        "few": "建议回到 01 的阶段一、阶段二和 02 的键盘控制小节重看一遍，再测一次。",
    },
    "en": {
        "start": "Start quiz",
        "restart": "Retry",
        "submit": "Submit",
        "intro": "{n} single-choice questions, all based on steps you actually ran in this lesson. Click the button to begin.",
        "drawn": "Answer each item, then click Submit.",
        "unanswered": "Still unanswered:",
        "score": "Score: {score} / {total}",
        "correct": "Correct",
        "wrong": "Incorrect",
        "your_pick": "You picked",
        "answer": "Answer",
        "why": "Why",
        "ref": "Section",
        "full": "All correct. You can now connect command parameters, eval duration, and the inference loop.",
        "most": "Mostly correct. Revisit the sections listed for the items you missed.",
        "few": "Reread phase 1, phase 2 in 01 and the keyboard control section in 02, then try again.",
    },
}


def get_questions(lang: str) -> list[dict[str, Any]]:
    """Return the fixed question list for `lang` (same order every time)."""
    return QUESTIONS[lang]


def _verdict(lang: str, score: int, total: int) -> str:
    t = UI[lang]
    if score == total:
        return t["full"]
    return t["most"] if score >= 3 else t["few"]


def launch(lang: str = "zh"):
    """Render a Start button in Jupyter; clicking it shows the five questions."""
    import ipywidgets as w
    from IPython.display import display

    t = UI[lang]
    questions = get_questions(lang)
    header = w.HTML(f"<p>{t['intro'].format(n=len(questions))}</p>")
    start = w.Button(description=t["start"], button_style="primary", icon="play")
    body = w.VBox([])

    def render(_=None):
        start.description = t["restart"]
        picks = []
        rows = [w.HTML(f"<p>{t['drawn']}</p>")]
        for idx, q in enumerate(questions, start=1):
            radio = w.RadioButtons(
                options=[(f"{LETTERS[i]}. {c}", i) for i, c in enumerate(q["choices"])],
                value=None,
                layout=w.Layout(width="100%"),
            )
            picks.append(radio)
            rows.append(
                w.VBox(
                    [
                        w.HTML(f"<h4>Q{idx} · {q['topic']}</h4><p>{q['prompt']}</p>"),
                        radio,
                        w.HTML("<hr>"),
                    ]
                )
            )

        out = w.Output()
        submit = w.Button(description=t["submit"], button_style="success")

        def on_submit(_):
            out.clear_output()
            missing = [f"Q{i}" for i, p in enumerate(picks, start=1) if p.value is None]
            with out:
                if missing:
                    print(t["unanswered"], ", ".join(missing))
                    return
                score = sum(p.value == q["answer"] for q, p in zip(questions, picks))
                print(t["score"].format(score=score, total=len(questions)), end="\n\n")
                for i, (q, p) in enumerate(zip(questions, picks), start=1):
                    ok = p.value == q["answer"]
                    print(f"Q{i} {t['correct'] if ok else t['wrong']}")
                    if not ok:
                        print(f"  {t['your_pick']}: {q['choices'][p.value]}")
                    print(f"  {t['answer']}: {q['choices'][q['answer']]}")
                    print(f"  {t['why']}: {q['why']}")
                    print(f"  {t['ref']}: {q['ref']}\n")
                print(_verdict(lang, score, len(questions)))

        submit.on_click(on_submit)
        body.children = tuple(rows + [submit, out])

    start.on_click(render)
    display(w.VBox([header, start, body]))


def run_cli(lang: str) -> int:
    t = UI[lang]
    questions = get_questions(lang)
    picks = []
    for i, q in enumerate(questions, start=1):
        print(f"\nQ{i} · {q['topic']}\n{q['prompt']}")
        for j, c in enumerate(q["choices"]):
            print(f"  {LETTERS[j]}. {c}")
        while True:
            raw = input(f"{LETTERS[: len(q['choices'])]}> ").strip().upper()
            if raw and raw[0] in LETTERS[: len(q["choices"])]:
                picks.append(LETTERS.index(raw[0]))
                break

    score = sum(p == q["answer"] for q, p in zip(questions, picks))
    print("\n" + t["score"].format(score=score, total=len(questions)) + "\n")
    for i, (q, p) in enumerate(zip(questions, picks), start=1):
        ok = p == q["answer"]
        print(f"Q{i} {t['correct'] if ok else t['wrong']}")
        if not ok:
            print(f"  {t['your_pick']}: {q['choices'][p]}")
        print(f"  {t['answer']}: {q['choices'][q['answer']]}")
        print(f"  {t['why']}: {q['why']}")
        print(f"  {t['ref']}: {q['ref']}\n")
    print(_verdict(lang, score, len(questions)))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="MicroDuck lesson quiz (5 questions)")
    parser.add_argument("--lang", choices=sorted(QUESTIONS), default="zh")
    parser.add_argument(
        "--list", action="store_true", help="print the questions instead of quizzing"
    )
    args = parser.parse_args()

    if args.list:
        for i, q in enumerate(get_questions(args.lang), start=1):
            print(f"{i}. [{q['topic']}] {q['prompt']}")
        return 0
    return run_cli(args.lang)


if __name__ == "__main__":
    raise SystemExit(main())
