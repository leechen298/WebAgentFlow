"""Learning sub-package — autonomous learning and exploration.

Public API:
  - infer_candidates()           — rule-based candidate inference
  - ExplorationRunService        — exploration run CRUD
  - LearnedPathService           — learned path CRUD
  - SuccessCriteriaService       — success criteria CRUD
  - CandidateFeedbackService     — candidate feedback CRUD
  - evaluate_success()           — success criteria evaluator
  - make_before_state()          — helper for evaluator
  - run_exploration()            — generic exploration loop engine
"""

from app.services.learning.candidate_inference import infer_candidates
from app.services.learning.exploration_run_service import ExplorationRunService
from app.services.learning.learned_path_service import LearnedPathService
from app.services.learning.success_criteria_service import SuccessCriteriaService
from app.services.learning.candidate_feedback_service import CandidateFeedbackService
from app.services.learning.success_evaluator import evaluate_success, make_before_state


def run_exploration(*args, **kwargs):
    """Lazy wrapper to avoid importing Playwright at module level."""
    from app.services.learning.exploration_loop import run_exploration as _run
    return _run(*args, **kwargs)

__all__ = [
    "infer_candidates",
    "ExplorationRunService",
    "LearnedPathService",
    "SuccessCriteriaService",
    "CandidateFeedbackService",
    "evaluate_success",
    "make_before_state",
    "run_exploration",
]
