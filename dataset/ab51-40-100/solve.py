from __future__ import annotations

from pathlib import Path
import sys
import json


def main() -> int:
    instance_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(instance_dir.parent))
    from ab_family_common import solve_from_data, update_optimal_value  # noqa: E402

    write = "--write-optimal-value" in sys.argv
    value = solve_from_data(instance_dir, backend="auto")
    print(f"Optimal objective value (maximize profit): {value:.6f}")

    inst_path = instance_dir / "instance.json"
    if inst_path.exists():
        inst = json.loads(inst_path.read_text(encoding="utf-8"))
        if "optimal_value" in inst:
            expected = float(inst["optimal_value"])
            diff = abs(value - expected)
            if diff <= 1e-4:
                print(f"Consistent with optimal_value in instance.json (diff {diff:.6g})")
            else:
                raise SystemExit(f"Inconsistent with optimal_value in instance.json: {value:.6f} vs {expected:.6f} (diff {diff})")

    if write:
        update_optimal_value(instance_dir, backend="auto", digits=6)
        print("Updated instance.json: optimal_value")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())