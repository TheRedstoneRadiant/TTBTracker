import requests
from Courses import *
class TTBAPI:
    """
    Class which abstracts all interactions with the UofT TTB API.
    """
    def __init__(self) -> None:
        self.headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive',
            'Content-Type': 'application/json',
            'DNT': '1',
            'Origin': 'https://ttb.utoronto.ca',
            'Prefer': 'safe',
            'Referer': 'https://ttb.utoronto.ca/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36 Edg/113.0.1774.35',
            'sec-ch-ua': '"Microsoft Edge";v="113", "Chromium";v="113", "Not-A.Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        }

        self.json_data = {
            'courseCodeAndTitleProps': {
                'courseCode': '',
                'courseTitle': '',
                'courseSectionCode': '',
                'searchCourseDescription': False,
            },
            'departmentProps': [],
            'campuses': [],
            'sessions': [
                '20239',
                '20241',
                '20239-20241',
            ],
            'requirementProps': [],
            'instructor': '',
            'courseLevels': [],
            'deliveryModes': [],
            'dayPreferences': [],
            'timePreferences': [],
            'divisions': [
                'APSC',
                'ARTSC',
                'FPEH',
                'MUSIC',
                'ARCLA',
                'ERIN',
                'SCAR',
            ],
            'creditWeights': [],
            'page': 1,
            'pageSize': 20,
            'direction': 'asc',
        }

    def _make_request(self, course_code: str, semester: str) -> dict:
        """
        Makes a request to the TTB API to get info on a course.
        Precondition: Coursecode is a valid coursecode, and semester is a valid semester
        Which coursecode is offered in
        """
        self.json_data['courseCodeAndTitleProps']['courseCode'] = course_code
        self.json_data['courseCodeAndTitleProps']['courseSectionCode'] = semester
        response = requests.post(
        'https://api.easi.utoronto.ca/ttb/getPageableCourses', headers=self.headers, json=self.json_data)
        return response.json()

    def get_course(self, course_code: str, semester: str) -> Course:
        """
        Returns a Course object from the TTB API
        Raises CourseNotFoundException if the course is deemed to be invalid
        """
        try:
            response = self._make_request(course_code, semester)
            course = response['payload']['pageableCourse']['courses'][0]
            to_return = Course(course['name'], course['code'], course['sectionCode'])
            activities = course['sections']
            for activity in activities:
                to_return.add_activity(Activity(activity['name'], activity['type'], activity['currentEnrolment'], activity['maxEnrolment'], activity['openLimitInd'] != 'N'))
            return to_return
        except IndexError:
            raise CourseNotFoundException("Invalid course code or semester")

    def validate_course(self, coursecode: str, semester: str, activity: str):
        """
        Method which validates a coursecode/semester/activity combo
        """
        try:
            course = self.get_course(coursecode, semester)
            activity = course.get_activity(activity)
        except CourseNotFoundException:
            raise CourseNotFoundException("Invalid course code or semester")
        except KeyError:
            raise InvalidActivityException("Invalid activity")

class CourseNotFoundException(Exception):
    """
    Exception which is raised when a course is not found in the TTB API
    """
    pass

class InvalidActivityException(Exception):
    """
    Exception which is raised when an activity is not found in the TTB API
    """
    pass

if __name__ == '__main__':
    api = TTBAPI()

    api.get_course('CSC148H5', 'S')