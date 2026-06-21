#!/usr/bin/env python3
"""
Test the OpenSplat loss parsing functionality.
"""

import json
import tempfile
from pathlib import Path
from src.opensplat_trainer import parse_opensplat_loss


def test_parse_opensplat_loss():
    """Test parsing of various loss log line formats."""

    test_cases = [
        # (input_line, expected_step, expected_loss)
        ("Step 10: 0.335803 (20%)", 10, 0.335803),
        ("Step 100: 0.12345 (50%)", 100, 0.12345),
        ("Step 1000: 0.0001 (75%)", 1000, 0.0001),
        ("Step 0: 1.5 (0%)", 0, 1.5),
        ("Step 500: 0.54321 (99%)", 500, 0.54321),
        ("Some text Step 250: 0.999 (60%) more text", 250, 0.999),
        ("Invalid line", None, None),
        ("Step 100: missing percentage", None, None),
        ("", None, None),
    ]

    print("\nTesting parse_opensplat_loss() function:")
    print("=" * 70)

    passed = 0
    failed = 0

    for line, expected_step, expected_loss in test_cases:
        result = parse_opensplat_loss(line)

        if expected_step is None:
            if result is None:
                print(f"✓ PASS: '{line[:40]}...' → None (as expected)")
                passed += 1
            else:
                print(f"✗ FAIL: '{line[:40]}...' → {result} (expected None)")
                failed += 1
        else:
            if result is None:
                print(
                    f"✗ FAIL: '{line[:40]}...' → None (expected ({expected_step}, {expected_loss}))"
                )
                failed += 1
            else:
                step, loss = result
                if step == expected_step and abs(loss - expected_loss) < 1e-6:
                    print(
                        f"✓ PASS: '{line[:40]}...' → ({step}, {loss:.6f})"
                    )
                    passed += 1
                else:
                    print(
                        f"✗ FAIL: '{line[:40]}...' → ({step}, {loss}) (expected ({expected_step}, {expected_loss}))"
                    )
                    failed += 1

    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed\n")

    return failed == 0


def test_jsonl_format():
    """Test JSONL format generation."""

    print("Testing JSONL format generation:")
    print("=" * 70)

    loss_records = [
        {"step": 0, "loss": 1.5, "timestamp": "2026-06-21T14:30:00"},
        {"step": 100, "loss": 0.89234, "timestamp": "2026-06-21T14:30:10"},
        {"step": 200, "loss": 0.45123, "timestamp": "2026-06-21T14:30:20"},
    ]

    # Write to temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        for record in loss_records:
            f.write(json.dumps(record) + "\n")
        temp_file = Path(f.name)

    # Read back and verify
    read_records = []
    with open(temp_file, "r") as f:
        for line in f:
            read_records.append(json.loads(line))

    temp_file.unlink()  # Clean up

    if len(read_records) == len(loss_records):
        print(f"✓ PASS: Wrote and read {len(read_records)} JSONL records")
        for i, record in enumerate(read_records):
            print(f"  Record {i}: step={record['step']}, loss={record['loss']:.5f}")
        print("=" * 70)
        return True
    else:
        print(
            f"✗ FAIL: Expected {len(loss_records)} records, got {len(read_records)}"
        )
        return False


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("OpenSplat Loss Logging - Test Suite")
    print("=" * 70)

    test1 = test_parse_opensplat_loss()
    test2 = test_jsonl_format()

    if test1 and test2:
        print("✓ All tests passed!")
        exit(0)
    else:
        print("✗ Some tests failed")
        exit(1)
