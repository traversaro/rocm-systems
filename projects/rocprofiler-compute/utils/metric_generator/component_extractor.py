"""
Component Extraction Module
Extracts and normalizes components from split YAML files to generate validation files
"""

import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml

# Add parent directory to path for log_usage import
sys.path.append(str(Path(__file__).parent.parent))


@dataclass
class MetricDefinition:
    name: str
    formula: str
    unit: str
    peak: Optional[str] = None
    supported_archs: set[str] = None
    arch_overrides: dict[str, dict] = None

    def __post_init__(self):
        if self.supported_archs is None:
            self.supported_archs = set()
        if self.arch_overrides is None:
            self.arch_overrides = {}


@dataclass
class PanelDefinition:
    id: int
    title: str
    data_sources: list[dict]
    metrics_used: set[str]


@dataclass
class ArchitectureSpec:
    name: str
    supported_metrics: set[str]
    metric_overrides: dict[str, dict]
    parameters: dict[str, str]


class ComponentExtractor:
    """Extracts normalized components from split YAML files"""

    def __init__(self, root_dir: Path):
        self.root_dir = Path(root_dir)
        self.split_yaml_dir = (
            self.root_dir / "src" / "rocprof_compute_soc" / "analysis_configs"
        )
        self.validation_dir = (
            self.root_dir / "utils" / "metric_generator" / "validation"
        )

        # Known architectures - will be updated by discovery
        self.architectures = [
            "gfx908",
            "gfx90a",
            "gfx940",
            "gfx941",
            "gfx942",
            "gfx950",
        ]

    def load_all_split_yamls(self) -> dict[str, dict[str, dict]]:
        """Load all split YAML files organized by architecture and panel"""
        data = {}

        for arch_dir in self.split_yaml_dir.iterdir():
            if not arch_dir.is_dir() or not arch_dir.name.startswith("gfx"):
                continue

            arch_name = arch_dir.name
            data[arch_name] = {}
            print(f"Loading split YAMLs for {arch_name}")

            for yaml_file in arch_dir.glob("*.yaml"):
                try:
                    with open(yaml_file) as f:
                        file_data = yaml.safe_load(f)

                    # Extract panel ID from filename
                    panel_id = yaml_file.stem.split("_")[0]
                    data[arch_name][panel_id] = file_data
                    print(f"  Loaded panel {panel_id}")

                except Exception as e:
                    print(f"Failed to load {yaml_file}: {e}")

        return data

    def extract_metric_definitions(
        self, split_data: dict[str, dict[str, dict]]
    ) -> dict[str, MetricDefinition]:
        """Extract and deduplicate metric definitions from split YAMLs"""
        print("Extracting metric definitions...")

        # Collect all metric instances
        metric_instances = defaultdict(list)

        for arch_name, panels in split_data.items():
            for panel_id, panel_data in panels.items():
                if "Panel Config" not in panel_data:
                    continue

                panel_config = panel_data["Panel Config"]

                # Extract from data sources
                for data_source in panel_config.get("data source", []):
                    if "metric_table" in data_source:
                        metric_table = data_source["metric_table"]
                        if "metric" in metric_table:
                            for metric_name, metric_data in metric_table[
                                "metric"
                            ].items():
                                if isinstance(metric_data, dict):
                                    metric_instances[metric_name].append({
                                        "arch": arch_name,
                                        "panel": panel_id,
                                        "data": metric_data,
                                        "unit": metric_data.get("unit", ""),
                                    })

        # Deduplicate and create normalized definitions
        metric_definitions = {}

        for metric_name, instances in metric_instances.items():
            print(f"Processing metric: {metric_name}")

            # Find the most common formula (this will be the base)
            formula_counts = defaultdict(int)
            unit_counts = defaultdict(int)
            peak_counts = defaultdict(int)

            for instance in instances:
                data = instance["data"]

                # Count formulas (using 'avg' as the primary formula)
                if "avg" in data:
                    formula_counts[data["avg"]] += 1
                elif "value" in data:
                    formula_counts[data["value"]] += 1

                # Count units
                if "unit" in data:
                    unit_counts[data["unit"]] += 1

                # Count peak formulas
                if "peak" in data:
                    peak_counts[data["peak"]] += 1

            # Get most common values
            most_common_formula = (
                max(formula_counts, key=formula_counts.get) if formula_counts else ""
            )
            most_common_unit = (
                max(unit_counts, key=unit_counts.get) if unit_counts else ""
            )
            most_common_peak = (
                max(peak_counts, key=peak_counts.get) if peak_counts else None
            )

            # Determine supported architectures and overrides
            supported_archs = set()
            arch_overrides = {}

            for instance in instances:
                arch = instance["arch"]
                data = instance["data"]

                # Check if this instance uses the common formula
                instance_formula = data.get("avg") or data.get("value", "")

                if instance_formula == most_common_formula:
                    supported_archs.add(arch)
                elif instance_formula in [None, "None", ""]:
                    # This architecture doesn't support this metric
                    arch_overrides[arch] = {"value": None, "pop": None}
                else:
                    # This architecture has a different formula
                    supported_archs.add(arch)
                    arch_overrides[arch] = {
                        "value": instance_formula,
                        "unit": data.get("unit", most_common_unit),
                    }
                    if "peak" in data and data["peak"] != most_common_peak:
                        arch_overrides[arch]["peak"] = data["peak"]

            metric_definitions[metric_name] = MetricDefinition(
                name=metric_name,
                formula=most_common_formula,
                unit=most_common_unit,
                peak=most_common_peak,
                supported_archs=supported_archs,
                arch_overrides=arch_overrides,
            )

        print(f"Extracted {len(metric_definitions)} unique metrics")
        return metric_definitions

    def extract_architecture_specs(
        self,
        split_data: dict[str, dict[str, dict]],
        metric_definitions: dict[str, MetricDefinition],
    ) -> dict[str, ArchitectureSpec]:
        """Extract architecture specifications"""
        print("Extracting architecture specifications...")

        arch_specs = {}

        for arch_name in split_data.keys():
            print(f"Processing architecture: {arch_name}")

            # Determine supported metrics for this architecture
            supported_metrics = set()
            metric_overrides = {}

            for metric_name, metric_def in metric_definitions.items():
                if arch_name in metric_def.supported_archs:
                    supported_metrics.add(metric_name)

                if arch_name in metric_def.arch_overrides:
                    metric_overrides[metric_name] = metric_def.arch_overrides[arch_name]

            # Extract common parameters (these would be variables like $max_sclk)
            parameters = self._extract_architecture_parameters(
                arch_name, split_data[arch_name]
            )

            arch_specs[arch_name] = ArchitectureSpec(
                name=arch_name,
                supported_metrics=supported_metrics,
                metric_overrides=metric_overrides,
                parameters=parameters,
            )

        print(f"Extracted specifications for {len(arch_specs)} architectures")
        return arch_specs

    def _extract_architecture_parameters(
        self, arch_name: str, panel_data: dict
    ) -> dict[str, str]:
        """Extract architecture-specific parameters from formulas"""
        # Look for variables like $max_sclk, $cu_per_gpu in formulas
        parameters = {}

        # Common parameters we expect to find
        common_params = {
            "max_sclk": "$max_sclk",
            "cu_per_gpu": "$cu_per_gpu",
            "l2_banks": "$l2_banks",
            "memory_channels": "$memory_channels",
        }

        # For now, just return the common parameters
        # In a more sophisticated implementation, we'd parse formulas to find variables
        return common_params

    def extract_panel_definitions(
        self, split_data: dict[str, dict[str, dict]]
    ) -> dict[str, PanelDefinition]:
        """Extract panel structure definitions"""
        print("Extracting panel definitions...")

        panel_definitions = {}

        # Use the first architecture as the template (panels should be consistent)
        template_arch = next(iter(split_data.keys()))
        template_data = split_data[template_arch]

        for panel_id, panel_data in template_data.items():
            if "Panel Config" not in panel_data:
                continue

            panel_config = panel_data["Panel Config"]

            # Extract basic panel info
            panel_def = PanelDefinition(
                id=panel_config.get("id", int(panel_id)),
                title=panel_config.get("title", ""),
                data_sources=panel_config.get("data source", []),
                metrics_used=set(),
            )

            # Collect metrics used in this panel
            for data_source in panel_def.data_sources:
                if "metric_table" in data_source:
                    metric_table = data_source["metric_table"]
                    if "metric" in metric_table:
                        panel_def.metrics_used.update(metric_table["metric"].keys())

            panel_definitions[panel_id] = panel_def

        print(f"Extracted {len(panel_definitions)} panel definitions")
        return panel_definitions

    def extract_metric_descriptions(
        self, split_data: dict[str, dict[str, dict]]
    ) -> dict[str, dict[str, str]]:
        """Extract metric descriptions from split YAMLs"""
        print("Extracting metric descriptions...")

        descriptions = {}

        # Collect descriptions from all files (they should be consistent)
        for arch_name, panels in split_data.items():
            for panel_id, panel_data in panels.items():
                if "Panel Config" not in panel_data:
                    continue

                panel_config = panel_data["Panel Config"]
                metrics_description = panel_config.get("metrics_description", {})

                for metric_name, description in metrics_description.items():
                    if metric_name not in descriptions:
                        if isinstance(description, str):
                            # Simple string description
                            descriptions[metric_name] = {
                                "plain": description,
                                "rst": description,  # Could be enhanced
                                "unit": "",  # Would need to be extracted separately
                            }
                        elif isinstance(description, dict):
                            # Already structured description
                            descriptions[metric_name] = description

        print(f"Extracted descriptions for {len(descriptions)} metrics")
        return descriptions

    def extract_all_components(self) -> tuple[dict, dict, dict, dict]:
        """Extract all components and return them"""
        print("=== Starting Component Extraction ===")

        # Load all split YAML files
        split_data = self.load_all_split_yamls()

        if not split_data:
            print("No split YAML data found")
            return {}, {}, {}, {}

        # Extract each component type
        metric_definitions = self.extract_metric_definitions(split_data)
        arch_specs = self.extract_architecture_specs(split_data, metric_definitions)
        panel_definitions = self.extract_panel_definitions(split_data)
        metric_descriptions = self.extract_metric_descriptions(split_data)

        print("=== Component Extraction Complete ===")

        return metric_definitions, arch_specs, panel_definitions, metric_descriptions
