import random
from typing import List, Tuple, Dict
from copy import copy
import igp2 as ip
import matplotlib.pyplot as plt
from itertools import product

from gofi.occluded_factor import OccludedFactor


class OGoalsProbabilities:
    """Class used to store and update goal, occlusion probabilities, as well as store useful results
    such as the priors, likelihoods, generated trajectories and rewards. """

    def __init__(self,
                 goals: List[ip.Goal] = None,
                 occluded_factors: List[OccludedFactor] = None,
                 goals_priors: List[float] = None,
                 occluded_factors_priors: List[float] = None):
        """Creates a new GoalsProbabilities object.

        Args:
            goals: a list of goals objects representing the scenarios goals.
            occluded_factors: list of occluded factor instantiations.
            goals_priors: optionally, a list of goal priors measured from the dataset.
                    If unused, the priors will be set to a uniform distribution.
            occluded_factors_priors: optionally, a list of occluded factors priors
        """
        self._goals = goals if goals else []
        self._occluded_factors = occluded_factors if occluded_factors else []
        self._goals_and_factors = list(product(self._goals, self._occluded_factors))

        if goals_priors is None:
            self._goals_priors = dict.fromkeys(self._goals, float(1 / len(self._goals)))
        else:
            self._goals_priors = dict(zip(self._goals, goals_priors))

        if occluded_factors_priors is None:
            self._occluded_factors_priors = dict.fromkeys(self._occluded_factors, 0.1)
        else:
            self._occluded_factors_priors = dict(zip(self._occluded_factors, occluded_factors_priors))
        self._merged_occluded_factors_probabilities = {factor: 0. for factor in self.occluded_factors}

        # Actual normalised goal and trajectories probabilities
        self._goals_probabilities = dict.fromkeys(self._goals_and_factors, float(1 / len(self._goals_and_factors)))
        self._trajectories_probabilities = dict.fromkeys(self._goals_and_factors, [])
        self._occluded_factors_probabilities = copy(self._occluded_factors_priors)

        # To store trajectory data
        self._optimum_trajectory = dict.fromkeys(self._goals_and_factors, None)
        self._current_trajectory = copy(self._optimum_trajectory)
        self._all_trajectories = {key: [] for key in self._goals_and_factors}

        # To store the plans that generated the trajectories
        self._optimum_plan = dict.fromkeys(self._goals_and_factors, None)
        self._all_plans = {key: [] for key in self._goals_and_factors}

        # Reward data
        self._optimum_reward = copy(self._optimum_trajectory)
        self._current_reward = copy(self._optimum_trajectory)
        self._all_rewards = {key: [] for key in self._goals_and_factors}

        # Reward difference data
        self._reward_difference = copy(self._optimum_trajectory)
        self._all_reward_differences = {key: [] for key in self._goals_and_factors}

        # The goal likelihoods
        self._likelihood = copy(self._optimum_trajectory)

    def set_merged_occluded_factors_probabilities(self, pz: Dict[OccludedFactor, float]):
        """ Set the merged occluded factor probabilities.

        Args:
            pz: the final merged occluded factor probabilities after recognition was performed for all observed agents.
        """
        self._merged_occluded_factors_probabilities = pz

    def sample_occluded_factor(self, k: int = 1) -> list[OccludedFactor]:
        """ Sample an occluded factor from the distribution $p(z|\hat{s}_{1:t})$

        Args:
            k: the number of factors to sample.
        """
        factors = self.occluded_factors
        weights = self.occluded_factors_probabilities.values()
        return random.choices(factors, weights=weights, k=k)

    def sample_goals_given_factor(self, occluded_factor: OccludedFactor, k: int = 1) -> list[ip.Goal]:
        """ Sample a goal given an occluded factor instantiations from the distribution $p(g^i|\hat{s}_{1:t},z)$

        Args:
            occluded_factor: occluded factor instantiation to condition on
            k: number of goals to sample
        """
        pg_z = {goal: p for (goal, factor), p in self.goals_probabilities.items() if factor == occluded_factor}
        goals = list(pg_z)
        weights = pg_z.values()
        return random.choices(goals, weights=weights, k=k)

    def optimal_trajectory_to_goal_with_factor(self, goal: ip.Goal, factor: OccludedFactor) \
            -> Tuple[ip.VelocityTrajectory, List[ip.MacroAction]]:
        """ Return the optimal trajectory to a given goal and given occluded factor instantiations from the
        current timestep. """
        key = (goal, factor)
        trajectory = self.all_trajectories[key][0]
        plan = self.trajectory_to_plan(key, trajectory)
        return trajectory, plan

    def sample_trajectory_to_goal_with_factor(self, goal: ip.Goal, factor: OccludedFactor, k: int = 1) \
            -> Tuple[List[ip.VelocityTrajectory], List[List[ip.MacroAction]]]:
        """ Sample a set of trajectories to a given goal and given occluded factor instantiations. """
        key = (goal, factor)
        trajectories = self._all_trajectories[key]
        if trajectories:
            weights = self._trajectories_probabilities[key]
            trajectories = random.choices(trajectories, weights=weights, k=k)
            plans = [self.trajectory_to_plan(key, traj) for traj in trajectories]
            return trajectories, plans

    def trajectory_to_plan(self, key: Tuple[ip.Goal, OccludedFactor], trajectory: ip.VelocityTrajectory) \
            -> List[ip.MacroAction]:
        """ Return the plan that generated the trajectory. Not used for optimal trajectories.
        The function will raise an error if either the key or the trajectory is not found.

        Args:
            key: a goal and occluded factor instantiation tuple
            trajectory: the trajectory for which the plan is to be retrieved
        """
        idx = self.all_trajectories[key].index(trajectory)
        return self.all_plans[key][idx]

    @property
    def goals_probabilities(self) -> Dict[Tuple[ip.Goal, OccludedFactor], float]:
        """Returns the current goals probabilities."""
        return self._goals_probabilities

    @property
    def goals_priors(self) -> Dict[ip.Goal, float]:
        """Return the goals priors."""
        return self._goals_priors

    @property
    def trajectories_probabilities(self) -> Dict[Tuple[ip.Goal, OccludedFactor], List[float]]:
        """ Return the trajectories probability distribution to each goal"""
        return self._trajectories_probabilities

    @property
    def optimum_trajectory(self) -> Dict[Tuple[ip.Goal, OccludedFactor], ip.VelocityTrajectory]:
        """Returns the trajectory from initial vehicle position generated to each goal to calculate the likelihood."""
        return self._optimum_trajectory

    @property
    def optimum_plan(self) -> Dict[Tuple[ip.Goal, OccludedFactor], List[ip.MacroAction]]:
        """ Returns the plan from initial vehicle position generated to each goal."""
        return self._optimum_plan

    @property
    def current_trajectory(self) -> Dict[Tuple[ip.Goal, OccludedFactor], ip.VelocityTrajectory]:
        """Returns the real vehicle trajectory, extended by the trajectory
         from current vehicle position that was generated to each goal to calculate the likelihood."""
        return self._current_trajectory

    @property
    def all_trajectories(self) -> Dict[Tuple[ip.Goal, OccludedFactor], List[ip.VelocityTrajectory]]:
        """ Returns the real vehicle trajectory, extended by all possible generated paths to a given goal."""
        return self._all_trajectories

    @property
    def all_plans(self) -> Dict[Tuple[ip.Goal, OccludedFactor], List[List[ip.MacroAction]]]:
        """ Returns all plans from the most recent vehicle position generated to each goal."""
        return self._all_plans

    @property
    def optimum_reward(self) -> Dict[Tuple[ip.Goal, OccludedFactor], float]:
        """Returns the reward generated by the optimum_trajectory for each goal"""
        return self._optimum_reward

    @property
    def current_reward(self) -> Dict[Tuple[ip.Goal, OccludedFactor], float]:
        """Returns the reward generated by the current_trajectory for each goal"""
        return self._current_reward

    @property
    def all_rewards(self) -> Dict[Tuple[ip.Goal, OccludedFactor], List[float]]:
        """Returns a list of rewards generated by all_trajectories for each goal"""
        return self._all_rewards

    @property
    def reward_difference(self) -> Dict[Tuple[ip.Goal, OccludedFactor], float]:
        """Returns the reward generated by the optimum_trajectory for each goal,
        if we are not using the reward_as_difference toggle."""
        return self._reward_difference

    @property
    def all_reward_differences(self) -> Dict[Tuple[ip.Goal, OccludedFactor], List[float]]:
        """Returns the rewards generated by all_trajectories for each goal and occluded factor,
        if we are using the reward_as_difference toggle."""
        return self._all_reward_differences

    @property
    def likelihood(self) -> Dict[Tuple[ip.Goal, OccludedFactor], float]:
        """Returns the computed likelihoods for each goal and occluded factor"""
        return self._likelihood

    @property
    def goals(self) -> List[ip.Goal]:
        """ Return each goal """
        return self._goals

    @property
    def goals_and_occluded_factors(self) -> List[Tuple[ip.Goal, OccludedFactor]]:
        """ Return the Cartesian product of the goals and the occluded factor instantiations. """
        return self._goals_and_factors

    @property
    def occluded_factors(self) -> List[OccludedFactor]:
        """ Return each occluded factor instantiation """
        return self._occluded_factors

    @property
    def occluded_factors_priors(self) -> Dict[OccludedFactor, float]:
        """ Return the priors corresponding to each occluded factor instantiation. """
        return self._occluded_factors_priors

    @property
    def occluded_factors_probabilities(self) -> Dict[OccludedFactor, float]:
        """ Return each actual occluded factor instantiation probability """
        return self._occluded_factors_probabilities

    @property
    def merged_occluded_factors_probabilities(self) -> Dict[OccludedFactor, float]:
        """ Return the merged occluded factor probabilities. """
        return self._merged_occluded_factors_probabilities
