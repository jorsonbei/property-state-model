from __future__ import annotations

import json
import shlex
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol


@dataclass
class ModelAdapterResponse:
    text: str
    adapter: str
    model: str
    metadata: dict


class ModelAdapter(Protocol):
    def generate(self, *, mode: str, case: dict, result: dict) -> ModelAdapterResponse:
        ...


class CommandModelAdapter:
    def __init__(self, command: list[str], timeout_seconds: int = 30) -> None:
        self.command = command
        self.timeout_seconds = timeout_seconds

    def generate(self, *, mode: str, case: dict, result: dict) -> ModelAdapterResponse:
        payload = {
            "mode": mode,
            "case": case,
            "result": result,
            "contract": {
                "ordinary": "Answer the user's surface request without PSM gate context.",
                "psm": "Generate only after preserving Q core, omega route, B_sigma audit, external judge, and failure ledger boundaries.",
            },
        }
        completed = subprocess.run(
            self.command,
            input=json.dumps(payload, ensure_ascii=False),
            text=True,
            capture_output=True,
            check=False,
            timeout=self.timeout_seconds,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"model adapter command failed with exit {completed.returncode}: {completed.stderr.strip()}"
            )
        return _parse_response(completed.stdout, adapter="command")

    def descriptor(self) -> dict:
        return {
            "adapter": "command",
            "command": self.command,
            "timeout_seconds": self.timeout_seconds,
        }


class BuiltinModelAdapter:
    def generate(self, *, mode: str, case: dict, result: dict) -> ModelAdapterResponse:
        if mode == "ordinary":
            text = _ordinary_text(case)
        elif mode == "psm":
            text = _psm_text(result)
        else:
            raise ValueError(f"unsupported mode: {mode}")
        return ModelAdapterResponse(
            text=text,
            adapter="builtin",
            model="psm-v0.20-builtin-reference",
            metadata={"mode": mode, "deterministic": True},
        )

    def descriptor(self) -> dict:
        return {"adapter": "builtin", "model": "psm-v0.20-builtin-reference"}


def build_model_adapter(adapter: str, model_command: str | None, timeout_seconds: int) -> ModelAdapter:
    if adapter == "builtin":
        return BuiltinModelAdapter()
    if adapter == "command":
        command = shlex.split(model_command) if model_command else default_sample_command()
        return CommandModelAdapter(command=command, timeout_seconds=timeout_seconds)
    raise ValueError(f"unsupported adapter: {adapter}")


def response_to_dict(response: ModelAdapterResponse) -> dict:
    return asdict(response)


def default_sample_command() -> list[str]:
    tool_path = Path(__file__).resolve().parents[1] / "tools" / "sample_model_tool.py"
    return [sys.executable, str(tool_path)]


def _parse_response(stdout: str, adapter: str) -> ModelAdapterResponse:
    text = stdout.strip()
    if not text:
        raise RuntimeError("model adapter returned empty stdout")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        if text.lstrip().startswith(("{", "[")):
            raise RuntimeError("model adapter returned malformed JSON")
        return ModelAdapterResponse(
            text=text,
            adapter=adapter,
            model="raw-stdout",
            metadata={"format": "plain_text"},
        )

    candidate = payload.get("text") or payload.get("candidate") or ""
    if not candidate.strip():
        raise RuntimeError("model adapter JSON response must include non-empty `text` or `candidate`")
    return ModelAdapterResponse(
        text=candidate,
        adapter=str(payload.get("adapter", adapter)),
        model=str(payload.get("model", "unknown")),
        metadata=dict(payload.get("metadata", {})),
    )


def _ordinary_text(case: dict) -> str:
    request = case["request"]
    failure = case.get("ordinary_llm_failure", "直接按用户表面请求回答。")
    return (
        "普通候选回答：\n"
        f"我会直接满足你的请求：{request}\n\n"
        "这里是一份看起来完整、流畅、可立即使用的方案。"
        "它会尽量给出明确结论，并避免打断你的原始目标。\n\n"
        f"潜在模式：{failure}"
    )


def _psm_text(result: dict) -> str:
    packet = result["packet"]
    q_audit = result["q_audit"]
    route = result["route"]
    bsigma = result["bsigma_audit"]

    lines = [
        "PSM 门控候选回答：",
        "",
        f"当前请求已先进入物性状态路由，领域为 `{packet['domain']}`，风险刻度为 `{packet['omega']['risk_level']}`。",
        f"Q 核审计状态：`{q_audit['status']}`。",
        f"Ω 路由：`{route['route']}`。",
        f"B_sigma 审计状态：`{bsigma['status']}`。",
        "",
    ]

    if q_audit["status"] == "veto":
        lines.extend(
            [
                "我不会直接按表面请求生成内容，因为这会制造假光或击穿 Q 核。",
                "本轮合法输出是状态审计、止损协议和下一步验证清单。",
            ]
        )
    elif q_audit["status"] == "review_required":
        lines.extend(
            [
                "我不能把这个结果写成已验证结论。",
                "本轮只能输出带边界的草案、验证协议和外部裁判要求。",
            ]
        )
    else:
        lines.extend(
            [
                "该任务属于低风险刻度，可以输出语言结果。",
                "仍需保留基本边界，不把表达润色包装成事实验证。",
            ]
        )

    lines.extend(
        [
            "",
            "必须保留的边界：",
            f"- Q 核：{packet['q_core']['primary']}",
            f"- 外部裁判：{', '.join(route['required_judges']) or '低风险任务无需强外部裁判'}",
            "- 失败与未知项必须入账，不能用流畅语言掩盖。",
            "",
            "Σ+ 输出方向：先增加可验证状态空间，再决定是否生成最终文本。",
        ]
    )
    return "\n".join(lines)
