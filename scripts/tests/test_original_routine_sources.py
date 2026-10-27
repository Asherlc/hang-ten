"""Source-prescription regressions for the shared iOS/Android plan library."""
import json
from pathlib import Path
import unittest


class OriginalRoutineSourcesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        library = json.loads((Path(__file__).resolve().parents[2] /
                              "HangTen/Resources/PlanLibrary.json").read_text())
        cls.plans = {plan["id"]: plan for plan in library["plans"]}
        cls.blocks = {block["id"]: block for block in library["blocks"]}

    def steps(self, plan_id):
        steps = []
        for ref in self.plans[plan_id]["blocks"]:
            pattern = self.blocks[ref["blockID"]]["steps"]
            count = ref.get("repeatCount", 1)
            ids, titles = ref.get("stepIDs", []), ref.get("stepTitles", [])
            for repetition in range(count):
                for index, template in enumerate(pattern):
                    step = dict(template)
                    if count > 1 and len(ids) == len(pattern) * count:
                        step["id"] = ids[repetition * len(pattern) + index]
                    else:
                        stem = ids[index] if ids else template["id"]
                        step["id"] = f"{stem}-{repetition + 1}" if count > 1 else stem
                    if titles:
                        step["title"] = titles[index if len(titles) == len(pattern) else repetition * len(pattern) + index]
                    steps.append(step)
        return steps

    def test_repeated_catalog_cycles_are_declared(self):
        for plan_id, count in [("research.max-hangs", 4), ("beastmaker-repeaters", 6)]:
            with self.subTest(plan_id=plan_id):
                self.assertIn(count, [ref.get("repeatCount", 1) for ref in self.plans[plan_id]["blocks"]])

    def test_warmups_preserve_source_timing_gaps_and_published_windows(self):
        warmups = {key: plan for key, plan in self.plans.items() if key.startswith("warmup.")}
        self.assertEqual(len(warmups), 4)
        for key, plan in warmups.items():
            self.assertEqual(plan["metadata"]["focus"], "warmUp")
            self.assertIn("warm-up", plan["metadata"]["workoutLabels"])
            self.assertEqual(plan["metadata"]["provenance"], "adapted")
            self.assertTrue(plan["metadata"]["sourceURL"].startswith("https://"))
            self.assertNotIn("boardID", plan)
            self.assertTrue(all("gripType" not in step and "fingerConfiguration" not in step
                                for step in self.steps(key)))
        lattice = self.steps("warmup.lattice.progressive")
        self.assertEqual(len(lattice), 1)
        self.assertNotIn("duration", lattice[0])
        self.assertIn("3–4", lattice[0]["instruction"])
        beastmaker = self.steps("warmup.beastmaker.general")
        self.assertEqual(beastmaker[0]["duration"], 900)
        self.assertNotIn("duration", beastmaker[1])
        pyramid = self.steps("warmup.climbing.bouldering")
        self.assertEqual([s["duration"] for s in pyramid if "duration" in s], [600, 300, 600])
        self.assertEqual(next(s for s in pyramid if s["id"].endswith("depump"))["segments"],
                         [{"kind": "rest", "timing": "undefined"}])
        self.assertEqual([s["duration"] for s in self.steps("warmup.ccc.rope-practice")], [1200, 900, 900])

    def test_lopez_max_hangs_targets_preserve_the_prescribed_edge_range(self):
        work = [step for step in self.steps("research.max-hangs") if step["phase"] == "hang"]
        self.assertTrue(work)
        for step in work:
            for hand in step["segments"][0]["target"]["tasks"][0]:
                self.assertEqual(hand["target"]["depth"], {"minMM": 8, "maxMM": 20})

    def test_metolius_small_edge_retains_source_size_without_a_numeric_conversion(self):
        work = {step["id"]: step for step in self.steps("metolius.generic-ten-minute.intermediate")}
        for step_id in ["intermediate.minute-3.task-1", "intermediate.minute-6.task-1",
                        "intermediate.minute-6.task-2"]:
            hands = work[step_id]["segments"][0]["target"]["tasks"][0]
            edges = [hand["target"] for hand in hands if hand["target"].get("kind") == "edge"]
            self.assertTrue(edges, step_id)
            for edge in edges:
                self.assertEqual(edge["depth"], {"category": "small"}, step_id)

    def test_abrahamsson_original_ten_hang_sequence(self):
        plan_id = "research.abrahangs"
        self.assertEqual(self.plans[plan_id]["metadata"]["sourceURL"],
                         "https://www.youtube.com/watch?v=sBTI9qiH4UE")
        work = [s for s in self.steps(plan_id) if s["phase"] == "hang"]
        self.assertEqual(len(work), 10)
        self.assertEqual([s["activeDuration"] for s in work], [10] * 10)
        self.assertEqual([s["duration"] for s in work], [60] * 10)
        self.assertEqual([s["fingerConfiguration"]["engagedFingers"] for s in work],
                         [["index", "middle", "ring", "pinky"]] * 3 +
                         [["index", "middle", "ring"]] * 3 +
                         [["middle", "ring"], ["index", "middle"],
                          ["middle", "ring"], ["index", "middle"]])
        self.assertTrue(all("70–80%" in s["instruction"] for s in work[:6]))
        self.assertTrue(all("50–60%" in s["instruction"] for s in work[6:8]))
        self.assertTrue(all("30–40%" in s["instruction"] for s in work[8:]))
        self.assertTrue(all("pinky" in s["instruction"] for s in work[8:]))
        self.assertTrue(all(s["segments"][-1]["duration"] == 50 for s in work))

    def test_nelson_beginner_density_hangs_preserve_failure_and_recovery(self):
        plan_id = "coach.density-hangs"
        self.assertEqual(self.plans[plan_id]["metadata"]["sourceURL"],
                         "https://www.trainingbeta.com/the-simplest-finger-training-program/")
        steps = self.steps(plan_id)
        work = [s for s in steps if s["phase"] == "hang"]
        self.assertEqual(len(work), 4)  # Table 2: two positions, one set, two reps.
        self.assertTrue(all(s["segments"][0]["timing"] == "stopwatch" for s in work))
        self.assertTrue(all("muscular failure" in s["instruction"] for s in work))
        self.assertTrue(all("20–40" in s["instruction"] for s in work))
        self.assertEqual([s["duration"] for s in steps if s["phase"] == "rest"], [180] * 3)

    def test_bechtel_ladders_use_athlete_chosen_rests(self):
        plan_id = "coach.bechtel-three-six-nine"
        self.assertEqual(self.plans[plan_id]["metadata"]["sourceURL"],
                         "https://www.powercompanyclimbing.com/blog/2016/01/episode-2-resistance-training-with.html")
        steps = self.steps(plan_id)
        self.assertEqual(len(steps), 3)  # Explicitly labeled three-ladder app adaptation.
        self.assertTrue(all(s["segments"][0]["timing"] == "undefined" for s in steps))
        self.assertTrue(all("15 seconds" in s["instruction"] for s in steps))
        self.assertTrue(all("as long as you need" in s["instruction"] for s in steps))

    def test_megos_cites_his_own_video(self):
        self.assertEqual(self.plans["research.megos-one-arm-7-3"]["metadata"]["sourceURL"],
                         "https://www.youtube.com/watch?v=urTeUObQlsg")

    def test_nelson_all_three_methods_have_both_levels(self):
        expected = {
            "coach.nelson-recruitment-pulls.beginner": (12, "single", 4, 90),
            "coach.nelson-recruitment-pulls.expert": (16, "single", 4, 90),
            "coach.nelson-velocity-pulls.beginner": (4, "double", 2, 15),
            "coach.nelson-velocity-pulls.expert": (20, "single", 2, 15),
            "coach.nelson-density-hangs.expert": (9, "double", None, 180),
        }
        for plan_id, (count, hands, work_duration, recovery) in expected.items():
            with self.subTest(plan_id=plan_id):
                self.assertTrue(plan_id in self.plans, f"Missing source plan {plan_id}")
                metadata = self.plans[plan_id]["metadata"]
                self.assertEqual(metadata["sourceURL"],
                                 "https://www.trainingbeta.com/the-simplest-finger-training-program/")
                self.assertEqual(metadata["provenance"], "adapted")
                steps = self.steps(plan_id)
                work = [s for s in steps if s["phase"] != "rest"]
                self.assertEqual(len(work), count)
                self.assertTrue(all(len(s["segments"][0]["target"]["tasks"][0]) ==
                                    (1 if hands == "single" else 2) for s in work))
                if work_duration is None:
                    self.assertTrue(all(s["segments"][0]["timing"] == "stopwatch" for s in work))
                else:
                    self.assertEqual([s["activeDuration"] for s in work], [work_duration] * count)
                self.assertEqual([s["duration"] for s in steps if s["phase"] == "rest"],
                                 [recovery] * (count - 1))
                if "pulls" in plan_id:
                    self.assertTrue(all(s.get("action") == "isometricPull" for s in work),
                                    "Pull efforts must retain their action in workout recording")
                if "velocity" in plan_id and "expert" in plan_id:
                    self.assertTrue(all("power drops" in s["instruction"] for s in work))
                if "velocity" in plan_id and "beginner" in plan_id:
                    self.assertTrue(any("cycle" in note for note in metadata["notes"]))


if __name__ == "__main__":
    unittest.main()
