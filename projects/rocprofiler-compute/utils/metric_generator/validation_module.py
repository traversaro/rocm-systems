"""
Validation and Consistency Module for Metric Generator
Handles dual-input validation and conflict detection
"""

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml

# Add parent directory to path for log_usage import
sys.path.append(str(Path(__file__).parent.parent))


@dataclass
class ValidationError:
    error_type: str
    message: str
    file_path: Optional[Path] = None
    details: Optional[dict] = None


@dataclass
class ConsistencyResult:
    is_consistent: bool
    errors: list[ValidationError]
    warnings: list[str]


class DualInputValidator:
    """Validates consistency between split YAMLs and validation files"""

    def __init__(self, root_dir: Path):
        self.root_dir = Path(root_dir)
        self.split_yaml_dir = (
            self.root_dir / "src" / "rocprof_compute_soc" / "analysis_configs"
        )
        self.validation_dir = (
            self.root_dir / "utils" / "metric_generator" / "validation"
        )

    def load_split_yaml_data(self) -> dict[str, dict]:
        """Load all split YAML files into memory"""
        data = {}

        for arch_dir in self.split_yaml_dir.iterdir():
            if not arch_dir.is_dir() or not arch_dir.name.startswith("gfx"):
                continue

            arch_name = arch_dir.name
            data[arch_name] = {}

            for yaml_file in arch_dir.glob("*.yaml"):
                try:
                    with open(yaml_file) as f:
                        file_data = yaml.safe_load(f)
                        # Extract panel ID from filename (e.g., "1000_compute_units_instruction_mix.yaml")
                        panel_id = yaml_file.stem.split("_")[0]
                        data[arch_name][panel_id] = file_data
                except Exception as e:
                    print(f"Failed to load {yaml_file}: {e}")

        return data

    def load_validation_files(self) -> dict[str, Any]:
        """Load all validation files"""
        validation_files = [
            "metric_templates.yaml",
            "arch_specs.yaml",
            "panel_definitions.yaml",
            "metric_descriptions.yaml",
        ]

        data = {}
        for filename in validation_files:
            filepath = self.validation_dir / filename
            if filepath.exists():
                try:
                    with open(filepath) as f:
                        data[filename.replace(".yaml", "")] = yaml.safe_load(f)
                except Exception as e:
                    print(f"Failed to load {filepath}: {e}")
                    data[filename.replace(".yaml", "")] = {}
            else:
                data[filename.replace(".yaml", "")] = {}

        return data

    def extract_metrics_from_split_yamls(
        self, split_data: dict[str, dict]
    ) -> dict[str, set[str]]:
        """Extract metric names per architecture from split YAMLs"""
        arch_metrics = {}

        for arch_name, panels in split_data.items():
            metrics = set()
            for panel_id, panel_data in panels.items():
                if "Panel Config" in panel_data:
                    # Extract from data sources
                    for data_source in panel_data["Panel Config"].get(
                        "data source", []
                    ):
                        if "metric_table" in data_source:
                            metric_table = data_source["metric_table"]
                            if "metric" in metric_table:
                                metrics.update(metric_table["metric"].keys())
            arch_metrics[arch_name] = metrics

        return arch_metrics

    def extract_metrics_from_validation(
        self, validation_data: dict
    ) -> dict[str, set[str]]:
        """Extract metric names per architecture from validation files"""
        arch_metrics = {}

        # From arch_specs - get supported metrics per architecture
        arch_specs = validation_data.get("arch_specs", {})
        if "architectures" in arch_specs:
            for arch_name, arch_config in arch_specs["architectures"].items():
                metrics = set(arch_config.get("supported_metrics", []))
                arch_metrics[arch_name] = metrics

        return arch_metrics

    def validate_metric_consistency(
        self, split_data: dict, validation_data: dict
    ) -> ConsistencyResult:
        """Validate that split YAMLs and validation files have consistent metric definitions"""
        errors = []
        warnings = []

        # Extract metrics from both sources
        split_metrics = self.extract_metrics_from_split_yamls(split_data)
        validation_metrics = self.extract_metrics_from_validation(validation_data)

        # Compare architectures
        split_archs = set(split_metrics.keys())
        validation_archs = set(validation_metrics.keys())

        # Check for missing architectures
        missing_in_validation = split_archs - validation_archs
        missing_in_split = validation_archs - split_archs

        if missing_in_validation:
            errors.append(
                ValidationError(
                    error_type="missing_architecture",
                    message=f"Architectures in split YAMLs but not in validation: {missing_in_validation}",
                )
            )

        if missing_in_split:
            warnings.append(
                f"Architectures in validation but not in split YAMLs: {missing_in_split}"
            )

        # Check metric consistency for common architectures
        common_archs = split_archs & validation_archs
        for arch in common_archs:
            split_arch_metrics = split_metrics[arch]
            validation_arch_metrics = validation_metrics[arch]

            # Check for metric mismatches
            extra_in_split = split_arch_metrics - validation_arch_metrics
            extra_in_validation = validation_arch_metrics - split_arch_metrics

            if extra_in_split:
                errors.append(
                    ValidationError(
                        error_type="metric_mismatch",
                        message=f"Architecture {arch}: metrics in split YAMLs but not validation: {extra_in_split}",
                        details={
                            "architecture": arch,
                            "extra_metrics": list(extra_in_split),
                        },
                    )
                )

            if extra_in_validation:
                errors.append(
                    ValidationError(
                        error_type="metric_mismatch",
                        message=f"Architecture {arch}: metrics in validation but not split YAMLs: {extra_in_validation}",
                        details={
                            "architecture": arch,
                            "missing_metrics": list(extra_in_validation),
                        },
                    )
                )

        return ConsistencyResult(
            is_consistent=len(errors) == 0, errors=errors, warnings=warnings
        )

    def validate_formula_consistency(
        self, split_data: dict, validation_data: dict
    ) -> ConsistencyResult:
        """Validate that metric formulas are consistent between sources"""
        errors = []
        warnings = []

        # Extract formulas from metric_templates
        metric_templates = validation_data.get("metric_templates", {})
        template_formulas = {}
        if "metrics" in metric_templates:
            for metric_name, template in metric_templates["metrics"].items():
                template_formulas[metric_name] = template.get("formula", "")

        # Extract formulas from split YAMLs
        split_formulas = {}
        for arch_name, panels in split_data.items():
            for panel_id, panel_data in panels.items():
                if "Panel Config" in panel_data:
                    for data_source in panel_data["Panel Config"].get(
                        "data source", []
                    ):
                        if "metric_table" in data_source:
                            metric_table = data_source["metric_table"]
                            if "metric" in metric_table:
                                for metric_name, metric_data in metric_table[
                                    "metric"
                                ].items():
                                    if (
                                        isinstance(metric_data, dict)
                                        and "avg" in metric_data
                                    ):
                                        key = f"{arch_name}:{metric_name}"
                                        split_formulas[key] = metric_data["avg"]

        # Compare formulas (this is complex due to architecture variations)
        # For now, just check if templates exist for metrics found in split YAMLs
        for formula_key, formula in split_formulas.items():
            arch, metric_name = formula_key.split(":", 1)

            if metric_name not in template_formulas:
                warnings.append(
                    f"Metric '{metric_name}' in {arch} has no template definition"
                )

        return ConsistencyResult(
            is_consistent=len(errors) == 0, errors=errors, warnings=warnings
        )

    def validate_deltas_match(
        self, split_changes: list, validation_changes: list
    ) -> ConsistencyResult:
        """Main validation function for when both input sources have changes"""
        print(
            "Validating consistency between split YAML and validation file changes..."
        )

        # Load current data
        split_data = self.load_split_yaml_data()
        validation_data = self.load_validation_files()

        all_errors = []
        all_warnings = []

        # Run metric consistency validation
        metric_result = self.validate_metric_consistency(split_data, validation_data)
        all_errors.extend(metric_result.errors)
        all_warnings.extend(metric_result.warnings)

        # Run formula consistency validation
        formula_result = self.validate_formula_consistency(split_data, validation_data)
        all_errors.extend(formula_result.errors)
        all_warnings.extend(formula_result.warnings)

        # Log results
        if all_errors:
            print("Consistency validation failed:")
            for error in all_errors:
                print(f"  {error.error_type}: {error.message}")

        if all_warnings:
            print("Consistency validation warnings:")
            for warning in all_warnings:
                print(f"  {warning}")

        if not all_errors:
            print("Consistency validation passed")

        return ConsistencyResult(
            is_consistent=len(all_errors) == 0, errors=all_errors, warnings=all_warnings
        )


