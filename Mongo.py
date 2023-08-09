import os
from typing import List, Dict, Union
import pymongo
import dotenv
dotenv.load_dotenv("tokens.env")

DEFAULT_PROFILE_LAYOUT = {"phone_number": "",
                          "instagram_username": ""}


class Mongo:
    def __init__(self, creds: str, database_name: str):
        """
        Initialize MongoDBProfiles instance.

        :param client: MongoClient instance for MongoDB connection.
        :param database_name: Name of the MongoDB database.
        """
        self.client = pymongo.MongoClient(creds)
        self.db = self.client[database_name]
        self.profiles_collection = self.db['profiles']
        self.courses_collection = self.db['courses']
        self.sections_collection = self.db['sections']

    def is_user_in_db(self, user_id: str) -> bool:
        """
        Check if a user exists in the database.

        :param user_id: User's Discord ID.
        :return: True if user exists, False otherwise.
        """
        return self.profiles_collection.find_one({"_id": user_id}) is not None

    def add_user_to_db(self, user_id: str, profile: Dict[str, str] = DEFAULT_PROFILE_LAYOUT) -> None:
        """
        Add a new user to the database with a blank profile.
        Precondition: user_id does not exist in the database.
        :param user_id: User's Discord ID.
        """
        if not self.is_user_in_db(user_id):
            self.profiles_collection.insert_one(profile)

    def remove_user(self, user_id: str) -> None:
        """
        Remove a user from the database.
        Precondition: user_id exists in the database.

        :param user_id: User's Discord ID.
        """
        # To delete the user we first have to remove them from the self.courses_collection
        # Then we can remove them from the self.profiles_collection

        # Get all the activities the user is tracking
        tracked_activities = self.get_user_tracked_activities(user_id)
        for activity in tracked_activities:
            self._remove_user_from_activity(
                user_id, activity["coursecode"], activity["semester"], activity["activity"])

        self.profiles_collection.delete_one({"_id": user_id})

    def update_user_profile(self, user_id: str, new_profile: Dict[str, Union[str, int]]) -> None:
        """
        Update a user's profile.
        Precondition: user_id exists in the database.
        :param user_id: User's Discord ID.
        :param new_profile: Dictionary containing updated profile information.
        """
        current_profile = self.get_user_profile(user_id)
        for key, value in new_profile.items():
            current_profile[key] = value
        self.profiles_collection.update_one(
            {"_id": user_id}, {"$set": {"profile": current_profile}})

    def add_tracked_activity(self, user_id: str, course_code: str, semester: str, activity: str) -> None:
        """
        Add a tracked activity to a user's profile.
        Precondition: user_id exists in the database.
        :param user_id: User's Discord ID.
        :param course_code: Course code of the tracked activity.
        :param semester: Semester of the tracked activity.
        :param activity: Activity type of the tracked activity.
        """
        self.profiles_collection.update_one(
            {"_id": user_id},
            {"$addToSet": {"tracked": {"coursecode": course_code,
                                       "semester": semester, "activity": activity}}}, upsert=True
        )
        self._add_user_to_activity(user_id, course_code, semester, activity)

    def remove_tracked_activity(self, user_id: str, course_code: str, semester: str, activity: str) -> None:
        """
        Remove a tracked activity from a user's profile.
        Precondition: user_id exists in the database and the tracked activity exists in the user's profile.
        :param user_id: User's Discord ID.
        :param course_code: Course code of the tracked activity.
        :param semester: Semester of the tracked activity.
        :param activity: Activity type of the tracked activity.
        """
        self.profiles_collection.update_one(
            {"_id": user_id},
            {"$pull": {"tracked": {"coursecode": course_code,
                                   "semester": semester, "activity": activity}}}
        )
        self._remove_user_from_activity(
            user_id, course_code, semester, activity)

    def get_all_courses(self) -> List[Dict[str, str]]:
        """
        Returns all the courses in the courses collection.
        """
        return list(self.courses_collection.find({}))

    def is_user_tracking_activity(self, user_id: str, course_code: str, semester: str, activity: str) -> bool:
        """
        Return whether a user is tracking a specific activity.
        """
        query = {"_id": user_id, "tracked": {"$elemMatch": {"coursecode": course_code, "semester": semester, "activity": activity}}}
        return bool(self.profiles_collection.count_documents(query) > 0)
    
    def get_user_tracked_activities(self, user_id: str) -> List[Dict[str, str]]:
        """
        Get a user's tracked activities.
        Precondition: user_id exists in the database.
        :param user_id: User's Discord ID.
        :return: List of dictionaries representing tracked activities.
        """
        user_doc = self.profiles_collection.find_one({"_id": user_id})
        return user_doc.get("tracked", [])

    def get_all_users(self) -> List[str]:
        """
        Get a list of all users in the database.

        :return: List of user IDs.
        """
        return [user["_id"] for user in self.profiles_collection.find({}, {"_id": 1})]

    def get_user_profile(self, user_id: str) -> Dict[str, Dict[str, str]]:
        """
        Get a user's profile.

        :param user_id: User's Discord ID.
        :return: Dictionary containing user's profile information.
        """
        return self.profiles_collection.find_one({"_id": user_id}).get("profile", None)

    def _add_user_to_activity(self, user_id: str, course_code: str, semester: str, activity: str) -> bool:
        """
        Add a user to an activity.

        :param semester: Semester code (e.g., "F2023").
        :param course_code: Course code.
        :param activity: Activity type (e.g., "Lecture").
        :param user_id: User's Discord ID.
        :return: True if user was added, False if already present.

        The database should follow this structure:
        _id: semester{
            courses {
                activity:{
                    [list of users]
                }
            }
        }

        """
        update_query = {
            f"{course_code}.{activity}": user_id
        }

        result = self.courses_collection.update_one(
            {"_id": semester},
            {"$addToSet": update_query},
            upsert=True
        )

        # return result.modified_count > 0

    def _remove_user_from_activity(self,  user_id: str, course_code: str, semester: str, activity: str) -> bool:
        """
        Remove a user from an activity.

        :param semester: Semester code (e.g., "F2023").
        :param course_code: Course code.
        :param activity: Activity type (e.g., "Lecture").
        :param user_id: User's Discord ID.
        :return: True if user was removed, False if not found.
        """
        update_query = {
            f"{course_code}.{activity}": user_id
        }

        result = self.courses_collection.update_one(
            {"_id": semester},
            {"$pull": update_query}, upsert=True
        )

        return result.modified_count > 0

    def add_course_sections(self, course_code: str, semester: str, activity_type: str, sections: list[str]):
        """
        Add a list of sections for a course to the database.
        """
        update_query = {
            f"{course_code}.{activity_type}": {"$each": sections}
        }

        # Update the document in the database
        self.sections_collection.update_one(
            {"_id": semester},
            {"$addToSet": update_query},
            upsert=True
        )

    def get_course_sections(self, course_code: str, semester: str, activity_type: str) -> List[str]:
        """
        Get a list of sections for a course.
        """
        doc = self.sections_collection.find_one({"_id": semester})
        return doc.get(course_code, {}).get(activity_type, [])


if __name__ == "__main__":
    # Crude tests for each of the methods
    database_creds = os.getenv("PYMONGO")
    db = Mongo(database_creds, "TTBTrackrDev")
    
    db._add_user_to_activity("123", "CSC148", "F2021", "Lecture")
    print(db.get_all_courses())