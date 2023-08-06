from pymongo import MongoClient
from typing import List, Optional
import dotenv
dotenv.load_dotenv("tokens.env")

import os

class Mongo:
    """
    Class with abstraction of MongoDB database.
    Allows for easier access to the database.
    """
    
    def __init__(self, db_url: str, db_name: str):
        self.client = MongoClient(db_url)
        self.db = self.client[db_name]

    def add_user_activity(self, user_id: int, course_code: str, semester: str, activity: str):
        """
        Add an activity for a specific user.
        
        Precondition: user_id exists in the database.
        """
        collection = self.db["users"]
        query = {"_id": user_id}
        update = {"$push": {"activity": {"courseCode": course_code, "Semester": semester, "Activity": activity}}}
        collection.update_one(query, update, upsert=True)

    def remove_user_activity(self, user_id: int, course_code: str, semester: str, activity: str):
        """
        Remove a specific activity for a user.

        Precondition: user_id exists in the database, and the activity exists for the user.
        """
        collection = self.db["users"]
        query = {"_id": user_id}
        update = {"$pull": {"activity": {"courseCode": course_code, "Semester": semester, "Activity": activity}}}
        collection.update_one(query, update)

    def add_user(self, user_id: int, profile: dict[str, str]):
        """
        Add a new user to the database.

        Precondition: user_id does not exist in the database.
        """
        collection = self.db["users"]
        collection.insert_one({"_id": user_id, "activity": [], "profile": profile})

    def update_user_profile(self, user_id: int, profile: dict[str, str]):
        """
        Updates a user's profile.
        """
        collection = self.db["users"]
        collection.update_one({"_id": user_id}, {"$set": {"profile": profile}})

    def get_user_profile(self, user_id: int) -> Optional[dict[str, str]]:
        """
        Returns a user's profile.
        Preconditions: user_id exists in the database.
        """
        return self.db["users"].find_one({"_id": user_id}).get("profile", None)

    def remove_user(self, user_id: int):
        """
        Remove a user and all their activities from the database.

        Preconditions: user_id exists in the database.
        """
        collection = self.db["users"]
        collection.delete_one({"_id": user_id})

    def get_user_activities(self, user_id: int) -> List[dict]:
        """
        Get the activities for a specific user.

        Preconditions: user_id exists in the database.
        """
        collection = self.db["users"]
        user_data = collection.find_one({"_id": user_id})
        return user_data.get("activity", [])

    def get_all_users(self) -> List[int]:
        """
        Get a list of all user IDs in the database.
        """
        collection = self.db["users"]
        return [user["_id"] for user in collection.find()]


    def is_user_tracking_activity(self, user_id: int, course_code: str, semester: str, activity: str) -> bool:
        """
        Check if a user is tracking a specific activity.
        Precondition: user_id exists in the database.
        """
        collection = self.db["users"]
        query = {"_id": user_id, "activity": {"$elemMatch": {"courseCode": course_code, "Semester": semester, "Activity": activity}}}
        return bool(collection.count_documents(query) > 0)
    
    def is_user_in_db(self, user_id: int) -> bool:
        """
        Check if a user with the given user ID exists in the database.
        """
        collection = self.db["users"]
        return bool(collection.count_documents({"_id": user_id}) > 0)

if __name__ == "__main__":
    db_url = os.getenv("PYMONGO")  # Replace with your MongoDB URL
    db_name = "TTBWatchr"  # Replace with your database name

    # Initialize the abstraction layer
    db = Mongo(db_url, db_name)

    # Add a user with their activities
    db.add_user(1234567890)
    db.add_user_activity(1234567890, "CSC148H1", "Fall 2023", "Tutorial")
    db.add_user_activity(1234567890, "MAT135Y1", "Summer 2023", "Lecture")

    # Remove an activity for a user
    # db.remove_user_activity(1234567890, "CSC148H1", "Fall 2023", "Tutorial")

    # # Remove the entire user with all activities
    # db.remove_user(1234567890)

    # Get user activities and all users
    print(db.get_user_activities(1234567890))
    print(db.get_all_users())
