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

    def test_removed_general_and_wall_warmups_are_absent(self):
        removed = {
            "warmup.lattice.progressive", "warmup.beastmaker.general",
            "warmup.climbing.bouldering", "warmup.ccc.rope-practice",
        }
        self.assertTrue(removed.isdisjoint(self.plans))
        self.assertFalse(any(block.startswith(tuple(removed)) for block in self.blocks))

    def test_hangboard_warmups_are_source_linked_adaptations(self):
        ids = {"warmup.pitchsix.recruitment-prep", "warmup.entralpi.max-hang-ramp"}
        warmups = {key for key in self.plans if key.startswith("warmup.")}
        self.assertEqual(warmups, ids)
        for key in ids:
            plan = self.plans[key]
            self.assertNotIn("boardID", plan)
            self.assertEqual(plan["metadata"]["focus"], "warmUp")
            self.assertEqual(plan["metadata"]["category"], "warmup")
            self.assertEqual(plan["metadata"]["workoutLabels"], ["warm-up"])
            self.assertEqual(plan["metadata"]["provenance"], "adapted")
            self.assertTrue(plan["metadata"]["sourceURL"].startswith("https://"))
            self.assertNotEqual(self.steps(key)[-1]["phase"], "rest")

    def test_pitchsix_recruitment_preserves_contraction_load_and_each_hand(self):
        steps = self.steps("warmup.pitchsix.recruitment-prep")
        work = [step for step in steps if step["phase"] == "hang"]
        self.assertEqual(len(work), 24)
        for index, (contraction, percent) in enumerate([
                ("OISO", 50), ("OISO", 70), ("OISO", 80),
                ("OISO", 90), ("YISO", 60), ("YISO", 80)]):
            for offset, side in enumerate(["left", "right"]):
                pair = work[index * 4 + offset * 2:index * 4 + offset * 2 + 2]
                for step in pair:
                    self.assertEqual(step["action"], "isometricPull")
                    self.assertEqual(step["handUse"], "single")
                    self.assertEqual(step["side"], side)
                    self.assertEqual(step["gripType"], "halfCrimp")
                    self.assertNotIn("fingerConfiguration", step)
                    self.assertNotIn("externalLoadKGF", step)
                    self.assertIn(f"{percent}%", step["instruction"])
                    self.assertIn(contraction, step["instruction"])
                    self.assertEqual(step["duration"], 5)
                    self.assertEqual(step["segments"], [{
                        "kind": "work", "timing": "fixed", "duration": 5,
                        "target": {"tasks": [[{"side": side, "target": {"kind": "edge"}}]]},
                    }])
        rests = [step["duration"] for step in steps if step["phase"] == "rest"]
        self.assertEqual(rests, [10, 30] * 11 + [10])
        self.assertEqual(sum(s["duration"] for s in steps), 570)
        self.assertEqual([s["phase"] for s in steps], ["hang", "rest", "hang", "rest"] * 11 + ["hang", "rest", "hang"])

    def test_entralpi_ramp_discloses_timer_defaults_without_inventing_grips(self):
        steps = self.steps("warmup.entralpi.max-hang-ramp")
        self.assertEqual([s["phase"] for s in steps], ["hang", "rest", "hang", "rest", "hang"])
        work = [s for s in steps if s["phase"] == "hang"]
        for step, percent in zip(work, [50, 70, 85]):
            self.assertEqual(step["duration"], 5)
            self.assertEqual(step["action"], "hang")
            self.assertEqual(step["handUse"], "double")
            self.assertNotIn("gripType", step)
            self.assertNotIn("fingerConfiguration", step)
            self.assertNotIn("externalLoadKGF", step)
            self.assertIn(f"{percent}%", step["instruction"])
            self.assertIn("5–10", step["instruction"])
            self.assertEqual(step["segments"][0]["target"], {
                "tasks": [[{"target": {"kind": "edge"}}, {"target": {"kind": "edge"}}]],
            })
        rests = [s for s in steps if s["phase"] == "rest"]
        self.assertEqual([s["duration"] for s in rests], [60, 60])
        self.assertTrue(all("1–2 minutes" in s["instruction"] for s in rests))
        notes = " ".join(self.plans["warmup.entralpi.max-hang-ramp"]["metadata"]["notes"])
        self.assertIn("two hands", notes)
        self.assertIn("lighter", notes)
        self.assertIn("2–3", notes)

    def test_lopez_max_hangs_targets_preserve_the_prescribed_edge_range(self):
        work = [step for step in self.steps("research.max-hangs") if step["phase"] == "hang"]
        self.assertTrue(work)
        for step in work:
            for hand in step["segments"][0]["target"]["tasks"][0]:
                self.assertEqual(hand["target"]["depth"], {"minMM": 8, "maxMM": 20})

    def test_metolius_small_edge_retains_source_size_without_a_numeric_conversion(self):
        work = {step["id"]: step for step in self.steps("metolius.generic-ten-minute.intermediate")}
        for step_id in ["intermediate.minute-3.task-1", "intermediate.minute-6.task-1"]:
            tasks = work[step_id]["segments"][0]["target"]["tasks"]
            edges = [hand["target"] for task in tasks for hand in task
                     if hand["target"].get("kind") == "edge"]
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
        self.assertTrue(all("duration" not in s for s in work))
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
        self.assertTrue(all("duration" not in s for s in steps))
        self.assertTrue(all("15 seconds" in s["instruction"] for s in steps))
        self.assertTrue(all("as long as you need" in s["instruction"] for s in steps))

    def test_metolius_generic_minutes_preserve_counts_without_rep_time_estimates(self):
        expected = {
            "entry": {2: [1], 4: [3], 5: [2], 6: [5], 7: [4], 9: [3]},
            "intermediate": {1: [3], 2: [2], 5: [4], 6: [3, 3], 7: [15], 9: [3]},
            "advanced": {1: [3], 2: [20], 3: [5], 6: [5, 5], 8: [3], 9: [3]},
        }
        for level, counts in expected.items():
            steps = self.steps("metolius.generic-ten-minute." + level)
            self.assertEqual(len(steps), 10)
            self.assertEqual([s["duration"] for s in steps], [60] * 10)
            for minute, step in enumerate(steps, 1):
                with self.subTest(level=level, minute=minute):
                    self.assertTrue(step["restsAfterCompletion"])
                    self.assertNotIn("activeDuration", step)
                    self.assertEqual(len(step["segments"]), 1)
                    self.assertNotIn("duration", step["segments"][0])
                    self.assertEqual(step["segments"][0]["timing"],
                                     "stopwatch" if minute == 10 else "undefined")
                    self.assertEqual([r["minimum"] for r in step.get("repTargets", [])],
                                     counts.get(minute, []))
                    self.assertTrue(all("maximum" not in r for r in step.get("repTargets", [])))
        advanced = self.steps("metolius.generic-ten-minute.advanced")
        self.assertTrue(advanced[1]["repTargets"][0]["isOptional"])
        self.assertIn("20-second L-sit or 20 hanging knee curls", advanced[1]["instruction"])
        self.assertIn("Stay on", advanced[2]["instruction"])
        self.assertIn("each for 5 seconds", advanced[3]["instruction"])
        self.assertIn("20-second large-slope hang", advanced[3]["instruction"])
        self.assertIn("Switch hands", advanced[4]["instruction"])
        self.assertIn("5-second front lever or 15-second", advanced[7]["instruction"])
        self.assertIn("no rest", advanced[9]["instruction"])
        # Keep successive holds as successive tasks, even within one work segment.
        entry_six = self.steps("metolius.generic-ten-minute.entry")[5]
        self.assertEqual([t[0]["target"]["kind"] for t in entry_six["segments"][0]["target"]["tasks"]],
                         ["sloper", "pocket"])

    def test_board_specific_metolius_cycles_keep_source_counts_and_completion_rest(self):
        counts = {
            "contact.entry": {1: [1], 2: [1, 1], 3: [1, 1], 5: [5], 7: [3], 9: [1, 1], 10: [2]},
            "contact.intermediate": {1: [3], 2: [2], 3: [4, 4], 7: [4, 10], 9: [4], 10: [4]},
            "contact.advanced": {1: [6], 2: [4], 3: [3, 3], 7: [5], 8: [3], 10: [8]},
            "simulator-3d.entry": {2: [1], 3: [1, 1], 5: [5], 7: [3], 9: [1]},
            "simulator-3d.intermediate": {2: [3], 3: [10], 7: [4, 10], 10: [5]},
            "simulator-3d.advanced": {1: [5], 2: [5, 5], 4: [5, 5], 7: [5], 9: [3], 10: [8]},
            "rock-rings.ten-minute": {1: [3], 3: [2, 2], 5: [5], 10: [5]},
        }
        for suffix, minutes in counts.items():
            steps = self.steps("metolius." + suffix)
            self.assertEqual(len(steps), 10)
            for minute, step in enumerate(steps, 1):
                self.assertEqual(step["duration"], 60)
                self.assertTrue(step["restsAfterCompletion"])
                self.assertEqual([t["minimum"] for t in step.get("repTargets", [])], minutes.get(minute, []))
                self.assertNotIn("activeDuration", step)

    def test_method_emom_counts_are_self_paced_inside_source_minutes(self):
        steps = self.steps("method.intermediate-hangboarding.emom")
        counts = {2: 3, 3: 5, 5: 3, 7: 3, 9: 10}
        self.assertEqual([s["duration"] for s in steps], [60] * 10)
        for minute, count in counts.items():
            step = steps[minute - 1]
            self.assertEqual(step["repTargets"][0]["minimum"], count)
            self.assertTrue(step["restsAfterCompletion"])
            self.assertEqual(step["segments"][0]["timing"], "undefined")
            self.assertEqual(len(step["segments"]), 1)
            self.assertNotIn("duration", step["segments"][0])
        self.assertEqual(steps[0]["segments"][0]["duration"], 20)
        self.assertEqual(steps[3]["segments"][0]["duration"], 15)
        self.assertEqual(steps[5]["segments"][0]["duration"], 10)
        self.assertEqual(steps[7]["segments"][0]["duration"], 25)
        self.assertEqual(steps[9]["segments"][0]["timing"], "stopwatch")

    def test_hooper_self_paced_tasks_keep_source_recovery_windows(self):
        steps = self.steps("hoopers-beta.introductory-home-hangboard")
        warmup = steps[:7]
        self.assertTrue(all("duration" not in s for s in warmup))
        self.assertEqual(warmup[1]["repTargets"][0]["minimum"], 10)
        self.assertEqual(warmup[2]["repTargets"][0],
                         {"id": "push-ups", "title": "Push-ups", "minimum": 10, "maximum": 20})
        for step in warmup[3:]:
            self.assertNotIn("minimum", step["repTargets"][0])
            self.assertNotIn("maximum", step["repTargets"][0])
        round_five_pulls = [step for step in steps
                            if "round-5" in step["id"] and step["id"].endswith("pull-ups")]
        self.assertEqual(len(round_five_pulls), 4)
        self.assertTrue(all(step["repTargets"] == [{"id": "pull-ups", "title": "Pull-ups"}]
                            for step in round_five_pulls))
        for step in steps:
            if step["phase"] != "conditioning":
                continue
            if "round-5" in step["id"]:
                self.assertNotIn("duration", step)
            elif "round-" in step["id"]:
                self.assertIn(step["duration"], [60, 90, 180])
                self.assertTrue(step["restsAfterCompletion"])
            if step["id"].endswith("kicks"):
                self.assertEqual([(t["minimum"], t["maximum"]) for t in step["repTargets"]], [(20, 30), (20, 30)])
            if step["id"].endswith("hollow"):
                self.assertEqual((step["repTargets"][0]["minimum"], step["repTargets"][0]["maximum"]), (10, 20))
                self.assertIn("rest for about 10 seconds, then hold", step["instruction"])

    def test_failure_efforts_are_uncapped_but_keep_source_intervals(self):
        for plan_id, count in [("coach.density-hangs", 4), ("coach.nelson-density-hangs.expert", 9),
                               ("tension-long-hangs", 3), ("tension-6-6-6-plus", 4)]:
            work = [s for s in self.steps(plan_id) if s["phase"] == "hang"]
            self.assertEqual(len(work), count)
            self.assertTrue(all("duration" not in s for s in work))
            self.assertTrue(all(s["segments"][0]["timing"] == "stopwatch" for s in work))
            self.assertTrue(all("pause" not in s["instruction"].lower() for s in work))
        for step in self.steps("tension-6-6-6-plus"):
            if step["phase"] == "hang":
                self.assertIn("6s hang / 6s rest, 6+ reps", step["instruction"])
                self.assertEqual(step["repTargets"][0]["minimum"], 6)
                self.assertNotIn("maximum", step["repTargets"][0])


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
