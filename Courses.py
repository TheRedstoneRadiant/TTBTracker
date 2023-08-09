# File which contains all classes relevant to the TTB API replies
from __future__ import annotations
class Course:
    """
    Class which represents a course in a TTB API reply
    """
    
    def __init__(self, name: str, course_code: str, semester: str) -> None:
        self.name = name
        self.course_code = course_code
        self.semester = semester
        self.activities = {}
    
    def add_activity(self, activity: Activity):
        self.activities[activity.name] = activity

    def get_activity(self, name: str) -> Activity:
        """
        Returns the activity with the given name
        Raises KeyError if the activity does not exist
        """
        if name not in self.activities:
            raise KeyError(f"Activity {name} does not exist")
        return self.activities[name]

    def get_name(self) -> str:
        """
        Returns the name of the course
        """
        return self.name

    def get_all_activities(self) -> list[str]:
        """
        Returns a list of all the names of the activities in this course
        """
        return list(self.activities.keys())

class Activity:
    def __init__(self, name: str, type: str, current_enrollment: int, max_enrollment: int, enrollment_controls: bool) -> None:
        self.name = name
        self.type = type
        self.current_enrollment = current_enrollment
        self.max_enrollment = max_enrollment
        self.enrollment_controls = enrollment_controls
    
    def is_seats_free(self) -> bool:
        """
        Returns whether or not this activity has seats free
        """
        return self.current_enrollment < self.max_enrollment and not self.enrollment_controls
        