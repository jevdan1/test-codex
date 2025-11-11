"""Configuration loaders for the portable crypto collector."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import yaml


@dataclass(slots=True)
class SourceEndpoint:
    path: str
    params: Dict[str, Any]
    defaults: Dict[str, Any]
    limit: int
    mapping: Dict[str, int | str]


@dataclass(slots=True)
class SourceDefinition:
    id: str
    name: str
    type: str
    base_url: str
    auth: Dict[str, Any]
    rate_limit: Dict[str, Any]
    retry_policy: Dict[str, Any]
    endpoints: Dict[str, SourceEndpoint]


@dataclass(slots=True)
class PipelineDefinition:
    source_id: str
    pair: str
    granularity: str


@dataclass(slots=True)
class IndicatorDefinition:
    name: str
    window_sec: int
    expression: str
    inputs: List[str]


@dataclass(slots=True)
class ConfigBundle:
    sources: Dict[str, SourceDefinition]
    pipelines: List[PipelineDefinition]
    pair_shortlist: List[str]
    indicators: List[IndicatorDefinition]


def _load_yaml(path: Path) -> Dict[str, Any] | List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _parse_sources(config: Iterable[Dict[str, Any]]) -> Dict[str, SourceDefinition]:
    sources: Dict[str, SourceDefinition] = {}
    for entry in config:
        endpoints = {
            endpoint_id: SourceEndpoint(
                path=endpoint_cfg["path"],
                params=endpoint_cfg.get("params", {}),
                defaults=endpoint_cfg.get("defaults", {}),
                limit=int(endpoint_cfg.get("limit", 1000)),
                mapping=endpoint_cfg.get("mapping", {}),
            )
            for endpoint_id, endpoint_cfg in entry.get("endpoints", {}).items()
        }
        definition = SourceDefinition(
            id=entry["id"],
            name=entry["name"],
            type=entry.get("type", "rest"),
            base_url=entry["base_url"],
            auth=entry.get("auth", {"type": "none"}),
            rate_limit=entry.get("rate_limit", {}),
            retry_policy=entry.get("retry_policy", {}),
            endpoints=endpoints,
        )
        sources[definition.id] = definition
    return sources


def _parse_pipelines(config: Any) -> tuple[List[PipelineDefinition], List[str]]:
    pipelines: List[PipelineDefinition] = []
    shortlist: List[str] = []

    if isinstance(config, dict):
        raw_shortlist = config.get("shortlist", [])
        shortlist = [str(item) for item in raw_shortlist]
        pipelines_block = config.get("pipelines", {})
        for _, entry in pipelines_block.items():
            source_id = entry.get("source")
            granularity = str(entry.get("granularity", "1s"))
            for pair in entry.get("pairs", []):
                pipelines.append(
                    PipelineDefinition(
                        source_id=str(source_id),
                        pair=str(pair),
                        granularity=granularity,
                    )
                )
    else:
        for entry in config or []:
            pipelines.append(
                PipelineDefinition(
                    source_id=entry["source_id"],
                    pair=entry["pair"],
                    granularity=str(entry.get("granularity", "1s")),
                )
            )

    if not shortlist:
        shortlist = sorted({pipeline.pair for pipeline in pipelines})

    return pipelines, shortlist


def _parse_indicators(config: Iterable[Dict[str, Any]]) -> List[IndicatorDefinition]:
    indicators: List[IndicatorDefinition] = []
    for entry in config:
        indicators.append(
            IndicatorDefinition(
                name=entry["name"],
                window_sec=int(entry["window_sec"]),
                expression=entry["expression"],
                inputs=list(entry.get("inputs", [])),
            )
        )
    return indicators


def load_config_bundle(config_dir: Path) -> ConfigBundle:
    sources_path = config_dir / "sources.yaml"
    pipelines_path = config_dir / "pipelines.yaml"
    indicators_path = config_dir / "indicators.yaml"

    sources_data = _load_yaml(sources_path) if sources_path.exists() else []
    pipelines_data = _load_yaml(pipelines_path) if pipelines_path.exists() else []
    indicators_data = _load_yaml(indicators_path) if indicators_path.exists() else []

    pipelines, shortlist = _parse_pipelines(pipelines_data or [])

    return ConfigBundle(
        sources=_parse_sources(sources_data or []),
        pipelines=pipelines,
        pair_shortlist=shortlist,
        indicators=_parse_indicators(indicators_data or []),
    )


def dump_manifest(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
