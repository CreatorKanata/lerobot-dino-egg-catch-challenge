#!/usr/bin/env python

# Copyright 2025 The HuggingFace Inc. team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Hardware-free checks of LeKiwi.send_action's `arm_torque` action key (Dino Egg Catch fork).

The Feetech bus is replaced by a mock (as in test_so100_follower.py) and the robot has no cameras,
so no serial port or camera is opened. Written with unittest so it runs without pytest.
"""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, call, patch

from lerobot.robots.lekiwi import LeKiwi, LeKiwiConfig
from lerobot.robots.lekiwi.lekiwi import ARM_TORQUE_KEY

ARM_JOINTS = ("shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper")
BASE_ZERO = {"x.vel": 0.0, "y.vel": 0.0, "theta.vel": 0.0}


def _action(offset: float = 0.0, **extra: float) -> dict[str, float]:
    return {**{f"arm_{joint}.pos": 10.0 + offset + index for index, joint in enumerate(ARM_JOINTS)},
            **BASE_ZERO, **extra}


def _writes(bus: MagicMock, register: str) -> list:
    return [entry for entry in bus.sync_write.call_args_list if entry.args[0] == register]


class LeKiwiArmTorqueTests(unittest.TestCase):
    def setUp(self):
        self.bus = MagicMock(name="FeetechBusMock")

        def _bus_side_effect(*_args, **kwargs):
            self.bus.motors = kwargs["motors"]
            arm = [motor for motor in self.bus.motors if motor.startswith("arm")]
            self.bus.sync_read.return_value = {motor: float(index) for index, motor in enumerate(arm, 1)}
            return self.bus

        calibration_dir = tempfile.TemporaryDirectory()
        self.addCleanup(calibration_dir.cleanup)
        with patch("lerobot.robots.lekiwi.lekiwi.FeetechMotorsBus", side_effect=_bus_side_effect):
            config = LeKiwiConfig(port="/dev/null", cameras={}, calibration_dir=Path(calibration_dir.name))
            self.robot = LeKiwi(config)
        self.bus.is_connected = True  # marked connected without running connect()/configure()

    def _goal_raw(self, action: dict[str, float]) -> dict[str, float]:
        return {key.removesuffix(".pos"): value for key, value in action.items() if key.endswith(".pos")}

    def test_action_without_the_key_writes_both_goals_and_no_torque_calls(self):
        action = _action()
        returned = self.robot.send_action(action)
        self.assertEqual(_writes(self.bus, "Goal_Position"), [call("Goal_Position", self._goal_raw(action))])
        self.assertEqual(len(_writes(self.bus, "Goal_Velocity")), 1)
        self.bus.disable_torque.assert_not_called()
        self.bus.enable_torque.assert_not_called()
        self.assertEqual(returned, {key: value for key, value in action.items()})

    def test_torque_off_releases_the_arm_once_and_skips_goal_positions(self):
        for _ in range(3):
            returned = self.robot.send_action(_action(**{ARM_TORQUE_KEY: 0.0}))
        self.bus.disable_torque.assert_called_once_with(self.robot.arm_motors)
        self.bus.enable_torque.assert_not_called()
        self.assertEqual(_writes(self.bus, "Goal_Position"), [])
        self.assertEqual(len(_writes(self.bus, "Goal_Velocity")), 3)
        self.assertEqual(set(returned), set(_action()))  # same shape; the key is not echoed

    def test_torque_on_after_off_holds_the_present_pose_for_one_frame(self):
        self.robot.send_action(_action(**{ARM_TORQUE_KEY: 0.0}))
        self.bus.sync_write.reset_mock()
        self.robot.send_action(_action(**{ARM_TORQUE_KEY: 1.0}))
        present = self.bus.sync_read.return_value
        self.bus.sync_read.assert_called_once_with(
            "Present_Position", self.robot.arm_motors, num_retry=self.robot.config.num_read_retries
        )
        # The present pose, not the action's goal.
        self.assertEqual(_writes(self.bus, "Goal_Position"), [call("Goal_Position", present)])
        self.bus.enable_torque.assert_called_once_with(self.robot.arm_motors)
        self.assertEqual(len(_writes(self.bus, "Goal_Velocity")), 1)
        self.bus.sync_write.reset_mock()
        following = _action(offset=5.0, **{ARM_TORQUE_KEY: 1.0})
        self.robot.send_action(following)
        expected = [call("Goal_Position", self._goal_raw(following))]
        self.assertEqual(_writes(self.bus, "Goal_Position"), expected)
        self.bus.enable_torque.assert_called_once()

    def test_goal_position_write_comes_before_torque_enable(self):
        self.robot.send_action(_action(**{ARM_TORQUE_KEY: 0.0}))
        self.bus.reset_mock()
        self.robot.send_action(_action(**{ARM_TORQUE_KEY: 1.0}))
        names = [entry[0] for entry in self.bus.method_calls if entry[0] in ("sync_write", "enable_torque")]
        self.assertEqual(names[:2], ["sync_write", "enable_torque"])


if __name__ == "__main__":
    unittest.main()
