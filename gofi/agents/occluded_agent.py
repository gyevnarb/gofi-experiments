from typing import Dict, List

import igp2 as ip


class OccludedAgent(ip.TrafficAgent):
    """ Agent executing a pre-defined macro action with a fixed set of times when it is occluded from the ego. """

    def __init__(self,
                 occlusions: List[Dict[str, float]],
                 agent_id: int,
                 initial_state: ip.AgentState,
                 goal: ip.Goal = None,
                 fps: int = 20,
                 macro_actions: List[ip.MacroAction] = None):
        """ Create a new occluded agent. """
        super().__init__(agent_id, initial_state, goal, fps, macro_actions)
        self._occlusions = occlusions

    def __repr__(self) -> str:
        return f"OccludedAgent(ID={self.agent_id})"

    def __str__(self) -> str:
        return self.__repr__()

    def is_occluded(self, t: int) -> bool:
        """ Check if the agent is occluded at the given time step. """
        return any(occlusion["start"] <= t < occlusion["end"] for occlusion in self._occlusions)

    @property
    def occlusions(self) -> List[Dict[str, float]]:
        """ The occlusions of the agent. """
        return self._occlusions
