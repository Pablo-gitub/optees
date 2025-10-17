# tests/_utils/fakes.py
class FakeSolver:
    """Port implementation: .solve(problem) -> dict"""
    def __init__(self, response):
        self.response = response
        self.last_problem = None

    def solve(self, problem):
        self.last_problem = problem
        return self.response
