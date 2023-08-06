# File with required classes and methods to interact with the UofT TTB API

import requests


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

    def validate_course(self, course_code: str, semester: str, activity: str) -> bool:
        """
        Method which checks whether or not the provided course code and activity are valid using the 
        TTB API
        """
        self.json_data['courseCodeAndTitleProps']['courseCode'] = course_code
        self.json_data['courseCodeAndTitleProps']['courseSectionCode'] = semester
        response = requests.post(
        'https://api.easi.utoronto.ca/ttb/getPageableCourses', headers=self.headers, json=self.json_data)

        response = response.json()
        
        try:
            course = response['payload']['pageableCourse']['courses'][0]['sections']
            # Iterate through all the objects in `course` and check if activity is any of course[x]['name'] for x in range(len(course))
            for section in course:
                if activity == section['name']:
                    return True
            # If we're here, the activity is not in the course
            raise Exception("Activity not in course")
        except:
            # If any error is raised, the course is invalid
            return False

    def check_for_free_seats(self, course_code: str, semester: str, activity: str) -> bool:
        """
        Method which checks for free seats in a course using the TTB API
        
        Precondition: course_code, semester, and activity are all valid and apply to each other
        """
        self.json_data['courseCodeAndTitleProps']['courseCode'] = course_code
        self.json_data['courseCodeAndTitleProps']['courseSectionCode'] = semester
        response = requests.post(
        'https://api.easi.utoronto.ca/ttb/getPageableCourses', headers=self.headers, json=self.json_data)

        response = response.json()
        course = response['payload']['pageableCourse']['courses'][0]
        activity = [section for section in course['sections']
            if section['name'] == activity][0]
        return activity['maxEnrolment'] > activity['currentEnrolment']
        
    def get_name_from_code(self, course_code: str, semester: str) -> str:
        self.json_data['courseCodeAndTitleProps']['courseCode'] = course_code
        self.json_data['courseCodeAndTitleProps']['courseSectionCode'] = semester
        response = requests.post(
        'https://api.easi.utoronto.ca/ttb/getPageableCourses', headers=self.headers, json=self.json_data)

        response = response.json()
        course = response['payload']['pageableCourse']['courses'][0]
        return course['name']
        
if __name__ == '__main__':
    api = TTBAPI()
    print(api.validate_course('CSC148H5', 'S', 'LEC0101'))
    
    print(api.check_for_free_seats('CSC148H5', 'S', 'LEC0101'))