class SchemaValidator:
    """Validates individual files against expected schemas"""

    def __init__(self):
        pass

    def validate_split_yaml_schema(self, filepath: Path) -> list[ValidationError]:
        """Validate split YAML file structure"""
        errors = []

        try:
            with open(filepath) as f:
                data = yaml.safe_load(f)

            # Check required top-level structure
            if "Panel Config" not in data:
                errors.append(
                    ValidationError(
                        error_type="schema_error",
                        message="Missing 'Panel Config' section",
                        file_path=filepath,
                    )
                )
                return errors

            panel_config = data["Panel Config"]

            # Check required fields
            required_fields = ["id", "title", "data source"]
            for field in required_fields:
                if field not in panel_config:
                    errors.append(
                        ValidationError(
                            error_type="schema_error",
                            message=f"Missing required field: {field}",
                            file_path=filepath,
                        )
                    )

            # Validate data sources
            if "data source" in panel_config:
                for i, data_source in enumerate(panel_config["data source"]):
                    if "metric_table" in data_source:
                        metric_table = data_source["metric_table"]
                        if "metric" not in metric_table:
                            errors.append(
                                ValidationError(
                                    error_type="schema_error",
                                    message=f"Data source {i}: metric_table missing 'metric' field",
                                    file_path=filepath,
                                )
                            )

        except yaml.YAMLError as e:
            errors.append(
                ValidationError(
                    error_type="yaml_error",
                    message=f"Invalid YAML: {e}",
                    file_path=filepath,
                )
            )
        except Exception as e:
            errors.append(
                ValidationError(
                    error_type="file_error",
                    message=f"Error reading file: {e}",
                    file_path=filepath,
                )
            )

        return errors

    def validate_validation_file_schema(
        self, filepath: Path, file_type: str
    ) -> list[ValidationError]:
        """Validate validation file structure based on type"""
        errors = []

        try:
            with open(filepath) as f:
                data = yaml.safe_load(f)

            if file_type == "metric_templates":
                if "metrics" not in data:
                    errors.append(
                        ValidationError(
                            error_type="schema_error",
                            message="Missing 'metrics' section",
                            file_path=filepath,
                        )
                    )

            elif file_type == "arch_specs":
                if "architectures" not in data:
                    errors.append(
                        ValidationError(
                            error_type="schema_error",
                            message="Missing 'architectures' section",
                            file_path=filepath,
                        )
                    )

            # Add more validation rules as needed

        except yaml.YAMLError as e:
            errors.append(
                ValidationError(
                    error_type="yaml_error",
                    message=f"Invalid YAML: {e}",
                    file_path=filepath,
                )
            )
        except Exception as e:
            errors.append(
                ValidationError(
                    error_type="file_error",
                    message=f"Error reading file: {e}",
                    file_path=filepath,
                )
            )

        return errors
