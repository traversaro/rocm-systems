"""
Main Generator Controller
Implements the dual-input detection and generation logic
"""

import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path for log_usage import
sys.path.append(str(Path(__file__).parent.parent))

# Import our new modules
from detection_module import ChangeDetector, ChangeType
from validation_module import DualInputValidator


class MetricGeneratorController:
    """Main controller implementing the dual-input generation logic"""

    def __init__(self, root_dir: Optional[Path] = None):
        if root_dir is None:
            # Get root directory of the project (assumes script is in utils/)
            self.root_dir = Path(__file__).parent.parent
        else:
            self.root_dir = Path(root_dir)

        self.detector = ChangeDetector(self.root_dir)
        self.validator = DualInputValidator(self.root_dir)

    def run_generator(self) -> bool:
        """
        Main entry point implementing the dual-input logic:

        1. Check for both validation files Δ AND final split YAML Δ
           - Yes → Validate deltas match → Trigger generator
           - No → Continue
        2. Check for final split YAML Δ only
           - Yes → Trigger generator
           - No → Continue
        3. Check for validation files Δ only
           - Yes → Trigger generator
           - No → Exit (no work needed)

        Returns:
            bool: True if generation was triggered, False if no work needed
        """
        print("=== Metric Generator Controller Starting ===")

        try:
            # Phase 1: Detection
            detection_result = self.detector.detect_changes()

            # Phase 2: Decision Logic
            if detection_result.change_type == ChangeType.NO_CHANGES:
                print("No changes detected. Exiting.")
                return False

            elif detection_result.change_type == ChangeType.BOTH_CHANGED:
                print("Changes detected in both split YAMLs and validation files")
                return self._handle_both_changed(detection_result)

            elif detection_result.change_type == ChangeType.SPLIT_YAML_ONLY:
                print("Changes detected in split YAMLs only")
                return self._handle_split_yaml_only(detection_result)

            elif detection_result.change_type == ChangeType.VALIDATION_ONLY:
                print("Changes detected in validation files only")
                return self._handle_validation_only(detection_result)

            else:
                print(f"Unknown change type: {detection_result.change_type}")
                return False

        except Exception as e:
            print(f"Generator controller failed: {e}")
            return False

    def _handle_both_changed(self, detection_result) -> bool:
        """Handle case where both split YAMLs and validation files changed"""
        print(
            "Validating consistency between split YAML and validation file changes..."
        )

        # Validate that the deltas are consistent
        consistency_result = self.validator.validate_deltas_match(
            detection_result.split_yaml_changes,
            detection_result.validation_file_changes,
        )

        if consistency_result.is_consistent:
            print("Delta validation passed. Triggering generator.")
            return self._trigger_generator("both_changed")
        else:
            print("Delta validation failed. Manual resolution required.")
            print("Conflicts detected:")
            for error in consistency_result.errors:
                print(f"  - {error.message}")

            print("Please resolve conflicts manually and run generator again.")
            return False

    def _handle_split_yaml_only(self, detection_result) -> bool:
        """Handle case where only split YAMLs changed (standard workflow)"""
        print("Processing split YAML changes (standard workflow)")

        # Optional: Validate split YAML files before proceeding
        if self._validate_split_yamls(detection_result.split_yaml_changes):
            return self._trigger_generator("split_yaml_only")
        else:
            print("Split YAML validation failed. Fix errors and try again.")
            return False

    def _handle_validation_only(self, detection_result) -> bool:
        """Handle case where only validation files changed"""
        print("Processing validation file changes (validation-driven workflow)")

        # Optional: Validate validation files before proceeding
        if self._validate_validation_files(detection_result.validation_file_changes):
            return self._trigger_generator("validation_only")
        else:
            print("Validation file validation failed. Fix errors and try again.")
            return False

    def _validate_split_yamls(self, changes) -> bool:
        """Validate split YAML files for basic schema compliance"""
        # For now, just return True. Can be enhanced with schema validation
        print(f"Validating {len(changes)} split YAML changes...")
        return True

    def _validate_validation_files(self, changes) -> bool:
        """Validate validation files for basic schema compliance"""
        # For now, just return True. Can be enhanced with schema validation
        print(f"Validating {len(changes)} validation file changes...")
        return True

    def _trigger_generator(self, trigger_source: str) -> bool:
        """Trigger the actual generation process"""
        print(f"=== Triggering Generator (source: {trigger_source}) ===")

        try:
            # Import our generation modules
            from component_extractor import ComponentExtractor
            from validation_generator import (
                UnifiedConfigGenerator,
                ValidationFileGenerator,
            )

            # Step 1: Extract components from input files
            print("Step 1: Extracting components from split YAML files...")
            extractor = ComponentExtractor(self.root_dir)
            metric_definitions, arch_specs, panel_definitions, metric_descriptions = (
                extractor.extract_all_components()
            )

            if not metric_definitions:
                print("No metric definitions extracted. Cannot proceed.")
                return False

            # Step 2: Generate validation files
            print("Step 2: Generating validation files...")
            validation_generator = ValidationFileGenerator(self.root_dir)
            validation_generator.generate_all_validation_files(
                metric_definitions, arch_specs, panel_definitions, metric_descriptions
            )

            # Step 3: Generate unified config (for validation purposes)
            print("Step 3: Generating unified config for validation...")
            unified_generator = UnifiedConfigGenerator(self.root_dir)
            unified_generator.generate_unified_config()

            # Step 4: Run existing split_config.py logic
            print("Step 4: Running existing split_config.py logic...")
            self._run_split_config()

            print("=== Generator Completed Successfully ===")
            return True

        except Exception as e:
            print(f"Generation failed: {e}")
            return False

    def _run_split_config(self):
        """Run the existing split_config.py logic"""
        try:
            # Import and run the existing split config functionality
            import sys
            from pathlib import Path

            # Add the utils directory to path so we can import current_split_config
            utils_dir = self.root_dir / "utils"
            if str(utils_dir) not in sys.path:
                sys.path.insert(0, str(utils_dir))

            # Import and run the existing functions
            from current_split_config import (
                update_analysis_config,
                update_documentation,
                update_hash,
                update_sets_config,
            )

            print("Running existing split_config functions...")

            # Run the existing pipeline
            update_analysis_config()
            print("  ✓ Analysis config updated")

            update_sets_config()
            print("  ✓ sets config updated")

            update_documentation()
            print("  ✓ Documentation updated")

            update_hash()
            print("  ✓ Hash files updated")

        except ImportError as e:
            print(f"Failed to import existing split_config: {e}")
            print("Make sure current_split_config.py is available in utils/")
            raise
        except Exception as e:
            print(f"Failed to run existing split_config logic: {e}")
            raise

    def discover_new_architectures(self):
        """Discover any new architectures and report them"""
        new_archs = self.detector.discover_new_architectures()
        if new_archs:
            print(f"New architectures discovered: {', '.join(new_archs)}")
            print("Consider updating the architecture list in the controller.")
        return new_archs


def main():
    """Main entry point for the generator"""
    import argparse

    parser = argparse.ArgumentParser(
        description="ROCm Metric Generator with Dual-Input Support"
    )
    parser.add_argument("--root-dir", type=Path, help="Root directory of the project")
    parser.add_argument(
        "--discover-archs", action="store_true", help="Discover new architectures only"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force generation even if no changes detected",
    )

    args = parser.parse_args()

    controller = MetricGeneratorController(args.root_dir)

    if args.discover_archs:
        controller.discover_new_architectures()
        return

    if args.force:
        print("Force mode: Triggering generation regardless of changes")
        success = controller._trigger_generator("force")
    else:
        success = controller.run_generator()

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
