import tempfile
import unittest
from pathlib import Path

import run_hecras


class RunHecRasTests(unittest.TestCase):
    def test_parse_args_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            args_file = Path(temp_dir) / "args.txt"
            args_file.write_text(
                "\n".join(
                    [
                        "project_file=C:\\model\\Project.prj",
                        "max_workers=4",
                        "plan_numbers=01,02",
                    ]
                ),
                encoding="utf-8",
            )
            values = run_hecras.parse_args_file(str(args_file))
        self.assertEqual(values["project_file"], "C:\\model\\Project.prj")
        self.assertEqual(values["max_workers"], "4")
        self.assertEqual(values["plan_numbers"], "01,02")

    def test_parse_plan_numbers_all(self) -> None:
        self.assertIsNone(run_hecras.parse_plan_numbers("all"))
        self.assertIsNone(run_hecras.parse_plan_numbers("  "))

    def test_parse_plan_numbers_list(self) -> None:
        self.assertEqual(run_hecras.parse_plan_numbers("01, 02 ,03"), ["01", "02", "03"])

    def test_resolve_plan_numbers(self) -> None:
        plans = ["Plan 01", "Plan 02", "Plan 03"]
        self.assertEqual(run_hecras.resolve_plan_numbers(plans, ["01", "03"]), ["01", "03"])
        self.assertEqual(run_hecras.resolve_plan_numbers(plans, None), ["01", "02", "03"])
        with self.assertRaises(ValueError):
            run_hecras.resolve_plan_numbers(plans, ["99"])

    def test_parallel_results_to_status(self) -> None:
        plans = ["01", "02"]
        self.assertEqual(
            run_hecras._parallel_results_to_status(plans, {"01": True, "02": False}),
            {"01": True, "02": False},
        )
        self.assertEqual(run_hecras._parallel_results_to_status(plans, [True, False]), {"01": True, "02": False})


if __name__ == "__main__":
    unittest.main()
