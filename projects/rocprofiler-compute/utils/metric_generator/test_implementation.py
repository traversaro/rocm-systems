#!/usr/bin/env python3
"""
Test Implementation Script
Tests the new metric generator implementation
"""

import sys
from pathlib import Path

# Add parent directory to path for log_usage import
sys.path.append(str(Path(__file__).parent.parent))


def test_detection_module():
    """Test the change detection functionality"""
    print("=== Testing Change Detection ===")

    try:
        from detection_module import ChangeDetector

        # Assume we're running from the project root
        root_dir = Path.cwd()
        detector = ChangeDetector(root_dir)

        # Test detection
        result = detector.detect_changes()
        print(f"Detection result: {result.change_type}")
        print(f"Split YAML changes: {len(result.split_yaml_changes)}")
        print(f"Validation changes: {len(result.validation_file_changes)}")

        # Test architecture discovery
        new_archs = detector.discover_new_architectures()
        if new_archs:
            print(f"New architectures found: {new_archs}")
        else:
            print("No new architectures discovered")

        return True

    except Exception as e:
        print(f"Detection module test failed: {e}")
        return False


def test_component_extraction():
    """Test the component extraction functionality"""
    print("=== Testing Component Extraction ===")

    try:
        from component_extractor import ComponentExtractor

        root_dir = Path(__file__).parent.parent.parent
        extractor = ComponentExtractor(root_dir)

        # Test loading split YAMLs
        split_data = extractor.load_all_split_yamls()
        print(f"Loaded split data for {len(split_data)} architectures")

        for arch, panels in split_data.items():
            print(f"  {arch}: {len(panels)} panels")

        # Test component extraction
        metric_definitions, arch_specs, panel_definitions, metric_descriptions = (
            extractor.extract_all_components()
        )

        print(f"Extracted {len(metric_definitions)} metric definitions")
        print(f"Extracted {len(arch_specs)} architecture specs")
        print(f"Extracted {len(panel_definitions)} panel definitions")
        print(f"Extracted {len(metric_descriptions)} metric descriptions")

        # Sample some results
        if metric_definitions:
            sample_metric = next(iter(metric_definitions.keys()))
            sample_def = metric_definitions[sample_metric]
            print(f"Sample metric '{sample_metric}':")
            print(f"  Formula: {sample_def.formula[:50]}...")
            print(f"  Unit: {sample_def.unit}")
            print(f"  Supported archs: {sample_def.supported_archs}")

        return True

    except Exception as e:
        print(f"Component extraction test failed: {e}")
        return False


def test_validation_generation():
    """Test the validation file generation"""
    print("=== Testing Validation File Generation ===")

    try:
        from component_extractor import ComponentExtractor
        from validation_generator import (
            UnifiedConfigGenerator,
            ValidationFileGenerator,
        )

        root_dir = Path(__file__).parent.parent.parent

        # Extract components
        extractor = ComponentExtractor(root_dir)
        metric_definitions, arch_specs, panel_definitions, metric_descriptions = (
            extractor.extract_all_components()
        )

        if not metric_definitions:
            print("No components extracted, skipping validation generation test")
            return True

        # Generate validation files
        generator = ValidationFileGenerator(root_dir)
        generator.generate_all_validation_files(
            metric_definitions, arch_specs, panel_definitions, metric_descriptions
        )

        # Check if files were created
        validation_dir = root_dir / "utils" / "metric_generator" / "validation"
        expected_files = [
            "metric_templates.yaml",
            "arch_specs.yaml",
            "panel_definitions.yaml",
            "metric_descriptions.yaml",
        ]

        for filename in expected_files:
            filepath = validation_dir / filename
            if filepath.exists():
                print(f"  ✓ {filename} generated ({filepath.stat().st_size} bytes)")
            else:
                print(f"  ✗ {filename} not found")
                return False

        # Test unified config generation
        unified_generator = UnifiedConfigGenerator(root_dir)
        unified_generator.generate_unified_config()

        unified_path = root_dir / "utils" / "unified_config.yaml"
        if unified_path.exists():
            print(
                f"  ✓ unified_config.yaml generated ({unified_path.stat().st_size} bytes)"
            )
        else:
            print("  ✗ unified_config.yaml not found")
            return False

        return True

    except Exception as e:
        print(f"Validation generation test failed: {e}")
        return False


def test_main_controller():
    """Test the main controller"""
    print("=== Testing Main Controller ===")

    try:
        from main_controller import MetricGeneratorController

        root_dir = Path(__file__).parent.parent.parent
        controller = MetricGeneratorController(root_dir)

        # Test discovery
        new_archs = controller.discover_new_architectures()

        # Test dry-run (this will actually run the generator if changes are detected)
        print("About to run the full generator. This will modify files.")
        print("Continue? (y/n)")

        response = input().strip().lower()
        if response == "y":
            success = controller.run_generator()
            if success:
                print("  ✓ Generator completed successfully")
            else:
                print("  ✗ Generator failed")
            return success
        else:
            print("Skipped full generator test")
            return True

    except Exception as e:
        print(f"Main controller test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("Starting implementation tests...")

    tests = [
        ("Change Detection", test_detection_module),
        ("Component Extraction", test_component_extraction),
        ("Validation Generation", test_validation_generation),
        ("Main Controller", test_main_controller),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n{'=' * 50}")
        try:
            result = test_func()
            results.append((test_name, result))
            if result:
                print(f"✓ {test_name} PASSED")
            else:
                print(f"✗ {test_name} FAILED")
        except KeyboardInterrupt:
            print(f"Test {test_name} interrupted by user")
            results.append((test_name, False))
            break
        except Exception as e:
            print(f"✗ {test_name} CRASHED: {e}")
            results.append((test_name, False))

    # Summary
    print(f"\n{'=' * 50}")
    print("TEST SUMMARY:")
    passed = 0
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1

    print(f"\nOverall: {passed}/{len(results)} tests passed")

    if passed == len(results):
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
